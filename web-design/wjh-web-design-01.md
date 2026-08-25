---
name: wjh-web-design-01
description: Generate high-fidelity SaaS landing pages in the GMI Cloud visual language — near-black hero with lime-green keyword highlight, white section rhythm, 3-column feature/pricing cards, dark metric strip, customer case grid, comparison table, FAQ, yellow wave CTA section, multi-column footer. Use when the user asks for a SaaS/AI/cloud GPU landing page, a 1:1 inspired-by reference, or "this style of page" without supplying an explicit Design Library.
user-invocable: true
---

# wjh-web-design-01 — SaaS Landing Page Generator (GMI-style)

This Skill produces a single-file `.design` HTML landing page in the GMI Cloud visual system, ready to drop on the Design Canvas.

## When to Use

Invoke when the user says any of:
- "生成一个 SaaS / AI / GPU / 云计算落地页"
- "用 GMI Cloud / lime-green / 近黑 hero 风格生成"
- "做一页类似这个风格的网页" + supplies the GMI Cloud screenshot or URL
- "创建 wjh-web-design-01 风格的落地页"

Do NOT use when:
- User provides a Design Library identity → defer to `solo-design` lane with library constraint.
- User wants 1:1 restoration of a different site → use `restore_1to1` lane.
- User wants a poster/banner/illustration only → use `solo-graphic-generation`.

## Brand Tokens (hard-coded, sampled from GMI Cloud)

Tokens are emitted as `--wjh-*` CSS custom properties. Replace only when the user explicitly requests a different palette.

| Token | Value | Usage |
|---|---|---|
| `--wjh-background` | `#ffffff` | page base |
| `--wjh-foreground` | `#0a0d12` | primary text |
| `--wjh-card` | `#ffffff` | card surface |
| `--wjh-primary` | `#c4f500` | lime accent (CTA + hero keyword highlight) |
| `--wjh-primary-foreground` | `#0a0d12` | text on lime |
| `--wjh-muted` | `#f5f6f7` | light gray surface |
| `--wjh-muted-foreground` | `#5b6470` | secondary text |
| `--wjh-border` | `#e5e7eb` | hairline |
| `--wjh-dark-bg` | `#0a0d12` | hero + dark metric strip |
| `--wjh-dark-fg` | `#f5f6f7` | text on dark |
| `--wjh-wave-bg` | `#f6f7d9` | yellow wave CTA section |
| `--wjh-radius-sm` | `6px` | small chips |
| `--wjh-radius-md` | `10px` | buttons |
| `--wjh-radius-lg` | `16px` | cards |
| `--wjh-radius-pill` | `999px` | pill buttons |
| `--wjh-font-sans` | `Inter, "PingFang TC", "Noto Sans TC", system-ui, sans-serif` |
| `--wjh-font-mono` | `JetBrains Mono, ui-monospace, SFMono-Regular, monospace` |
| `--wjh-container-max` | `1200px` |
| `--wjh-nav-height` | `56px` |

Spacing scale: `--wjh-space-1` = 4px through `--wjh-space-24` = 96px.

## Type Scale (locked)

| Role | size / line-height / weight |
|---|---|
| `h1-hero` | 64 / 1.05 / 800 |
| `h1-hero-accent` | 64 / 1.05 / 800 / lime inline span |
| `p-hero-sub` | 18 / 1.6 / 400 / `#b8bcc4` |
| `h2-section` | 36 / 1.2 / 700 |
| `p-body` | 16 / 1.6 / 400 / muted |
| `metric-number` | 56 / 1 / 800 |
| `btn-primary` | 14 / 1 / 600 / pill |
| `nav-link` | 14 / 1 / 500 |

## Page Skeleton (required region order)

The Sub-Agent MUST emit sections in this exact order. All sections use `<section>` with a semantic class name. Container max-width 1200px, centered.

