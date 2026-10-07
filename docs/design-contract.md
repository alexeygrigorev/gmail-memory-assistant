# Postmark design contract — Gmail, Material You

## Phase 1 — Attack (state of the UI before this contract)

1. **Inter-first stack** (`style.css:2`) — no typographic identity.
2. **Blue soup** — seven near-identical blues with no system: `#3458cc`, `#4566d1`,
   `#4565c5`, `#3656b7`, `#5470b8`, `#5b78c9`, `#5674cb`.
3. **Radii chaos** — 4, 5, 6, 7, 8, 9, 10px all in one file; no policy.
4. **Pastel tint chips** — `.mail-label` / `.category-chip` pale purple/amber/teal pills.
5. **Wash decoration** — `#f8faff` hovers, `#edf2fc` selections, `#eaf0f8` search;
   blue-gray tints without a tonal system.
6. **Bordered + blur-shadow card** — reply card: 1px border *and* `0 2px 5px` soft shadow.
7. **Eyebrow micro-labels** — "YOUR MAILBOX", "LABELS" (uppercase, letterspaced).
8. **Dingbat glyphs** — ▣ ⌕ ◈ ↩ ✎ ⌄ ↗ at inconsistent weights and baselines.
9. **No grid discipline in the list** — stacked rows, three font sizes, line-heights
   1.6/1.7/1.9, arbitrary paddings (11/13/21/26/29/33px).

## Phase 2 — Direction: Gmail (Material You), per the user's own screenshot

The reference is the current Gmail web app. This is an *adopted* art direction:
Google's system is already opinionated; the job is to apply it without exceptions.

### Type

- Stack: `'Google Sans', Roboto, Arial, Helvetica, sans-serif`. Roboto 400/500/700
  loaded from Google Fonts; offline it falls back to Arial/Liberation Sans
  (metric-compatible — what Gmail itself falls back to).
- Scale (px): 11/12/13/14/16/22. Subject heading 22/400. Buttons 14/500.
  No letter-spacing tricks anywhere.

### Color (exact tokens, no others)

| Token | Value | Use |
|---|---|---|
| canvas | `#f8fafd` | app background behind all cards |
| surface | `#ffffff` | header, sidebar, list card, reading card |
| text | `#1f1f1f` | primary content |
| secondary | `#444746` | dates, snippets, secondary labels, icons |
| faint | `#80868b` | placeholders, timestamps in toolbar |
| blue | `#0b57d0` | the one accent: active states, links, filled button, focus |
| blue-hover | `#0842a0` | filled button hover |
| tint | `#d3e3fd` | selection container: active folder, selected row, tonal button, avatar |
| on-tint | `#041e49` | text on tint |
| compose | `#c2e7ff` | Compose pill |
| on-compose | `#001d35` | text on compose |
| hairline | `#dde3ea` | card borders |
| divider | `#e8eaed` | internal rules |
| row-divider | `#f1f3f4` | mail list row separators |
| list-hover | `#f0f4f9` | mail row hover |
| nav-hover | `#e9eef6` | sidebar row hover, search pill fill |
| purple / amber / teal | `#9334e6` / `#b06000` / `#0f9d9f` | category text + dots |
| avatar tints | `#f3e8fd`/`#6d1a85`, `#f7e9d4`/`#7a4f01`, `#d7efee`/`#0f6f6d` | initials avatars |
| success | `#146c2e` | saved-memory events |
| error | `#f9dedc` bg / `#8c1d18` text | error banner |

### Radius policy

- `9999px` pill: search, buttons, folder/label rows, switch track, text buttons.
- `16px`: cards (list, reading, reply, memory panel) and the Compose button.
- `8px`: small inputs (feedback textarea), error banner, brand mark.
- Nothing else. No 4/5/6/7/9/10px.

### Depth policy

No box-shadows. Depth = white surface on `#f8fafd` canvas + hairlines. Focus rings
are flat 1px rings or 2px outlines, never blurred.

### Components

- **Header** 64px white, seamless with the white sidebar. Brand: red `#d93025`
  rounded mark with white "p" + gray `#5f6368` 22px wordmark (Gmail's red-logo,
  blue-UI split). Search: 48px pill, `#e9eef6`, magnifier icon; focus = white fill +
  flat blue ring. Account: 32px initials avatar on tint.
- **Sidebar**: white; Compose pill (56px, `#c2e7ff`, radius 16, pencil icon, anchors
  to the reply card); nav rows 14px, full-round pills, `#e9eef6` hover, `#d3e3fd`
  active with 500 weight; counts 12px `#444746`; labels as 8px colored dots.
- **List card**: white, radius 16, hairline border, floats on canvas. Toolbar row
  ("Inbox" + count), 12px subhead, hairline. Rows: CSS grid — sender (bold when the
  row is selected) | subject over one-line snippet | date right-aligned. Selected
  row: `#d3e3fd` + 4px `#0b57d0` left bar. Category label = 12px colored text with
  a dot, no pill.
- **Reading pane**: canvas with a white reading card (radius 16, hairline). Subject
  22/400; 40px initials avatar in the category tint; body 14/1.6 aligned under the
  sender; round 40px icon buttons for prev/next.
- **Reply card**: white, radius 16, hairline, no shadow. Primary CTA = filled pill
  `#0b57d0`; Revise = tonal pill `#d3e3fd`/`#041e49`; Regenerate/suggestions = blue
  text buttons; feedback textarea = outlined 8px radius. Memory switch checked =
  `#0b57d0`.
- **Icons**: inline Material-style SVG (stroke/fill `currentColor`), one weight,
  aligned to a 20/24px grid. No font glyph dingbats.

### Banned (must never reappear)

Inter/system-ui-first stacks; any blue outside `#0b57d0`/`#0842a0`; pastel chip
pills with 4px radii; uppercase eyebrow micro-labels; blur box-shadows; glyph
icons (▣ ⌕ ◈ ✎ ↗); radii outside {pill, 16, 8}; line-height > 1.7 on running text;
more than one tint-wash per state.

## Phase 3 — Scope

Pure re-skin of `web/src/style.css` + targeted `web/index.html` edits (icons,
eyebrows, font links, theme-color). Class names, ids, and `main.js` stay untouched;
the mail-row grid uses `display: contents` on `.mail-item-top` so the JS-emitted
markup lays out as Gmail columns.

## Phase 4 — Verify

Build (`npm run build --prefix web`), CDP screenshots at 1440/1000/390px against the
attack list, real-backend smoke (streamed draft + memory-off revision), regenerate
`docs/email-demo.png`.
