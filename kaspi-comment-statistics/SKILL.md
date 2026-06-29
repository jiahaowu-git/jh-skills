---
name: kaspi-comment-statistics
description: 'Extract Kaspi.kz product review statistics from a single product URL via the public Kaspi review API. STRUCTURAL TRIGGER: URL must START with literal prefix `https://kaspi.kz/shop/p/` (or `http://` variant). Plus keyword trigger: prompt mentions 评论报告 / 好评率 / 差评 / 评论统计 / review analysis / sentiment / complaint summary. Output is a 9-field plain-text report, copy-pasteable.'
version: 4.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [kaspi, reviews, statistics, e-commerce, sentiment]
    created_by: user
    owner: user
    location: '~/.hermes/skills/kaspi-comment-statistics/'
    history: |
      v1-v3.21 (2024-2026-06-26) — 21 iterations. Skill accumulated 900-line
      SKILL.md with 28 pitfall rules, 250-line inline changelog,
      16-product THEMES registry, cross-product comparison mode; 14
      references; 3 overlapping scripts. User flagged bloat on 2026-06-26.
      v4.0 (2026-06-26) — Clean rewrite. SKILL.md → 251 lines (now ~265
      after maintenance-rules section), references → 2, scripts → 1.
      Single decision tree: fetch → if len(neg) <= 10 → list each
      translation; else → LLM cluster into ≤10 themes.
      v4.1 (2026-06-29) — Cluster path flipped to main-session default.
      Sub-agent kept as optional fallback with toolsets=[] minimal
      pattern (was: forced delegate_task with detailed prompt that
      triggered 600s agentic-loop timeouts).
      v4.2 (2026-06-29) — Tiny-sample path: clarified that compound
      reviews (mentioning 2+ problems) stay compound in translation;
      do not drop a problem because "it's not a theme".
---

# Kaspi Comment Statistics

Extract review statistics for a single Kaspi.kz product URL via the public review API. Output: a 9-field plain-text report.

## When to load

BOTH must be true:
1. URL starts with literal `https://kaspi.kz/shop/p/` (or `http://`).
2. Prompt mentions 评论报告 / 好评率 / 差评 / 评论统计 / review analysis / sentiment / complaint summary.

Otherwise decline.

## Core principle

**No API call = no report.** Every numeric field must come from a successful API call in this session. Never estimate from DOM impression or memory. If the API fails, surface the blocker and stop.

## Execution flow

### Step 1 — Parse productId from URL

```python
import re
url = "https://kaspi.kz/shop/p/stol-033665-chernyi-109364520/?c=750000000"
m = re.search(r'-(\d{6,})(?:/|\?|$)', url)
product_id = m.group(1) if m else re.search(r'(\d{6,})', url).group(1)
referer = url  # use FULL URL as Referer — required for 200, not 403
```

### Step 2 — One `withAgg=true` call gives all aggregates

```python
import urllib.request, json

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def fetch(pid, page=0, agg=True):
    u = (f"https://kaspi.kz/yml/review-view/api/v1/reviews/product/{pid}"
         f"?baseProductCode&orderCode&filter=COMMENT&sort=POPULARITY"
         f"&limit=100&page={page}&merchantCodes&withAgg={'true' if agg else 'false'}")
    req = urllib.request.Request(u, headers={
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": referer,
    })
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

agg = fetch(product_id, 0, agg=True)
group = {g["id"]: g["total"] for g in agg["groupSummary"]}
star  = {s["rate"]: s["count"] for s in agg["summary"]["statistic"]}
avg   = agg["summary"]["global"]
product_name_ru = agg["data"][0]["product"]["name"]
```

**Required fields in `group`:** `ALL`, `COMMENT`, `POSITIVE`, `NEGATIVE`. If any missing, the call failed — stop and report blocker.

### Step 3 — Parallel-fetch all reviews + cross-check

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

pages = (group["COMMENT"] + 99) // 100
all_reviews = []
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = [ex.submit(fetch, product_id, p, False) for p in range(pages)]
    for f in as_completed(futs):
        for r in f.result().get("data") or []:
            if isinstance(r, dict) and "rating" in r:
                all_reviews.append(r)

# CROSS-CHECK — catches pagination bugs
neg = [r for r in all_reviews if r["rating"] <= 3]
pos = [r for r in all_reviews if r["rating"] >= 4]
assert len(neg) == group["NEGATIVE"], f"NEG cross-check FAIL: {len(neg)} vs {group['NEGATIVE']}"
assert len(pos) == group["POSITIVE"], f"POS cross-check FAIL: {len(pos)} vs {group['POSITIVE']}"
assert group["COMMENT"] == group["POSITIVE"] + group["NEGATIVE"]

# Earliest date — re-sort full dataset (API sorts by POPULARITY, not date)
def text_of(r):
    """text → minus → plus. Some 2020/2023-era reviews put content only in
    minus or plus. Never classify a review as empty without checking all three."""
    c = r.get("comment")
    if not isinstance(c, dict):
        return (c or "").strip()
    for field in ("text", "minus", "plus"):
        v = (c.get(field) or "").strip()
        if v:
            return v
    return ""

