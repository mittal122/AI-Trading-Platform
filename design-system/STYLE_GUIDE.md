# Obsidian Terminal — Frontend Style Guide

Single source of truth for the ui-ux-redesign branch. Tokens and component
classes are defined in `frontend/src/index.css` (Tailwind v4 `@theme`).

## Non-negotiable rules

1. **Never change data logic.** Fetching, polling, state, handlers, chart
   wiring stay byte-identical unless a real bug is found (document it).
   This is a *reskin*: JSX structure and classNames only.
2. **No emojis, no unicode glyph icons** (✕ ⓘ ▲ ⚙ ◆ ↺ etc.). Use
   `lucide-react` (already installed): `<X size={12} />`, `<Info size={11} />`,
   `<ArrowUpRight size={14} />`, `<Trash2 />`, `<Play />`, `<Square />`,
   `<RefreshCw />`, `<ChevronDown />`… Every icon-only button needs `aria-label`.
3. **Green/red mean market direction ONLY** (`text-up` / `text-down`).
   Brand/interactive accent is amber (`text-accent`, `bg-accent-soft`).
   Never indigo/blue/purple — those classes must all disappear.
4. **All numbers** (prices, percents, quantities, timestamps in tables) get
   the `num` class (JetBrains Mono, tabular).
5. `cursor-pointer` on everything clickable. Focus stays keyboard-visible
   (global `:focus-visible` handles it — don't add `outline-none`).

## Token classes (Tailwind v4 — usable as `bg-*` / `text-*` / `border-*`)

| Token | Value | Use |
|---|---|---|
| `bg` | #0b0d12 | page background |
| `surface` | #11141b | cards/panels |
| `raised` | #171b25 | hover rows, nested panels, inputs on surface |
| `line` | #232837 | hairline borders |
| `line-strong` | #303748 | control borders |
| `fg` | #e8ecf4 | primary text |
| `fg-soft` | #98a1b3 | secondary text |
| `fg-faint` | #5c6475 | labels, hints |
| `accent` | #f5a623 | brand amber |
| `accent-soft` | #f5a62326 | amber tint bg |
| `up` / `up-soft` | #2ebd85 | bullish |
| `down` / `down-soft` | #f6465d | bearish |

## Component classes (defined in index.css — prefer these over ad-hoc)

- `.card` (+ `.card-pad` for p-4) — panel container. Header pattern:
  `<header className="flex items-center justify-between px-3 pt-3 pb-2"><h2 className="panel-title">TITLE</h2>…</header>`
- `.panel-title` — 11px uppercase tracked label for panel headers
- `.num` — mono tabular numerals
- `.btn` `.btn-primary` `.btn-buy` `.btn-sell` `.btn-ghost` `.btn-danger-outline`
- `.input` (+ `.input-mono`), `.field-label`
- `.th` `.td` `.row-hover` — table cells (replace all ad-hoc table styling)
- `.chip` `.chip-up` `.chip-down` `.chip-warn` `.chip-muted` — status badges

## Replacement map (old → new)

| Old | New |
|---|---|
| `bg-[#0f1117]` | `bg-bg` |
| `bg-[#1a1d27]`, `bg-[#161923]` | `card` class or `bg-surface` |
| `border-[#2a2d3e]` | `border-line` |
| `bg-[#232736]`, hover bgs | `bg-raised` / `.row-hover` |
| `text-white` | `text-fg` |
| `text-slate-300/400` | `text-fg-soft` |
| `text-slate-500/600` | `text-fg-faint` |
| `text-green-400`, `bg-green-500/20` | `text-up`, `chip-up` |
| `text-red-400`, `bg-red-500/20` | `text-down`, `chip-down` |
| `text-indigo-*`, `bg-indigo-*` (any) | accent classes or neutral |
| `text-yellow-*`, `text-amber-*` | `text-accent` / `chip-warn` |
| `rounded-xl` | `rounded-lg` (cards use `.card` = 8px) |
| headings `text-xl font-bold text-white` | `text-[15px] font-semibold text-fg` + `panel-title` hierarchy |

## Layout rhythm

- Page container: `p-3 space-y-3 max-w-[1800px] mx-auto` (dense, not `p-6 space-y-5`)
- Grid gaps: `gap-3` (not 4/5)
- Table rows: `py-1.5`, body text `text-[12.5px]`
- Page H1s are removed — the nav rail communicates location. If a page needs
  a header row, it's a `panel-title`-style toolbar, not a hero heading.

## Reference implementations (already converted — match them)

- `frontend/src/pages/Terminal.tsx`
- `frontend/src/components/shell/TopBar.tsx`, `NavRail.tsx`
- `frontend/src/index.css`

## Verification (required before an agent reports done)

`cd frontend && npx tsc --noEmit` must pass. Grep your files for
`indigo|slate-|#1a1d27|#2a2d3e|#0f1117|rounded-xl|✕|ⓘ|▲|▼|◆|⚙` — all zero.
