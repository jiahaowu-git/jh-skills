#!/usr/bin/env python3
"""
Kaspi.kz review statistics extractor (v4.0).

Single-script pipeline: parse URL → fetch agg → fetch all reviews →
cross-check → triage negatives → render 9-field report.

This replaces three v3-era scripts:
  - scripts/kaspi_api.py       (v1-era, superseded)
  - scripts/cluster_negatives.py (theme clustering + render)
  - scripts/pre_triage.py      (compound/contradiction/empty triage)

The new design:
  - One fetch + one render. No THEMES keyword registry.
  - Theme clustering is delegated to a sub-agent (see SKILL.md Step 4).
  - This script produces the aggregate fields + tiny-sample path.
  - For len(neg) > 10, the agent passes negatives to a delegate_task
    call and feeds the LLM themes back through `render_report(themes=...)`.

Usage:
  # Tiny-sample / zero-negative path (full auto):
  python kaspi_review.py <url-or-productId>

  # Cluster path: agent calls render_report(themes=llm_themes, other=...)
  # after the delegate_task call returns.

Output: prints the 9-field report to stdout, exit 0 on success,
exit 1 if any cross-check fails.

API: GET /yml/review-view/api/v1/reviews/product/{pid}?withAgg=true
Required headers: User-Agent, Accept, Referer (full original URL).
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# URL parsing + fetch
# ---------------------------------------------------------------------------

def parse_product_id(arg: str) -> tuple[str, str]:
    """Return (productId, referer). Accepts full URL, slug, or digits."""
    if re.fullmatch(r"\d{6,}", arg):
        return arg, f"https://kaspi.kz/shop/p/{arg}/"
    m = re.search(r"-(\d{6,})(?:/|\?|$)", arg)
    if not m:
        m = re.search(r"(\d{6,})", arg)
    if not m:
        raise ValueError(f"Cannot find productId in: {arg!r}")
    return m.group(1), arg


def fetch(pid: str, page: int, agg: bool, referer: str) -> dict:
    url = (
        f"https://kaspi.kz/yml/review-view/api/v1/reviews/product/{pid}"
        f"?baseProductCode&orderCode&filter=COMMENT&sort=POPULARITY"
        f"&limit=100&page={page}&merchantCodes&withAgg={'true' if agg else 'false'}"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": referer,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        # 403 = bad Referer, 429 = rate-limited. Retry once with cache-bust headers.
        if e.code in (403, 429):
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "application/json",
                "Referer": referer,
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        raise


# ---------------------------------------------------------------------------
# text_of() — the 3-field precedence rule
# ---------------------------------------------------------------------------

def text_of(r: dict) -> str:
    """text → minus → plus. Some reviews put content only in minus (2023-era)
    or plus (2020-era). Never classify as empty without checking all three."""
    c = r.get("comment")
    if not isinstance(c, dict):
        return (c or "").strip()
    for field in ("text", "minus", "plus"):
        v = (c.get(field) or "").strip()
        if v:
            return v
    return ""


# ---------------------------------------------------------------------------
# Pre-triage (compound / contradiction / empty)
# ---------------------------------------------------------------------------

POSITIVE_TEXT_HINTS = [
    "хорош", "удобн", "нравит", "понравил", "отличн", "доволен", "довольна",
    "рекоменду", "супер", "класс", "идеальн", "прекрасн", "замечательн",
    "нормальн", "хорошее качество", "вполне устраивает",
    "жақсы", "ұнайды", "ұнады", "ұнатты", "рахмет", "тамаша", "керемет",
    "өте жақсы", "бәрі жақсы",
    "good", "great", "nice", "love it", "works well",
]

COMPOUND_HINTS = [
    ", ", " и ", " а ", " но ", " плюс ", " также ", " к тому же ",
    ";", " — ", "：",
    " және ", " бірақ ",
]


def triage(reviews: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (compound, contradiction, empty)."""
    compound, contradiction, empty = [], [], []
    for r in reviews:
        t = text_of(r)
        if not t.strip():
            empty.append(r)
            continue
        tl = t.lower()
        if any(h in tl for h in POSITIVE_TEXT_HINTS):
            contradiction.append(r)
            continue
        joiner_count = sum(tl.count(j) for j in COMPOUND_HINTS)
        if joiner_count >= 3 or len(tl) > 300:
            compound.append(r)
    return compound, contradiction, empty