dated = sorted(
    [(datetime.strptime(r["date"], "%d.%m.%Y"), r) for r in all_reviews if r.get("date")],
    key=lambda x: x[0],
)
earliest_date = dated[0][0].strftime("%Y-%m-%d") if dated else "N/A"
```

**If any cross-check fails, do NOT report numbers.** Surface the failure.

### Step 4 — Process negatives

**Decision:**
- `len(neg) == 0` → field 9 = `没有差评`. But check 5★ `minus` fields and 4★ content for hidden complaints (rare but possible); surface any as "唯一不满点".
- `len(neg) <= 10` → **tiny-sample path**: skip clustering, output each review as `(N) 中文翻译 (N星)`. No theme labels, no original-language quote, no author, no date, no one-line summary.
- `len(neg) > 10` → **cluster path**: do it in the main session. Sub-agent delegation is optional — see "Sub-agent (optional, slow)" below for when it's worth using.

#### Tiny-sample path (`len(neg) <= 10`)

For each negative review:
1. Extract text via `text_of()`.
2. Translate to natural Chinese — **faithful rendition**, preserve original sentence count, causality, sequence, and buyer tone. Forbidden moves: compressing distinct facts into generic complaints; softening buyer tone; adding unstated facts. Allowed moves: clause reorder, sentence split, subject/predicate swap.
3. Output: `(N) 中文翻译 (N星)`.

**No pre-filtering.** Even single-word reviews (`Нормально.` → `还行`), rating-contradicting reviews (`挺好的` but 3★), or empty reviews (mark `<空评论>` but keep the slot) must be output.

#### Cluster path (`len(neg) > 10`) — do in the main session

**Do clustering directly in the main session.** Read the 37 reviews, group them by shared specific complaint, render the report. Single LLM turn, no tool calls, ~30 seconds total. The main session's context window handles `<100` reviews easily.

If main-session clustering is impossible (LLM disabled, context genuinely over capacity), fall back to a sub-agent. Use the minimal pattern below — sub-agents are **agentic loops**, not pure LLM calls, and a long/detailed prompt makes the LLM want to call tools, which then loops for 600s and times out.

##### Sub-agent (optional, slow) — minimal pattern

```python
delegate_task(
    goal=f"把以下 {len(neg)} 条 Kaspi 差评聚类成 3-10 个主题。直接输出 JSON，"
         f"不要调用任何工具，不要读文件，不要跑命令。\n\n{原文块}",
    toolsets=[],   # no tools = forces pure-text response = 1 turn = ~30s
)
```

**Why this works:** `toolsets=[]` removes the option to call any tool. The LLM has no choice but to output the JSON in one streaming turn. No agentic loop, no 600s spin.

**What to put in the prompt** (compact, no "you can use X tool" hints):
1. Product name (RU) for context.
2. Compact review list: `[i] {rating}★ "{text}"`.
3. The 6 hard rules (specific labels, sum_check, sort order).
4. Output format: `{"themes": [...], "other_count": N, "sum_check": M}`.

**What to NOT put in the prompt:**
- Pre-computed triage counts (compound/contradiction/empty). The LLM will redo them and disagree with you, wasting a turn. Let it classify fresh.
- Long pre-baked candidate themes. It anchors the LLM to your prior and skips re-reading.
- "You can use terminal to..." — kills the pure-text path.

After delegate returns, reconcile:

```python
total_in_themes = sum(count for _, count, _ in llm_themes)
other_count = len(neg) - total_in_themes
assert total_in_themes <= len(neg), "LLM over-counted — re-prompt"
llm_themes.append(("其他(无法归纳的笼统短评 + 空评论)", other_count))
```

### Step 5 — Chinese product name

Derive from RU title using the glossary in `references/edge-cases.md` §中文译名. If unsure, give a literal translation — never invent brand positioning.

### Step 6 — Output the 9-field report

```
【Kaspi 商品评论报告】

1. 商品URL：{url}
2. 商品名：{中文译名}（原文：{product_name_ru}，ID：{product_id}）
3. 总评分：{avg}/5
4. 好评率：{pos_rate:.2f}%（{pos}/{total}）
5. 1-5星评分分布：5星 {star[5]} 条 / 4星 {star[4]} 条 / 3星 {star[3]} 条 / 2星 {star[2]} 条 / 1星 {star[1]} 条
6. 好评总数：{pos} 条
7. 差评总数：{neg} 条
8. 最早评论日期：{earliest_date}
9. 差评要点：
   (1) {theme_1}（{count_1} 条）
   (2) {theme_2}（{count_2} 条）
   ...最多10条
```

**Tiny-sample field 9:**
```
9. 差评要点：
   (1) 中文翻译内容 (3星)
   (2) 中文翻译内容 (1星)
   ...
