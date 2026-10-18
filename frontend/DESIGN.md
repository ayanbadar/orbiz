# Orbiz design

Inspired by Wise's product surface: a pale sage canvas, white cards with a 24 px radius, near-black ink, and one lime-green CTA. The product should feel like a calm fintech magazine, not a dense bank dashboard.

Apply this when building or restyling UI. Tokens below are the source of truth. Map them onto the shadcn variables in `src/index.css` rather than hardcoding hex values in components.

Wise Sans is proprietary. Use **Geist Variable** (already loaded) at weight 800–900 for display headlines, and **Inter** for everything else: body, nav, buttons, forms, tables.

## Color

| Role             | Token              | Hex       | Use                                                                    |
| ---------------- | ------------------ | --------- | ---------------------------------------------------------------------- |
| CTA              | `primary`          | `#9fe870` | The only brand action color. Primary buttons only.                     |
| On CTA           | `on-primary`       | `#0e0f0c` | Text and icons on the lime button.                                     |
| CTA hover        | `primary-active`   | `#cdffad` | Hover and active fill for the primary button.                          |
| Green neutral    | `primary-neutral`  | `#c5edab` | Mid green fill when a surface needs a green tint that is not a button. |
| Green pale       | `primary-pale`     | `#e2f6d5` | Soft tints and positive badge backgrounds.                             |
| Ink              | `ink`              | `#0e0f0c` | Headings, default text, outline borders.                               |
| Ink deep         | `ink-deep`         | `#163300` | Text on positive surfaces.                                             |
| Body             | `body`             | `#454745` | Secondary copy.                                                        |
| Mute             | `mute`             | `#868685` | Captions, placeholders, fine print.                                    |
| Canvas           | `canvas`           | `#ffffff` | Cards, nav, inputs.                                                    |
| Canvas soft      | `canvas-soft`      | `#e8ebe6` | Page background and sage feature cards.                                |
| Positive         | `positive`         | `#2ead4b` | Success indicator. Not the CTA green.                                  |
| Positive deep    | `positive-deep`    | `#054d28` | Text on positive badges.                                               |
| Warning          | `warning`          | `#ffd11a` | Caution.                                                               |
| Warning deep     | `warning-deep`     | `#b86700` | Pressed warning.                                                       |
| Warning content  | `warning-content`  | `#4a3b1c` | Text on warning surfaces.                                              |
| Negative         | `negative`         | `#d03238` | Errors and destructive actions.                                        |
| Negative deep    | `negative-deep`    | `#a72027` | Pressed destructive.                                                   |
| Negative darkest | `negative-darkest` | `#a7000d` | Strongest destructive text.                                            |
| Negative bg      | `negative-bg`      | `#320707` | Destructive callout and negative badge fill.                           |
| Accent orange    | `accent-orange`    | `#ffc091` | Illustration and highlight only.                                       |
| Accent cyan      | `accent-cyan`      | `#38c8ff` | Illustration only.                                                     |

Lime is never a success color and never sits on a green background. Put it on sage, white, or ink.

## Type

| Token            | Face  | Size  | Weight | Line height | Tracking | Use in Orbiz                          |
| ---------------- | ----- | ----- | ------ | ----------- | -------- | ------------------------------------- |
| `display-mega`   | Geist | 126px | 900    | 107.1px     | 0        | Marketing or demo-welcome hero only.  |
| `display-xxl`    | Geist | 96px  | 900    | 81.6px      | 0        | Rare brand moment.                    |
| `display-xl`     | Geist | 64px  | 900    | 54.4px      | 0        | Sign-in and empty-workspace headline. |
| `display-lg`     | Geist | 47px  | 400    | 70.5px      | -0.108px | Lighter supporting display.           |
| `display-md`     | Geist | 40px  | 900    | 34px        | 0        | Section headlines.                    |
| `display-sm`     | Inter | 32px  | 600    | 38.4px      | -0.96px  | Page titles inside the app.           |
| `display-xs`     | Inter | 24px  | 600    | 31.2px      | -0.48px  | Card and dialog titles.               |
| `body-lg`        | Inter | 20px  | 400    | 30px        | 0        | Lead paragraphs.                      |
| `body-md`        | Inter | 16px  | 400    | 24px        | 0        | Default body and inputs.              |
| `body-md-strong` | Inter | 16px  | 600    | 24px        | 0        | Emphasized body.                      |
| `body-sm`        | Inter | 14px  | 400    | 20px        | 0        | Secondary copy and table cells.       |
| `body-sm-strong` | Inter | 14px  | 600    | 20px        | 0        | Nav links and badges.                 |
| `caption`        | Inter | 12px  | 400    | 16px        | 0        | Table headers, meta, fine print.      |
| `button-md`      | Inter | 16px  | 600    | 24px        | 0        | Button labels.                        |