def triage_prompt_prefix(compound_count: int, contradict_count: int) -> str:
    """⚠️ prefix prepended to the LLM clustering prompt so it sees
    compound/contradiction counts before allocating themes."""
    lines = []
    if compound_count > 0:
        lines.append(
            f"⚠️ 复合评论: {compound_count} 条同时提到 2+ 问题(必须分配到 2 个主题,"
            f"而不是只归入一个)"
        )
    if contradict_count > 0:
        lines.append(
            f"⚠️ 评分矛盾: {contradict_count} 条 1-3★ 但文本实际在夸商品 — "
            f"统一归入「其他」并在 commentary 解释"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def extract(pid: str, referer: str) -> dict:
    """Fetch agg + all reviews + cross-check. Returns dict with all
    fields needed by render_report(). Raises on cross-check failure."""
    agg = fetch(pid, 0, agg=True, referer=referer)
    group = {g["id"]: g["total"] for g in agg["groupSummary"]}
    stat = {s["rate"]: s["count"] for s in agg["summary"]["statistic"]}
    avg = agg["summary"]["global"]
    product_name_ru = agg["data"][0]["product"]["name"] if agg.get("data") else ""

    for required in ("ALL", "COMMENT", "POSITIVE", "NEGATIVE"):
        if required not in group:
            raise RuntimeError(f"Missing groupSummary field: {required}")

    pages = (group["COMMENT"] + 99) // 100
    all_reviews = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(fetch, pid, p, False, referer) for p in range(pages)]
        for f in as_completed(futs):
            for r in f.result().get("data") or []:
                if isinstance(r, dict) and "rating" in r:
                    all_reviews.append(r)

    neg = [r for r in all_reviews if r["rating"] <= 3]
    pos = [r for r in all_reviews if r["rating"] >= 4]

    if len(neg) != group["NEGATIVE"]:
        raise AssertionError(
            f"NEG cross-check FAIL: filtered {len(neg)} vs API {group['NEGATIVE']}"
        )
    if len(pos) != group["POSITIVE"]:
        raise AssertionError(
            f"POS cross-check FAIL: filtered {len(pos)} vs API {group['POSITIVE']}"
        )
    if group["COMMENT"] != group["POSITIVE"] + group["NEGATIVE"]:
        raise AssertionError(
            f"COMMENT math FAIL: {group['COMMENT']} != "
            f"{group['POSITIVE']} + {group['NEGATIVE']}"
        )

    dated = sorted(
        [(datetime.strptime(r["date"], "%d.%m.%Y"), r) for r in all_reviews if r.get("date")],
        key=lambda x: x[0],
    )
    earliest = dated[0][0].strftime("%Y-%m-%d") if dated else "N/A"

    return {
        "pid": pid,
        "referer": referer,
        "group": group,
        "star": stat,
        "avg": avg,
        "product_name_ru": product_name_ru,
        "all_reviews": all_reviews,
        "neg": neg,
        "pos": pos,
        "earliest": earliest,
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_report(
    *,
    url: str,
    pid: str,
    product_name_ru: str,
    product_name_zh: str,
    avg,
    group: dict,
    star: dict,
    earliest: str,
    neg: list[dict],
    themes: list[tuple[str, int]] | None = None,
    other_count: int | None = None,
) -> str:
    """Build the 9-field plain-text report.

    - If `themes` is None and neg is empty: field 9 = "没有差评".
    - If `themes` is None and 0 < len(neg) <= 10: tiny-sample path,
      each negative is "(N) 中文翻译 (N星)". Translation MUST be passed
      in via `themes` as a list of ("中文翻译 (N星)", 1) tuples (the LLM
      or the caller pre-translates). The 1-count is just structural.
    - If `themes` is set: cluster path. other_count must be set too;
      reconciliation: sum(themes counts) + other_count == len(neg).
    """
    pos = group["POSITIVE"]
    total = group["COMMENT"]
    pos_rate = pos / total * 100 if total else 0.0

    lines = [
        "【Kaspi 商品评论报告】",
        "",
        f"1. 商品URL：{url}",
        f"2. 商品名：{product_name_zh}（原文：{product_name_ru}，ID：{pid}）",
        f"3. 总评分：{avg}/5",
        f"4. 好评率：{pos_rate:.2f}%（{pos}/{total}）",
        f"5. 1-5星评分分布：5星 {star[5]} 条 / 4星 {star[4]} 条 / "
        f"3星 {star[3]} 条 / 2星 {star[2]} 条 / 1星 {star[1]} 条",
        f"6. 好评总数：{pos} 条",
        f"7. 差评总数：{group['NEGATIVE']} 条",
        f"8. 最早评论日期：{earliest}",
        "9. 差评要点：",
    ]

    if themes is None:
        if not neg:
            lines.append("   没有差评")
        else:
            # Tiny-sample path: caller must translate BEFORE calling render.
            # This branch is defensive — the main flow handles this in main().
            for i, r in enumerate(neg, 1):
                lines.append(f"   ({i}) {text_of(r)}（{r['rating']}星）")
    else:
        # Cluster path
        if other_count is None:
            other_count = len(neg) - sum(c for _, c in themes)
        all_buckets = list(themes) + [("其他(无法归纳的笼统短评 + 空评论)", other_count)]
        sum_check = sum(c for _, c in all_buckets)
        ok = sum_check == len(neg)
        for i, (label, cnt) in enumerate(all_buckets, 1):
            lines.append(f"   ({i}) {label}（{cnt} 条）")
        lines.append("")
        mark = "✓" if ok else "❌"
        lines.append(
            f"数字对账:{len(neg)} = {' + '.join(str(c) for _, c in all_buckets)} "
            f"= {sum_check} {mark}"
        )

    return "\n".join(lines)


def translate_negatives(neg: list[dict]) -> list[str]:
    """Faithful Chinese translation. Used by the tiny-sample path.

    Rule: natural-language Chinese, preserve original sentence count,
    causality, sequence, buyer tone. Forbidden: compression, softening,
    adding facts. Allowed: clause reorder, sentence split, swap.

    Implementation: the calling LLM should do this — this function is
    a placeholder that returns the original text unchanged. The agent
    is expected to translate in-line before calling render.
    """
    return [text_of(r) for r in neg]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Kaspi review stats extractor")
    ap.add_argument("url_or_pid", help="Full Kaspi product URL or productId")
    ap.add_argument("--zh-name", default="", help="Chinese product name (field 2)")
    ap.add_argument("--out", default="", help="Write JSON dump to this path (for debugging)")
    args = ap.parse_args()

    pid, referer = parse_product_id(args.url_or_pid)
    try:
        data = extract(pid, referer)
    except (AssertionError, RuntimeError, urllib.error.HTTPError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    if args.out:
        Path(args.out).write_text(json.dumps({
            "pid": data["pid"],
            "group": data["group"],
            "star": data["star"],
            "avg": data["avg"],
            "product_name_ru": data["product_name_ru"],
            "earliest": data["earliest"],
            "neg_count": len(data["neg"]),
            "pos_count": len(data["pos"]),
            "neg_reviews": [
                {"rating": r["rating"], "date": r["date"], "author": r["author"],
                 "text": text_of(r)}
                for r in data["neg"]
            ],
        }, ensure_ascii=False, indent=2))

    print(f"# Aggregate data for {pid}:")
    print(json.dumps({
        "group": data["group"],
        "star": data["star"],
        "avg": data["avg"],
        "product_name_ru": data["product_name_ru"],
        "earliest": data["earliest"],
        "neg_count": len(data["neg"]),
    }, ensure_ascii=False, indent=2))

    print(f"\n# Triage:")
    compound, contradiction, empty = triage(data["neg"])
    print(f"  compound:      {len(compound)}")
    print(f"  contradiction: {len(contradiction)}")
    print(f"  empty:         {len(empty)}")
    print(f"  plain:         {len(data['neg']) - len(compound) - len(contradiction) - len(empty)}")
    if compound or contradiction:
        print(f"\n# Triage prompt prefix for LLM clustering:")
        print("---")
        print(triage_prompt_prefix(len(compound), len(contradiction)))
        print("---")

    print(f"\n# Negative review texts ({len(data['neg'])} total):")
    for i, r in enumerate(data["neg"], 1):
        print(f"  [{i}] {r['rating']}★ {r['date']} {r['author']}: {text_of(r)!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())