# Kaspi Comment Statistics

> 基于 Kaspi.kz 公开评论 API 的单商品评论统计抽取 skill。输入一个 Kaspi 商品 URL，输出一份可直接复制的 9 字段纯文本报告。

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [触发条件](#触发条件)
- [目录结构](#目录结构)
- [运行依赖](#运行依赖)
- [快速开始](#快速开始)
- [输出报告格式](#输出报告格式)
- [执行流程](#执行流程)
- [差评处理决策树](#差评处理决策树)
- [关键规则](#关键规则)
- [边界场景](#边界场景)
- [验证清单](#验证清单)
- [维护规约](#维护规约)
- [版本历史](#版本历史)
- [许可证](#许可证)

---

## 项目简介

**Kaspi Comment Statistics** 是一个面向 LLM Agent 的领域 Skill，用于从哈萨克斯坦电商平台 [Kaspi.kz](https://kaspi.kz) 的公开评论 API 抽取单个商品的评论统计数据，并生成结构化的中文分析报告。

Skill 的设计目标：

- **API 唯一**：所有数字字段必须来源于当前会话内一次成功的 API 调用，绝不允许从 DOM 印象或记忆估算。
- **单 URL 单报告**：一次只处理一个商品，不输出跨商品对比表。
- **忠实翻译**：tiny-sample 路径下保留买家原文语气，不压缩、不软化、不增删事实。
- **轻量结构**：SKILL.md < 300 行、references ≤ 3 个、scripts ≤ 2 个。

## 核心特性

| 能力 | 说明 |
|---|---|
| 评论聚合 | 总评分、好评率、1-5 星分布、好评/差评总数、最早评论日期 |
| 中文译名 | 内置俄文 SKU → 中文译名表（家具、拖把、帐篷、清洁用品等） |
| 差评聚类 | 超过 10 条差评时自动归类为 3-10 个主题，附数字对账 |
| 忠实翻译 | ≤ 10 条差评时逐条翻译，保留原文时间线、因果、买家语气 |
| 数据校验 | 三重交叉对账（API 聚合 vs 翻页过滤 vs 数学一致性） |
| 异常检测 | 错挂评论、评分矛盾、空评论自动识别 |
| 重试机制 | 403 / 429 自动重试，无需人工干预 |

## 触发条件

**同时满足以下两条才加载本 Skill**：

1. URL 字面前缀为 `https://kaspi.kz/shop/p/`（或 `http://` 变体）。
2. 提示词包含以下任一关键词：评论报告 / 好评率 / 差评 / 评论统计 / review analysis / sentiment / complaint summary。

不满足时礼貌拒绝。

## 目录结构

```
kaspi-comment-statistics/
├── README.md                       # 本文件
├── SKILL.md                        # Skill 主体规约（Agent 加载此文件）
├── scripts/
│   └── kaspi_review.py             # 单脚本流水线：抓取 + 校验 + 渲染
└── references/
    ├── kaspi-extraction-recipe.md  # API 抽取配方 + 403/429 重试逻辑
    └── edge-cases.md               # 中文译名表 + 零差评/错挂/tiny-sample 边界
```

| 文件 | 行数预算 | 职责 |
|---|---|---|
| `SKILL.md` | < 300 | Agent 加载的唯一规范文件，包含决策树与关键规则 |
| `scripts/kaspi_review.py` | ≤ 2 脚本之一 | fetch + cross-check + render 一体化 |
| `references/kaspi-extraction-recipe.md` | ≤ 3 参考之一 | API 端点、Header、字段映射、重试 |
| `references/edge-cases.md` | ≤ 3 参考之一 | 译名表、样本量置信度、零差评、错挂、翻译守则 |

## 运行依赖

- Python ≥ 3.8（仅使用标准库：`urllib`、`concurrent.futures`、`json`、`re`、`datetime`）
- 无第三方依赖
- 网络可访问 `kaspi.kz`

## 快速开始

### 命令行（聚合数据 + 负评列表）

```bash
# 完整 URL
python scripts/kaspi_review.py "https://kaspi.kz/shop/p/stol-033665-chernyi-109364520/?c=750000000"

# 仅 productId
python scripts/kaspi_review.py 109364520

# 输出 JSON dump 到文件供调试
python scripts/kaspi_review.py 109364520 --out dump.json

# 指定中文商品名称
python scripts/kaspi_review.py 109364520 --zh-name "033665 黑色桌子"
```

脚本输出分四段：

1. **Aggregate data**：JSON 格式的聚合字段（group / star / avg / earliest / neg_count）
2. **Triage**：差评的预分类（compound / contradiction / empty / plain）
3. **Triage prompt prefix**：若有 compound 或 contradiction 评，输出供 LLM 聚类使用的提示前缀
4. **Negative review texts**：每条差评的原文文本

### 在 LLM Agent 中使用

将 `SKILL.md` 加入 Agent 工具集的 Skills 加载列表，按其定义的 6 步执行流程（见下文）运作。

## 输出报告格式

成功时输出一份 9 字段纯文本报告，可直接复制：

```
【Kaspi 商品评论报告】

1. 商品URL：https://kaspi.kz/shop/p/...
2. 商品名：黑色折叠桌（原文：Стол 033665 чёрный，ID：109364520）
3. 总评分：4.5/5
4. 好评率：89.04%（73/82）
5. 1-5星评分分布：5星 65 条 / 4星 8 条 / 3星 6 条 / 2星 2 条 / 1星 0 条
6. 好评总数：73 条
7. 差评总数：8 条
8. 最早评论日期：2023-04-15
9. 差评要点：
   (1) 中文本土翻译 (3星)
   (2) 中文本土翻译 (1星)
   ...
```

**字段对照表**：

| 字段 | 数据来源 |
|---|---|
| 1. 商品URL | 用户输入原文 |
| 2. 商品名 | RU 原文 + 中文译名 + productId |
| 3. 总评分 | `summary.global` |
| 4. 好评率 | `groupSummary[POSITIVE] / groupSummary[COMMENT] × 100` |
| 5. 1-5星分布 | `summary.statistic[].count` 按 `rate` 键 |
| 6. 好评总数 | `groupSummary[POSITIVE].total` |
| 7. 差评总数 | `groupSummary[NEGATIVE].total` |
| 8. 最早评论日期 | 所有抓取评论按 `date` 重排后取最小值（格式 `YYYY-MM-DD`） |
| 9. 差评要点 | 依差评数量走 tiny-sample 或 cluster 路径 |

## 执行流程

```
┌─────────────────────────────────────────────────────┐
│ Step 1 — 解析 URL 中的 productId（6 位以上数字）      │
│ Step 2 — 一次 withAgg=true 调用拿到所有聚合字段        │
│ Step 3 — 并行翻页抓取全部评论 + 三重交叉对账          │
│ Step 4 — 根据 len(neg) 走 tiny-sample 或 cluster 路径 │
│ Step 5 — 查 references/edge-cases.md 得到中文译名    │
│ Step 6 — 按 9 字段模板渲染报告                       │
└─────────────────────────────────────────────────────┘
```

**三重交叉对账（任一失败即停）**：

1. `len(neg) == group[NEGATIVE]`
2. `len(pos) == group[POSITIVE]`
3. `group[COMMENT] == group[POSITIVE] + group[NEGATIVE]`

## 差评处理决策树

```
                    len(neg) ?
                    │
        ┌───────────┼───────────┐
        │           │           │
      == 0      1 ≤ x ≤ 10    x > 10
        │           │           │
   ┌────▼────┐  ┌───▼────┐  ┌───▼──────────────┐
   │ 零差评   │  │ tiny-  │  │ cluster（主会话） │
   │ 字段 9: │  │ sample │  │ 3-10 个主题       │
   │ 没有差评 │  │ 路径   │  │ + 其他 + 数字对账  │
   └─────────┘  └────────┘  └──────────────────┘
```

| 路径 | 适用 | 字段 9 格式 | 翻译要求 |
|---|---|---|---|
| 零差评 | `len(neg) == 0` | 单行 `没有差评` | 仍需检查 5★ `minus` 与 4★ 内容 |
| tiny-sample | `1 ≤ len(neg) ≤ 10` | `(N) 中文翻译 (N星)` | 忠实翻译，逐条，不归类 |
| cluster | `len(neg) > 10` | `(N) 主题标签（X 条）` | LLM 聚类，主会话完成 |

**cluster 路径数字对账**：`sum(主题计数) + 其他 == len(neg)`，不对账则报告视为失败。

**sub-agent（可选）**：仅在主会话无法聚类（LLM 禁用、上下文过载）时使用。必须用 `toolsets=[]` 强制纯文本响应，避免 600s agentic loop 超时。

## 关键规则

> 这 12 条规则是 2026-06-26 大重写后沉淀的硬约束，违反任何一条都视为 Skill 损坏。

1. **API-only 数据**：每个数字字段必须可追溯到本会话 `fetch()` 的返回值。
2. **好评率分母用 `COMMENT`** 而非 `ALL`：`ALL` 包含纯星级无文本评论。
3. **`text_of()` 三字段优先级**：`text → minus → plus`。某些年代评论只写在 `plus`（2020）或 `minus`（2023）。
4. **`Referer` 必须是完整原始 URL**：含 `?c=750000000` 等参数，否则 403。
5. **`withAgg=true` 仅在首调用**：否则 `groupSummary` 与 `summary.statistic` 缺失。
6. **最早评论日期必须重排**：API 默认按 POPULARITY 排序。
7. **tiny-sample 与 cluster 格式互斥**：不可混用。
8. **tiny-sample 不过滤**：单词评论、评分矛盾评论、空评论全部保留。
9. **tiny-sample 翻译要忠实**：不压缩、不软化、不增删事实；复合评论（提到 2+ 问题）必须保留全部问题。
10. **cluster 优先主会话**：37 条差评轻松纳入上下文；sub-agent 仅作备选。
11. **不输出跨商品对比**：一 URL 一报告，禁止批量对比表。
12. **不做伞型归并**：用户偏好每平台独立 Skill。

## 边界场景

完整处理见 `references/edge-cases.md`。摘要：

| 场景 | 处理 |
|---|---|
| 中文译名缺失 | 查 `edge-cases.md §中文译名`；查不到给字面翻译，禁止发明品牌定位 |
| 极小样本 (`COMMENT < 20`) | ⚠️ 标注置信度低，仍输出完整 9 字段 |
| 零差评 | 检查 5★ `minus` 与 4★ 内容；样本量 < 50 时必须标"100% 好评置信度低" |
| 错挂评论 | 不静默删除，字段 9 标注 `(K) ⚠️ 数据异常:1 条评价实为 X`，计入对账 |
| 评分矛盾（1-3★ 但文本在夸） | 自动归入"其他"，commentary 说明 |
| 403 / 429 | 自动重试一次，加 `Cache-Control: no-cache` |

## 验证清单

每次输出报告前逐项打勾：

- [ ] URL 字面前缀匹配确认
- [ ] `withAgg=true` 调用返回 200，4 个 group ID 齐全
- [ ] 三重交叉对账全部通过
- [ ] 9 个字段齐全且顺序正确
- [ ] 字段 4 分母是 `COMMENT` 而非 `ALL`
- [ ] 字段 5 星数总和 = `ALL`
- [ ] 字段 8 日期格式严格 `YYYY-MM-DD`
- [ ] 字段 9 走 tiny-sample 或 cluster 之一（非混用）
- [ ] cluster 路径下 `sum(主题数) + 其他 == total_negative`
- [ ] **每个数字字段可追溯到 API 响应**（Pitfall #1）

## 维护规约

> 用户于 2026-06-26 反馈 Skill 已臃肿后确立。违反任一条视为 Skill 污染。

1. **正文不带版本叙事**：历史仅放在 YAML frontmatter `metadata.history`（1-2 行内）。禁止"v3.8 增加了…"内联写法。
2. **正文不写"v3.x Pitfall #N"**：用祈使语气平铺，不要版本号标记。
3. **单 URL 单报告**：禁止自动追加跨商品对比表。
4. **绝不编造数据**：API 失败就 surface blocker，禁止估算。

**规模预算**：

- `SKILL.md` 目标 < 300 行，超过 400 行必须审计臃肿
- references ≤ 3 个文件
- scripts ≤ 2 个文件
- 需要扩展时新建 reference 文件，而非膨胀主体

## 版本历史

完整历史见 `SKILL.md` 的 YAML `metadata.history`。近期里程碑：

| 版本 | 日期 | 变更 |
|---|---|---|
| v4.2 | 2026-06-29 | tiny-sample 路径：明确复合评论保留全部问题 |
| v4.1 | 2026-06-29 | cluster 路径翻为主会话默认；sub-agent 改为可选 fallback |
| v4.0 | 2026-06-26 | 大重写：SKILL.md 900→251 行，references 14→2，scripts 3→1，单决策树 |

## 许可证

MIT License. 详见 `SKILL.md` YAML frontmatter 的 `license` 字段。

---

**Skill 维护者**：Hermes Agent · **最后更新**：2026-06-29 · **当前版本**：v4.2