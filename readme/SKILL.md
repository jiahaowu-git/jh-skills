---
name: readme
description: |
  Generate comprehensive, bilingual README.md documentation for software projects.
  Creates both English (default, README.md) and Chinese (README_zh-CN.md) versions
  with language switch links at the top. Use when: user says "write README",
  "generate README", "create documentation", "重写 README", "生成 README",
  "帮我写 README", or needs project documentation created or improved.
license: MIT
metadata:
  version: "1.0.0"
  category: documentation
  sources:
    - "GitHub README best practices"
    - "Keep a Changelog convention"
    - "Semantic Versioning"
---

# README Generator

Generate complete, professional, bilingual README documentation for software projects.

## Invocation

```
/readme [project description or "rewrite"]
```

If no description is provided, the skill will automatically explore the project structure
by reading key files: `package.json`, `src/main.js`, `src/App.vue`, router files,
store modules, components, views, and configuration files.

## Output Files

The skill produces two files:

| File | Language | Notes |
|------|----------|-------|
| `README.md` | English (default) | Set as default language |
| `README_zh-CN.md` | Simplified Chinese | Linked from English README |

## README Structure

Each README (both languages) follows this structure:

### Header Section
- Project name and badge row (Electron, Vue, Vite, Node shields)
- Language toggle link: `[中文](./README_zh-CN.md) | English`
- Horizontal divider

### Table of Contents
- Auto-generated anchor links to all sections

### Sections (English)
1. **Overview** — What the project does, who it's for, key value proposition
2. **Features** — Detailed feature list with descriptions, grouped by functional area
3. **Tech Stack** — Table of technologies used (framework, libraries, tools)
4. **Project Structure** — Tree-style directory listing with file/dir descriptions
5. **Getting Started**
   - Prerequisites (Node version, package manager)
   - Installation (`npm install`)
   - Development (`npm run dev`, `npm run electron:dev`)
   - Build (`npm run build`, `npm run electron:build`)
6. **Configuration** — Environment variable files and key variables (`.env`, `.env.development`, `.env.production`)
7. **API Integration** — Endpoint table with methods and descriptions
8. **Print Functionality** — How the print feature works (for print-related projects)
9. **Internationalization** — Language files and how to switch languages
10. **License** — License type or "private project"

### Sections (Chinese)
Same structure as English but fully translated:
1. 项目概述
2. 功能特性
3. 技术栈
4. 项目结构
5. 快速开始
   - 环境要求
   - 安装依赖
   - 开发调试
   - 构建打包
6. 配置说明
7. 接口对接
8. 打印功能
9. 国际化
10. 许可证

## Content Guidelines

### Tech Stack Table
Use this format:
```
| Category | Technology |
|----------|------------|
| Framework | [Name](url) version |
| State Management | [Name](url) version |
| ... | ... |
```

### Project Structure
- Use tree format with comments after filenames
- Group: core source dirs first (`src/`, `electron/`), then build/config, then root files
- Mark entry points: `main.js`, `main.cjs`, `App.vue`

### Features
- Name each feature in bold
- Use bullet points for sub-descriptions
- Note editable fields for forms/cards
- Mention keyboard shortcuts if applicable

### Getting Started Commands
Use fenced code blocks with `bash` language tag.
List commands in logical order: install → dev → build.

### Language Toggle
Both READMEs must have the toggle at the top:
- English: `[中文](./README_zh-CN.md) | English`
- Chinese: `[English](./README.md) | 中文`

## Auto-Exploration Checklist

When generating without explicit project description, explore:
- [ ] `package.json` — name, version, author, scripts, dependencies
- [ ] `src/main.js` — app bootstrap
- [ ] `src/App.vue` — root component structure
- [ ] `src/router/routes/index.js` — routes and views
- [ ] `src/store/modules/` — state modules
- [ ] `src/lang/` — i18n files
- [ ] `src/components/` — component inventory
- [ ] `src/views/` — page inventory
- [ ] `electron/main.cjs` or `electron/main.js` — Electron main process
- [ ] `vite.config.js` — build config
- [ ] `index.html` — HTML entry
- [ ] `build/` — build scripts/plugins

## Submission

After generating both README files:
1. Run `git add README.md README_zh-CN.md`
2. Commit with message: `docs: 重写项目 README，添加中英双语版本`
3. Push: `git push`