Load Inter with `font-feature-settings: "calt"`. Hero and section display stays at weight 900. In-app headings stay Inter 600.

## Space, radius, elevation

Spacing scale: 2, 4, 8, 12, 16, 24, 32, 48 px.

| Radius          | Value  | Use                                      |
| --------------- | ------ | ---------------------------------------- |
| `sm`            | 8px    | Sidebar rows, small chips.               |
| `md`            | 12px   | Inputs.                                  |
| `lg`            | 16px   | Mid-size containers.                     |
| `xl`            | 24px   | Buttons and cards. Default radius.       |
| `pill` / `full` | 9999px | Status badges and circular icon buttons. |

Page bands use 48 px vertical padding. Card interiors use 24 px. Content width centers near 1200 px.

Elevation is surface contrast, not shadow. The sage page holds white cards. Borders are a 1 px ink line, used on inputs, outline buttons, and outlined cards. Shadows stay off ordinary cards. Modals and toasts may use a soft shadow.

## Components

**Primary button.** Background `#9fe870`, text `#0e0f0c`, Inter 16/600, padding 12 px 24 px, radius 24 px. Hover `#cdffad`. About 48 px tall.

**Secondary button.** Background `#e8ebe6`, text `#0e0f0c`, same type, padding, and radius.

**Outline button.** White fill, ink text, 1 px ink border, same type, padding, and radius.

**Icon button.** White circle, ink icon.

**Input.** White fill, ink text and 1 px ink border, Inter 16, padding 12 px 16 px, radius 12 px.

**Card.** White, ink text, padding 24 px, radius 24 px, no border, sitting on the sage canvas.

**Sage card.** `#e8ebe6` fill. **Pale green card.** `#e2f6d5` fill. **Dark card.** `#0e0f0c` fill with `#9fe870` text, for a single promotional moment.

**Nav.** White bar, ink text, Inter 14/600, padding 12 px 24 px.

**Sidebar row.** White, radius 8 px, padding 12 px 16 px. Active state uses a lime indicator, not a lime row fill.

**Table.** Header background `#e8ebe6`, caption type. Body cells Inter 14, padding 12 px 16 px, row rule `#e8ebe6`.

**Badges.** Positive: pale green background, `#054d28` text. Negative: `#320707` background, white text. Both are pills, Inter 14/600, padding 4 px 12 px.

**Footer.** Ink background, sage text, Inter 14, padding 48 px 24 px.

**Auth card, empty state, modal, toast.** Same 24 px card radius. Auth and empty states use the sage fill. Modals and toasts use white.

## Orbiz screens

- The workspace canvas is sage. Summary cards, order detail, and the assistant draft are white cards on that canvas.
- Page titles inside the app use `display-sm` or `display-xs`. Reserve `display-xl` and above for sign-in and the demo welcome.
- Order and payment status use the semantic palette. Paid is positive green. Awaiting payment is warning. Failed or cancelled is negative. Do not paint "paid" with the lime CTA.
- Sandbox payment callouts can use the dark card: ink surface, lime text, so the demo reads as a brand moment without looking like a live charge.
- The assistant draft review uses the outlined input style inside a white card.
- Below 768 px, stacks go to one column. From 768 px, grids can be two columns. From 1024 px, the app shell can sit beside a content grid.

## Rules

- One accent: lime for primary actions only.
- Display headlines that use Geist stay at weight 900.
- Buttons and cards use the 24 px radius. Do not use sharp corners on actions or cards.
- Sage page, white cards. That contrast is the elevation.
- Positive, warning, and negative carry status. Lime does not.
- Orange and cyan stay in illustrations, not in chrome or status.
