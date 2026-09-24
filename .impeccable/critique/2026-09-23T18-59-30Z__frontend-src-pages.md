---
target: "hero surfaces: Landing, Ask Jo, Overview"
total_score: 21
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 4
target_identity: "file:C:\\FinancialAIAssistant\\frontend\\src\\pages"
timestamp: 2026-09-23T18-59-30Z
slug: frontend-src-pages
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score (hero surfaces: Landing, Ask Jo, Overview @375px + desktop)
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | Full-page spinner on Overview; balance strip shifts layout; Jo replies not announced |
| 2 | Match System / Real World | 2 | ISO date range, raw "SUNSET APARTMENTS RENT" as top merchant, lowercase legends |
| 3 | User Control and Freedom | 2 | One-tap "Log out all devices" with no confirm; on demo it revokes every viewer's session |
| 4 | Consistency and Standards | 2 | Off-token chart colors; violet=spending/rent, red=health break both color rules |
| 5 | Error Prevention | 2 | Logout-all; Send enabled on empty input |
| 6 | Recognition Rather Than Recall | 2 | 7 icon-only nav items on mobile; voice presets unexplained |
| 7 | Flexibility and Efficiency | 2 | Chips vanish after first question; no accelerators |
| 8 | Aesthetic and Minimalist Design | 3 | Calm, on-system; dual gradient CTAs, unlabelled donut |
| 9 | Error Recovery | 3 | Good retry bubble and empty states |
| 10 | Help and Documentation | 1 | No path to evals, GitHub, or how Jo works |
| Total | | 21/40 | Acceptable |

## Design Specificity
Partly specific: the visual language (violet spent on Jo, Sora tabular figures, cut-corner bubbles) is authored; the compositions are category templates (hero + fake chat + three icon cards; 4-stat grid + donut + bar). "Computed, not generated" is only asserted in copy. Detector: CLI clean (0/8 files); in-page overlay 65 flags on /ask + /overview, mostly purple-palette/glow false positives against the chosen brand; true positives: 16 low-contrast (faint #6e6c82 on #16151f 3.6:1, incl. chart axis text), white on Orchid 3.8:1, skipped heading level. Landing overlay not run (session redirect). Mobile: 27/30 targets under 44px; chat input 15px (iOS zoom); Overview figures overflow (138px in 90px).

## Priority Issues
- [P0] Landing mock chat shows figures the demo can't reproduce ($412.68, $368.20, "Nobu"; first Ask Jo chip asks the same question); "Amex" unsupported; "No account linking required" stale. Fix: build preview from real demo answers, correct bank list. Command: clarify.
- [P1] Log out all devices on shared demo revokes all viewers' sessions; 32px thumb-zone icon, no confirm. Fix: server guard for demo, hide in demo, confirm for real users. Command: harden.
- [P1] Overview breaks at 375px: stat figures overflow, main scrolls sideways, masks truncate. Fix: fluid figures, one stat per row <400px, truncate names not masks. Command: adapt.
- [P1] ML claims have no visual proof: unlabelled donut, dead-end anomalies card at bottom, no model provenance, anomaly chip dropped when accounts exist. Fix: ranked category list, provenance line, linked anomalies card, keep anomaly chip, tool chips, How it works page. Commands: clarify, bolder.
- [P1] Ask Jo mobile fights the thumb: 6 elements before first question, composer floats mid-screen, 28px presets without aria-pressed, 15px input, icon-only nav. Fix: pinned composer with safe-area, single Voice control, shorter header, 16px input, bottom tab bar. Commands: adapt, layout.

## Persona Red Flags
- Recruiter Rae: competing gradient CTAs; no GitHub/eval link; preview contradicted by Jo; clipped Overview; ML indistinguishable from API call.
- Casey: landing nav buttons wrap to 60px; theme toggle 27px wide; logout/logout-all in thumb zone; 28px presets; iOS zoom on chat input.
- Jordan: 7 unlabelled icons, ⚠ Anomalies reads as error; presets unexplained; no closing CTA.
- Sam: chat input unlabelled with outline:none and no replacement ring; no live region; charts as unnamed role=application; custom buttons lack focus-visible; mobile nav relies on title.

## Minor Observations
Faint text on readable copy ("Works with…" ~4.0:1, net-worth caption ~3.6:1); landing preview blur + shadow-2xl; two competing hero figures (net worth vs Net); Top merchant shows rent; "last month" suggestion ambiguous (data ends Jun 2024); unused .grad-text.

## Questions to Consider
- Shouldn't every Jo answer show the tool call that produced it?
- Would one real demo answer on the landing prove more than a scripted fake?
- Does a phone viewer need Overview, or should Jo's answers embed the backing chart?
