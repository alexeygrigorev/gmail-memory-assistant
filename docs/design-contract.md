# Postmark design contract

One art direction, applied without exceptions. This file is the law for the
Postmark UI; any change that violates it needs this file changed first.

## Phase 1 — Attack on the previous design

Verified claims about the old UI, in priority order:

1. **Default font stack.** `Inter, ui-sans-serif, system-ui, …` for everything;
   every size between 9 and 23px is the same sans. No typographic identity.
2. **Seven unrelated blues for one role.** `#3458cc`, `#4566d1`, `#4565c5`,
   `#3658ba`, `#5674cb`, `#5b78c9`, `#365ea0` — a new blue invented per rule.
3. **Pastel wash canvas.** Background `#f6f8fc`, hover `#f8faff`, selected
   `#edf2fc`, active folder `#e2eafa`, search well `#eaf0f8`: the whole app is
   a blue-gray tint with no hard surface anywhere.
4. **Pale tint chips.** `.purple/.amber/.teal` filled pills for every category,
   plus pastel initial avatars (`#ece8f8` on `#7960a4`).
5. **Soft radii on everything.** 4/5/7/8/9/10px and 50% avatars — rounding as
   reflex, no radius policy.
6. **Eyebrow micro-labels.** "YOUR MAILBOX", "LABELS": 10px, weight 650,
   1.2px tracking, gray `#8a96a9`, floating above headings.
7. **Explainer sub-lines.** "All mail / Newest first" under "Inbox · 4
   messages"; "You review and edit every draft…" footnote; the draft-empty
   paragraph repeating the headline.
8. **A glyph on everything.** ⌕ search, ▣ folder, ↩ reply, ✎ empty state,
   ◈ memory panel, ⌄ chevron, `↗` appended to two buttons.
9. **Soft blurred elevation.** Reply card `box-shadow: 0 2px 5px #293f6510`.
10. **No tension anywhere.** Weights 550–720, sizes 9–23px; the boldest move
    on the whole page is a 3px blue selection bar.

## Phase 2 — Direction: post office, 1962

The product is a mailbox where a machine drafts the replies. So: **incoming
mail is typeset correspondence (serif, ink on paper); anything the machine
writes — drafts, labels, counts, statuses — is typewritten (mono).** The UI is
paper, ink, and rubber stamps. One stamp-ink red is the only accent.

### Typefaces

| Voice | Stack | Used for |
| --- | --- | --- |
| Correspondence / display | `Georgia, 'DejaVu Serif', 'Times New Roman', serif` | wordmark, Inbox h1, subject h2, email body, sender names (small caps), empty-state headline, avatar initials |
| Machine / chrome | `'Nimbus Mono PS', 'Courier New', monospace` | all labels, meta, dates, addresses, counts, stamps, buttons, inputs, the reply draft, memory panel |

### Type scale (no negative letter-spacing anywhere)

- Serif display: 26px/1.25 bold (subject), 24px/1.2 bold (Inbox), 20px/1.3 (empty state)
- Serif correspondence: 15px/1.75 (email body)
- Serif small caps: 14px (sender names)
- Mono draft: 13px/1.8
- Mono meta: 11.5px; mono stamp label: 10.5px uppercase, 0.1em tracking
- Mono section label: 10.5px uppercase, 0.14em tracking, used only in the sidebar (max two)

### Color

| Token | Hex | Role |
| --- | --- | --- |
| `--paper` | `#f2ecdf` | desk background |
| `--sheet` | `#faf6ea` | inbox list surface |
| `--card` | `#fffdf4` | letter and reply paper |
| `--ink` | `#201b12` | text, strong rules, selected-row fill |
| `--ink-soft` | `#5f5744` | secondary text |
| `--ink-faint` | `#948a70` | tertiary text |
| `--rule` | `#d8cdb4` | hairlines |
| `--carmine` | `#b03d2e` | the single accent: brand stamp, primary CTA, saved-preference flashes, focus, SPECIMEN stamp |
| stamp ink blue | `#33557a` | Partnerships stamp only |
| stamp ink green | `#4a6b52` | Community stamp only |

### Structure rules

- **Radius 0.** Every element square. Sole exception: the brand stamp circle
  (1.5px dashed carmine ring — perforation).
- **Rules, not shadows.** 1px solid `--rule` hairlines; `3px double var(--ink)`
  for the two big seams (under the header, above the memory ledger). Exactly
  one shadow in the app: the reply card's hard offset `4px 4px 0 var(--rule)`.
  No blur shadows, no gradients, no glass.
- **The app frame is exactly viewport-height.** `.app-body` pins
  `grid-template-rows: minmax(0, 1fr)` and `.workspace` carries
  `min-height: 0`; the reading pane scrolls internally, never the window.
- **The used-memory slip.** "Memories used for this draft" sits on the reply
  card as a strip of `--paper` (a pasted slip), mono, with the em-dash list
  style shared with the drafting-memory ledger.
- **Selection = ink.** The selected mail row is solid `--ink` with paper text
  and an inverted stamp — no pastel fill, no blue bar.
- **Stamps, not chips.** Category labels are outlined uppercase mono in their
  ink color, transparent background, 1.5px currentColor border.
- **Avatars are squares.** 1px ink border, serif initials, transparent fill.

### Copy rules

- No eyebrow above a heading except the two sidebar filing labels.
- No explainer sentence that repeats its heading; the inbox subhead and the
  workspace footnote are deleted.
- The demo badge reads **SPECIMEN** (post-office stamp), carmine, the only
  rotated element (-2deg).
- Buttons carry words, not glyphs. The only permitted glyphs: `‹ ›` pager,
  `+`/`×` details marker, `↗` on the single external link.

### Banned list (must never reappear)

Inter/system-ui as identity font · any blue from the old palette · filled
pastel chips or pastel avatars · border-radius > 0 outside the brand stamp ·
blurred shadows · gradients · glassmorphism · eyebrow micro-labels beyond the
sidebar's two · icon glyphs on buttons · explainer sub-lines under headings ·
negative letter-spacing.