1. `<header class="topnav">` — 56px tall, flex `space-between`, logo left + 5 text links + lime pill CTA right + EN/中 switch.
2. `<section class="hero">` — dark `#0a0d12` bg, 96px vertical padding. Left: "Powered by NVIDIA" pill, h1 with lime accent `<span>`, 18px sub, 2 buttons (primary lime "Explore Platform" + ghost "Watch Demo"). Right: AI workload visual card (mock terminal / metric gauge / node graph).
3. `<section class="trust-logos">` — 6 grayscale partner logos inline, light gray bg, 48px tall.
4. `<section class="feature-serverless">` — h2 + sub + primary CTA + 4 bullet list + simulator visual on right.
5. `<section class="feature-gpu">` — h2 + sub + CTA + 3 bullet list.
6. `<section class="pricing">` — h2 + sub + 3-card grid (H-series active + Blackwell "Coming Soon" muted card).
7. `<section class="metrics">` — dark bg, h2 + 4 large stats (3.7x / 5.1x / 30% / 2.3x style) + tiny line-chart placeholder.
8. `<section class="inference">` — h2 + 3 feature cards (Serverless / RDMA Cluster / API→Cluster scaling).
9. `<section class="customers">` — h2 + 3 customer cards with logo + bullet metric list.
10. `<section class="comparison-table">` — h2 + 8-row × 6-col comparison table.
11. `<section class="faq">` — h2 + 5 collapsible FAQ rows (`<details>`).
12. `<section class="wave-section">` — yellow `#f6f7d9` bg, inline SVG mountain ridge, centered CTA strip "部署更快，推理更穩，擴展更輕鬆".
13. `<footer>` — 4-column footer (Product / Solutions / Resources / Company) + GMI logo + social icons + legal line.

## Visual Contract (executable)

- Section vertical spacing: `96px` (`--wjh-space-24`)
- Card padding: `32px`
- Card gap: `16px` grid
- Card border-radius: `16px`
- Card border: `1px solid var(--wjh-border)`
- Card shadow: `0 1px 2px rgba(10,13,18,0.04), 0 1px 3px rgba(10,13,18,0.06)`
- Primary button: lime bg, near-black text, pill radius, padding `12px 24px`
- Ghost button on dark: transparent bg, white border, white text
- Inline keyword highlight: `<span class="accent">...</span>` with `color: var(--wjh-primary)`
- Numbered metric: 56px / 800 weight + tiny label below

## Tailwind Bridge (recommended)

The Skill integrates with Tailwind v4 via `@tailwindcss/browser@4`:
1. Inject the token CSS into `:root { --wjh-* }`.
2. Map tokens via `@theme inline { --color-primary: var(--wjh-primary); ... }`.
3. Also emit a defensive `.bg-primary / .text-primary / .border-primary / .ring-primary` fallback set so Tailwind classes always resolve to `--wjh-*` even before the CDN hydrates.
4. Include `lucide@1.8.0` UMD + a trailing `<script>lucide.createIcons();</script>`.

## Output Strategy

- Single-screen page → one complete HTML file with `<html>`, `<head>`, `<body>`, all `<style>` blocks.
- Multi-screen page → split into 2–3 patch operations, one per regionGroup (`first-screen` / `middle-section` / `footer-bottom`).
- Always run the head contract script after writing HTML.

## Workflow

1. Parse user request → identify brand variants (cloud GPU / AI infra / agent platform / SaaS generic).
2. Emit `colors_and_type.css` with the locked `--wjh-*` palette.
3. Write the page `pages/index.html` following the skeleton above. Keep section count + visual rhythm unless user explicitly asks to drop sections.
4. Apply `apply-html-head-contract.mjs` with `--title="..." --lang="zh-Hant-TW|en" --prefix=wjh`.
5. Create `.design` canvas entry with `deviceType: "desktop"` and one `page-{slug}` node.
6. Run `validate-finish-readiness.mjs --check=all`.

## Localization

- Default copy language: match the user's input language.
- Preserved GMI-style phrase templates (translate, do not invent):
  - Hero keyword list: `compute / inference / agents`
  - Section tagline: "從原型到正式部署，從單一 API 到完整 GPU 叢集"
  - Metric framing: `更高吞吐量 / 更高效推理 / 更低成本 / 更快擴展`
  - CTA primary: "Explore Platform" / "前往平台"
  - CTA secondary: "Watch Demo" / "觀看示範"

## Anti-Patterns (FORBIDDEN)

- Replacing lime `#c4f500` with another brand color without explicit user instruction.
- Using pure black `#000` for hero — always use `#0a0d12`.
- Omitting the wave CTA section.
- Using Tailwind utility classes without injecting the `--wjh-*` palette into `@theme inline`.
- Switching section vertical spacing away from 96px.
- Removing the inline keyword highlight from the hero h1.

## Quick Adaptation Recipes

- "改成深色 hero 黑色字" → DO NOT. Hero must stay near-black with white text and lime accent.
- "换品牌色" → Replace `--wjh-primary` only; never rename the variable.
- "改文案" → Keep section count + visual rhythm; only swap copy.
- "换成英文" → Set `--lang="en"`; swap UI copy; keep all structural tokens identical.
