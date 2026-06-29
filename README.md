# jh-skills

> 个人维护的 LLM Agent Skills 集合。每个子目录是一个独立、可加载的 Skill。

---

## 目录

- [项目简介](#项目简介)
- [Skill 列表](#skill-列表)
- [目录结构](#目录结构)
- [什么是 Skill](#什么是-skill)
- [使用方式](#使用方式)
- [贡献规范](#贡献规范)
- [许可证](#许可证)

---

## 项目简介

**jh-skills** 是一个存放个人开发的 LLM Agent Skills 的仓库。每个 Skill 是一个独立的领域能力包，面向特定任务（如抽取电商评论、生成文档、代码审查等），可以被 Agent 框架动态加载并按 `SKILL.md` 规约执行。

设计原则：

- **一个 Skill 一个领域**：不强求通用，每个 Skill 解决一个明确的垂直场景。
- **轻量自包含**：Skill 内部带 `SKILL.md` + `scripts/` + `references/`，不跨 Skill 依赖。
- **API/事实优先**：所有 Skill 默认拒绝凭空估算，数据类 Skill 必须有真实数据源。
- **可独立分发**：每个子目录可直接打包成 `~/.hermes/skills/<name>/` 安装。

## Skill 列表

| Skill | 描述 | 版本 | 适用场景 |
|---|---|---|---|
| [kaspi-comment-statistics](./kaspi-comment-statistics/) | 从 Kaspi.kz 商品 URL 抽取评论统计并生成 9 字段中文报告 | v4.2 | 哈萨克斯坦电商商品评论分析 |
| [readme](./readme/) | 为软件项目生成中英双语 README 文档 | v1.0.0 | 项目文档创建与重写 |

## 目录结构

```
jh-skills/
├── README.md                              # 本文件
├── kaspi-comment-statistics/              # Skill: Kaspi 评论统计
│   ├── SKILL.md                           #   Agent 加载的规约文件
│   ├── README.md                          #   Skill 详细说明
│   ├── scripts/
│   │   └── kaspi_review.py                #   单脚本流水线
│   └── references/
│       ├── kaspi-extraction-recipe.md     #   API 抽取配方
│       └── edge-cases.md                  #   边界场景与译名表
└── readme/                                # Skill: README 生成器
    └── SKILL.md                           #   Agent 加载的规约文件
```

## 什么是 Skill

Skill 是 LLM Agent 的一种**按需加载的能力单元**，由三部分组成：

```
<skill-name>/
├── SKILL.md              ← YAML frontmatter（name/description/triggers）
│                          + 正文（执行流程、关键规则、决策树）
├── scripts/              ← 可执行代码（可选）
└── references/           ← 详细参考资料（可选）
```

**加载时机**：Agent 根据 `description` 字段的触发条件判断是否加载。当用户提示词同时匹配 URL/关键词等结构性触发条件时，Agent 才把 `SKILL.md` 注入上下文并按其规约执行。

**与 Prompt 的区别**：Skill 是**持久化的、可版本控制的**能力定义，可以独立测试、独立分发；Prompt 是临时性的会话指令。

## 使用方式

### 在 Agent 框架中加载

将本仓库克隆到 Agent 的 skills 目录：

```bash
# Hermes Agent
git clone <this-repo> ~/.hermes/skills/jh-skills
```

或者软链接单个 Skill：

```bash
ln -s /path/to/jh-skills/kaspi-comment-statistics ~/.hermes/skills/kaspi-comment-statistics
```

加载后，Agent 会自动根据 Skill 的 `description` 字段判断何时激活。

### 直接运行脚本

部分 Skill（如 `kaspi-comment-statistics`）提供独立脚本，可不依赖 Agent 直接运行：

```bash
python kaspi-comment-statistics/scripts/kaspi_review.py "https://kaspi.kz/shop/p/..."
```

### 阅读 Skill 规约

每个 Skill 的 `SKILL.md` 是该能力的完整规范，无需 Agent 也可作为领域知识文档阅读。

## 贡献规范

新增 Skill 时遵循以下规约：

1. **目录命名**：kebab-case，全小写，不带版本号（`my-skill/` 而非 `my_skill/` 或 `my-skill-v1/`）。
2. **必备文件**：
   - `SKILL.md` — 含 YAML frontmatter（`name` / `description` / `version` / `license`）+ 完整正文
   - `README.md` — Skill 自身的人类可读说明
3. **结构预算**（参照已稳定 Skill）：
   - `SKILL.md` 目标 < 300 行，超过 400 必须审计
   - `references/` ≤ 3 个文件
   - `scripts/` ≤ 2 个文件
4. **正文不带版本叙事**：版本变更仅记在 frontmatter `metadata.history`，正文明示规约。
5. **不编造数据**：数据类 Skill 必须在失败时 surface blocker，禁止估算。
6. **commit 风格**：`feat(skill-name): 简述变更` 或 `fix(skill-name): 简述修复`。

## 许可证

MIT License. 各 Skill 的具体许可证见其 `SKILL.md` 的 YAML frontmatter。

---

**维护者**：Hermes Agent · **最后更新**：2026-06-29