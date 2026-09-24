---
name: JoMoney
description: A precise ledger you can talk to. Calm surfaces, instrument-set figures, violet spent only on intelligence.
colors:
  jo-violet: "#7a28c9"
  orchid: "#a736d6"
  jo-violet-dark: "#9b44e0"
  orchid-dark: "#b03ed6"
  violet-ink: "#7a28c9"
  violet-ink-dark: "#c496ff"
  ledger-green: "#12a66b"
  ledger-green-dark: "#45e08b"
  overdraft-red: "#dc2626"
  overdraft-red-dark: "#f87171"
  caution-amber: "#b45309"
  caution-amber-dark: "#fbbf24"
  lavender-mist: "#f5f5fb"
  paper: "#ffffff"
  hairline: "#e7e6f1"
  hairline-soft: "#eeedf6"
  ink: "#16151f"
  slate-muted: "#6c6a80"
  slate-faint: "#9b99ad"
  night: "#09090f"
  night-surface: "#0f0e17"
  night-card: "#16151f"
  night-hairline: "#262435"
  night-hairline-soft: "#1d1c2a"
  moon-ink: "#eceaf6"
  moon-muted: "#9e9cb4"
  moon-faint: "#6e6c82"
typography:
  display:
    fontFamily: "Sora, system-ui, sans-serif"
    fontSize: "clamp(38px, 6vw, 62px)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Sora, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Sora, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.35
  figure:
    fontFamily: "Sora, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.02em"
    fontFeature: "\"tnum\""
  body:
    fontFamily: "Instrument Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.625
  label:
    fontFamily: "Instrument Sans, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.33
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  2xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.jo-violet}"
    textColor: "{colors.paper}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
    typography: "{typography.label}"
  button-ghost:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    typography: "{typography.body}"
  card:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "20px"
  chip:
    textColor: "{colors.slate-muted}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
    typography: "{typography.label}"
  nav-item-active:
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  chat-bubble-user:
    backgroundColor: "{colors.jo-violet}"
    textColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "10px 16px"
  chat-bubble-jo:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "12px 16px"
---

# Design System: JoMoney

## Overview

**Creative North Star: "The Talking Ledger"**

JoMoney should feel like a precise ledger that happens to talk back. The ledger part is quiet: near-white lavender or near-black surfaces, hairline borders, generous rounding, and money set in a tabular display face so every figure lines up like an instrument reading. The talking part is Jo, and Jo is the only thing allowed to be loud. The violet-to-orchid gradient marks intelligence and primary action, and almost nothing else.

The system is dark-first but fully symmetric: every token has a light and a dark value, switched by `data-theme` on the root, with `prefers-color-scheme` honored until the user picks. Density is moderate. Screens are built from soft-cornered cards on a tinted background, with one clear figure per card and supporting text in muted slate. The only atmospheric moment is the landing and auth backdrop, a gradient that falls from white (or black) into violet.

Soft and confident: controls are rounded and tactile, borders do the structural work, and shadows stay ambient. Nothing is glassy, noisy, or animated for its own sake; motion is limited to state transitions and a pulsing "thinking" indicator.

**Key Characteristics:**
- Violet/orchid gradient reserved for Jo, the logo spark, and primary actions.
- Money always in Sora with tabular numerals.
- Hairline-bordered cards (16px radius) on a lavender-tinted or near-black ground.
- Green for money in, red for money out/owed, never used decoratively.
- Symmetric light and dark themes from one set of RGB-channel tokens.

## Colors

A cool, faintly lavender neutral scale carries the interface; one violet-to-orchid pair carries the brand.

