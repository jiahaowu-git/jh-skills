# Kaspi API Extraction Recipe (v4.0)

> ## ⚠️ NO API CALL = NO REPORT
>
> Every numeric field in the 9-field report MUST come from a successful
> `fetch(pid, 0, agg=True)` API call **in this session**. Never estimate
> from DOM impression or memory.
>
> **Real failure (2026-06-26, Стол 033665 PID 109364520):** DOM showed
> 3 placeholder reviews → agent reported ALL=3/COMMENT=3/NEGATIVE=0/100%.
> API reality: ALL=114/COMMENT=73/NEGATIVE=8/89.04%.

## Endpoint

```
GET https://kaspi.kz/yml/review-view/api/v1/reviews/product/{productId}
    ?baseProductCode&orderCode
    &filter=COMMENT
    &sort=POPULARITY
    &limit=100                ← NOT size=, Kaspi silently ignores size=
    &page={N}
    &merchantCodes
    &withAgg=true             ← required for groupSummary
```

## Required headers

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "<full original product URL>",   # must match, else 403
}
```

The `Referer` must be the exact URL the user pasted (with `?c=<cityCode>` if present).

## Response → report field mapping

| Report field | API source |
|---|---|
| 总评分 | `summary.global` |
| 好评率 | `groupSummary[POSITIVE].total / groupSummary[COMMENT].total × 100` |
| 1-5星分布 | `summary.statistic[].count` keyed by `rate` |
| 好评总数 | `groupSummary[POSITIVE].total` |
| 差评总数 | `groupSummary[NEGATIVE].total` |
| 最早评论 | `min(date)` re-sorted across all fetched reviews |
| 商品名(原文) | `data[0].product.name` |

**Use `COMMENT` as the 好评率 denominator, NOT `ALL`.** `ALL` includes star-only reviews with no text.

## Date parsing

API date format: `dd.mm.yyyy`. Must `strptime` to datetime — lexicographic string sort puts `'05.01.2025'` before `'23.12.2024'`, wrong answer.

## 403 / 429 retry

On `HTTPError(403)` or `HTTPError(429)`: retry once with `Cache-Control: no-cache` header. `scripts/kaspi_review.py` does this automatically.

## End-to-end timing

| Reviews | Time |
|---|---|
| <100 | ~3s |
| 870 | ~12-15s |
| 1700+ | ~20s |

## Common errors

- 403: bad Referer (must be the full original URL, not the bare path).
- 200 but missing `groupSummary`: forgot `withAgg=true`.
- 200 but missing data: forgot `filter=COMMENT`.
- Cross-check `len(neg) != group[NEGATIVE]`: pagination incomplete. Re-fetch.
- Cross-check `len(pos) != group[POSITIVE]`: same.
- Cross-check `COMMENT != POSITIVE + NEGATIVE`: API schema mismatch, treat as data integrity issue.