```

**Zero-negative field 9:** `没有差评` (single line).

## Critical rules (do NOT skip)

1. **API-only data.** Every number must trace to a `group[ID].total` or `star[rate]` value from this session's `fetch()` call. No DOM impression, no memory, no estimation. (Caught a real fabrication on 2026-06-26: Стол 033665 DOM showed 3 placeholder reviews, agent reported ALL=3/COMMENT=3/NEGATIVE=0/100% — reality was ALL=114/COMMENT=73/NEGATIVE=8/89.04%.)

2. **Use `COMMENT` as denominator for 好评率, not `ALL`.** `ALL` includes star-only reviews with no text.

3. **`text_of()` precedence: text → minus → plus.** Some reviews put content only in `plus` (e.g. IKEA Терье Айнур 2020-12-31: `"Нормально."` in `plus` only).

4. **`Referer` header must be the FULL original URL**, not the bare productId path. Bad referer → 403.

5. **`withAgg=true` on first call only.** Without it, `groupSummary` and `summary.statistic` are missing.

6. **Re-sort by date for earliest.** API default-sorted by POPULARITY.

7. **`len(neg) <= 10` format and `len(neg) > 10` format are mutually exclusive.** Never mix.

8. **Tiny-sample has no pre-filtering.** Single-word, contradictory, empty reviews all stay.

9. **Tiny-sample translation is faithful.** No compression, no softening, no added facts. Compound reviews (mentioning 2+ problems in one review) stay compound — translate all the problems the buyer mentioned, in the order they mentioned them. Do not silently drop a problem because "it's not a theme". Faithful means faithful.

10. **Cluster path: prefer main session.** The 37 reviews fit easily in context; clustering them is one LLM turn, ~30s. Only fall back to a sub-agent if the main session can't cluster (LLM disabled, extreme context pressure). When you do use a sub-agent, use `toolsets=[]` and a short prompt — sub-agents are agentic loops, and a long prompt makes the LLM want to call tools, looping 600s to a timeout.

11. **Do NOT output cross-product comparisons.** One URL = one report. No batch tables.

12. **Do NOT propose umbrella consolidation.** User-preferred architecture is per-platform dedicated skills.

## Verification checklist (before sending)

- [ ] URL prefix literal match confirmed
- [ ] `withAgg=true` call returned 200, all 4 group IDs present
- [ ] All 3 cross-check asserts pass
- [ ] All 9 fields present, in exact order
- [ ] Field 4 denominator is `COMMENT`, not `ALL`
- [ ] Field 5 star counts sum to `ALL`
- [ ] Field 8 date format `YYYY-MM-DD` only
- [ ] Field 9 follows tiny-sample OR cluster format (mutually exclusive)
- [ ] If cluster: `sum(theme counts) + 其他 == total_negative`
- [ ] **Every numeric field traceable to API response** (Pitfall #1)

## Companion files

- `scripts/kaspi_review.py` — full fetch + cross-check + render in one script.
- `references/edge-cases.md` — 中文译名 glossary + zero-negative / wrong-product / tiny-sample edge cases.
- `references/kaspi-extraction-recipe.md` — extraction recipe + 403/429 retry logic.

## Skill maintenance rules (do NOT violate — user's hard preference)

This skill was rewritten on 2026-06-26 after the user complained it had become 臃肿. Four hard rules going forward:

1. **No version-history narrative in the body.** History belongs in the YAML frontmatter `metadata.history` (1-2 lines max). The body must read as a clean spec, not a changelog. NEVER write "v3.8 added..." or "v3.10 changed..." inline — that bloats the document and forces readers to mentally diff versions. (Caught: 900-line SKILL.md had 250 lines of inline changelog.)

2. **No "v3.x Pitfall #N" numbering in the body.** Pitfalls are listed flat in "Critical rules" with imperative language, not numbered with version tags. Version numbering makes rules feel like accumulated archaeology. (Caught: 28 numbered "Pitfall #N" rules referencing v1, v3.6, v3.8, v3.14, v3.18, v3.20, v3.21, etc.)

3. **One URL = one report. No cross-product contamination.** Do NOT add "for comparison" tables, batch summaries, or references to other products in the same session unless the user explicitly asks for comparison. Per-product output stays per-product. (Caught: skill auto-appended a 19-product cross-product table after every report.)

4. **No fabricated data under any circumstance.** Every number must trace to a real API call in this session. If the API fails, surface the blocker — never estimate. (Caught on 2026-06-26: Стол 033665 DOM showed 3 placeholder reviews → agent reported ALL=3/NEGATIVE=0/100% → reality was ALL=114/NEGATIVE=8/89.04%.)

**Size budget:** target < 300 lines for SKILL.md. If it grows past 400, audit for accumulated bloat. References should be ≤ 3 files. Scripts should be ≤ 2. If the skill needs to grow, add a new reference file rather than expanding the body.