### Primary
- **Jo Violet** (#7a28c9; dark #9b44e0): the brand. Start of the signature gradient, active navigation icon, focus rings, links, selected states, and the tint behind active items (14% alpha).
- **Orchid** (#a736d6; dark #b03ed6): end of the gradient. Never used alone as a fill. (Dark value deepened from #c24fe8 in Phase 23 so white button text clears 4.5:1.)
- **Violet Ink** (#7a28c9; dark #c496ff): violet used as *text* (links, tool-call chips). Jo Violet itself is only 2.8:1 on the dark ground, so text takes this lighter dark value; icons and fills keep Jo Violet.

### Tertiary
- **Ledger Green** (#12a66b; dark #45e08b): money in, positive net, met password rules. Semantic only.
- **Overdraft Red** (#dc2626; dark #f87171): money out that matters, amounts owed, destructive actions, errors. Semantic only.
- **Caution Amber** (#b45309; dark #fbbf24): needs attention but not an error: low-confidence categories to review, moderate anomalies. Semantic only.

### Neutral
- **Lavender Mist** (#f5f5fb) / **Night** (#09090f): the app background behind cards.
- **Paper** (#ffffff) / **Night Card** (#16151f): cards, inputs, chat bubbles, ghost buttons.
- **Night Surface** (#0f0e17; light: Paper): the sidebar and other chrome one step off the background.
- **Hairline** (#e7e6f1) / **Night Hairline** (#262435): every card, input, and divider border.
- **Hairline Soft** (#eeedf6) / **Night Hairline Soft** (#1d1c2a): hover fills, skeletons, in-card dividers.
- **Ink** (#16151f) / **Moon Ink** (#eceaf6): primary text and figures.
- **Slate Muted** (#6c6a80) / **Moon Muted** (#9e9cb4): secondary text, labels, subtitles.
- **Slate Faint** (#9b99ad) / **Moon Faint** (#6e6c82): placeholders, captions, metadata.

### Named Rules
**The Spent-On-Intelligence Rule.** The violet/orchid gradient appears only where Jo or a primary action lives: the logo spark, Jo's avatar, user chat bubbles, primary buttons, the active voice preset. If a gradient appears anywhere else, it is wrong.

**The Semantic Money Rule.** Green and red mean money direction or state (in/out, owed, met/unmet, error). They are never decoration, category colors, or brand accents.

## Typography

**Display Font:** Sora (with system-ui)
**Body Font:** Instrument Sans (with system-ui, -apple-system, Segoe UI)

**Character:** Sora is geometric and slightly wide, which makes headings and figures feel engineered. Instrument Sans is a calm, readable grotesk that stays out of the way. Loaded from Google Fonts at 400 to 800 (Sora) and 400 to 600 (Instrument Sans).

### Hierarchy
- **Display** (700, clamp(38px, 6vw, 62px), 1.02): the landing hero headline only, balanced wrapping.
- **Headline** (700, 24px, tight tracking): page titles (`PageHeader`).
- **Title** (600, 17px; 18px on auth and modals): card and section headings, usually in Slate Muted inside cards.
- **Figure** (700, 24px; 30px for the accounts net worth; tabular, -0.02em): every money amount. Applied with the `.num` class, which also works inline in body text.
- **Body** (400, 14px, 1.625): chat answers, descriptions, table cells. 15px in the chat input and landing chat bubbles.
- **Label** (500, 12px): chips, captions, checklist items, metadata.

### Named Rules
**The Instrument Figure Rule.** Money is always Sora with tabular numerals (`.num`), even inside a sentence. Proportional digits on a money figure is a bug.

## Layout

The app is a two-pane shell: a navigation rail on the left and a scrolling content column capped at 72rem (1152px) wide, padded 16px on phones and 32px from `md` (768px) up. The rail is 64px of icons below `md` and a 240px labelled sidebar above it.

Content is stacked cards in Tailwind's 4px rhythm: 16px gaps between cards, 20px padding inside them, 24px below page headers. Stat cards sit two-up on phones and four-up from `xl`; charts sit one-up, then two-up from `lg`. Ask Jo adds a 224px thread list from `lg` and a 256px balances panel from `xl`.

Breakpoints are Tailwind defaults (sm 640, md 768, lg 1024, xl 1280). The landing page uses a 72rem container with a two-column hero from `md`.

## Elevation & Depth

Depth comes from tonal layering first and ambient shadow second. Background, surface, and card are three distinct tones; hairline borders define every container; shadows are soft and low, adding lift rather than structure.

### Shadow Vocabulary
- **Card** (`box-shadow: 0 1px 2px rgb(20 19 31 / 0.04), 0 8px 24px rgb(20 19 31 / 0.05)`): every card, chat bubble, and the pinned chat input.
- **Pop** (`box-shadow: 0 12px 40px rgb(122 40 201 / 0.20)`): gradient elements only (primary buttons, the spark, active preset), as a violet under-glow.

### Named Rules
**The Border-Does-The-Work Rule.** Containers are defined by a 1px hairline, not by shadow. The Card shadow is barely there; if a surface needs a heavier shadow to separate, the tones are wrong.

## Shapes

Generously rounded, never pill-shaped except chips. Radii step with object size: 8px for small in-card controls and nav rows in threads, 12px for buttons, inputs, and nav items, 16px for cards, chat bubbles, and dropzones, 24px for the landing chat preview. Chat bubbles cut one corner to 6px on the speaker's side (bottom-right for the user, top-left for Jo) to show direction. Icon tiles are 36 to 40px squares at 12px radius, tinted with their accent at 10% alpha.

## Components

### Buttons
Soft, tactile, and clearly ranked.
- **Shape:** 12px radius, 10px by 16px padding, 14px medium label, icon gap 8px.
- **Primary:** the violet-to-orchid gradient, white text, Pop shadow; hover brightens by 10%.
- **Ghost:** Paper fill, 1px Hairline border, Ink text; hover tints the border to Jo Violet at 40%.
- **Destructive:** solid Overdraft Red, white text (clear-data confirmation only).
- **Focus / Disabled:** 2px Jo Violet ring at 60% on keyboard focus; disabled drops to 40 to 50% opacity.

### Chips
- **Style:** pill (full radius), 12px label, Slate Muted text on a 10% violet tint with a soft hairline, or a plain hairline outline (the "Sample" tag).
- **Suggestion chips** (Ask Jo): pill outline on Paper, 14px, hover shifts the border to violet.

### Cards / Containers
- **Corner Style:** 16px.
- **Background:** Paper / Night Card on the Lavender Mist / Night ground.
- **Shadow Strategy:** Card shadow (see Elevation).
- **Border:** 1px Hairline.
- **Internal Padding:** 20px (24px on modals and auth, 32px on auth from `sm`).
- **Hero stat variant:** 25% violet border with a faint violet-to-orchid wash (10 to 15%) for the single most important figure on a screen.

### Inputs / Fields
- **Style:** Paper fill, 1px Hairline, 12px radius, 10px by 14px padding.
- **Focus:** border turns Jo Violet with a 2px violet ring at 25%.
- **Error:** border and ring switch to Overdraft Red, with a 12px red message below.

### Navigation
- **Sidebar:** Night Surface panel with a hairline right edge. Items are 14px medium, 18px icons, 12px radius. Active: 14% violet tint, Ink text, violet icon. Idle: Slate Muted, hover to Hairline Soft fill. Theme toggle and log-out actions sit at the bottom.
- **Mobile:** currently the same rail collapsed to 64px of icons (to be replaced by a bottom tab bar in Phase 23).

### Chat (signature component)
Jo's conversation is the product's centerpiece. User bubbles are gradient with white text, right-aligned, bottom-right corner cut. Jo's bubbles are Paper cards with a hairline and Card shadow, top-left corner cut, preceded by the gradient spark avatar (28px). Jo's markdown renders bold figures in Ink semibold and tight bullet lists. Thinking state is a pulsing sparkle with "Jo is thinking…" in Slate Faint; failures show the message plus a ghost Retry button. The input is a pinned Paper bar with a 40px gradient send button.

## Do's and Don'ts

### Do:
- **Do** keep the gradient to Jo, the spark, and primary actions (The Spent-On-Intelligence Rule).
- **Do** set every money figure with `.num` (Sora, tabular numerals).
- **Do** define containers with a 1px hairline and the soft Card shadow, on a background one tone away.
- **Do** define every new color as RGB channels on `:root` with a matching dark value in both the `prefers-color-scheme` block and `[data-theme="dark"]`.
- **Do** mark synthetic data plainly (the outlined "Sample" chip) wherever sample balances or data appear.

### Don't:
- **Don't** use green or red for anything but money direction, state, or errors.
- **Don't** use Slate Faint / Moon Faint for text a user must read; it's below 4.5:1 contrast on cards. Captions and placeholders only.
- **Don't** introduce gradient text, glass or blur effects, or heavy shadows. The app uses none; the `.grad-text` utility is defined but unused, and the landing chat preview's backdrop blur and heavy shadow are the one exception, up for review in Phase 23.
- **Don't** add a new accent hue. Category colors in charts are the only multi-hue palette, and they stay inside charts and category badges.
