# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Responsive web app (React SPA served by FastAPI). **Phone is the primary demo surface**: the owner pulls it up on a phone for recruiters, so every flow must hold up at ~375px wide, not just desktop.

## Users

- **Primary: recruiters and hiring managers** for FinTech / AI Product / Data Science internships, usually seeing the live demo on a phone for about 60 seconds, often with the owner narrating. When audiences conflict, the recruiter's quick read wins.
- **Story user: someone managing their own money** who uploads a bank CSV or links a (sandbox) bank and wants to understand where it goes. The product is designed as if for them, because a credible product is the portfolio claim.

## Product Purpose

JoMoney turns messy bank data into answers. It normalizes CSVs from any bank (or pulls transactions through Plaid sandbox), categorizes every line with a trained ML model, detects recurring subscriptions/bills and spending anomalies, and lets you ask **Jo**, a conversational AI, questions about your money in plain English.

Success = in about a minute a recruiter comes away convinced that:
1. **It's real ML, not an API wrapper.** A trained categorizer and detectors with honest, leakage-free evaluation.
2. **The AI is grounded.** Jo's figures come from deterministic tools over the user's data, never invented.
3. **It's production-shaped.** Auth + per-user isolation, Postgres + migrations, CI/CD, a live deploy, abuse prevention, encrypted bank tokens.

Polish serves those three claims. It is not the claim itself.

## Positioning

A finance assistant whose answers are **computed, not generated**: an LLM (Gemini function-calling) picks the tools, but the numbers come from the database. Categorization comes from a model trained and evaluated in this project, not from the LLM or Plaid's labels. It also runs with zero API keys: without them the AI falls back to a deterministic engine.

## Operating Context

- **Demo path (the one that matters):** Landing → "Try the live demo" (shared demo account, sample data, no signup) → **Ask Jo** (the post-login home). Dashboards are secondary tabs to explore after.
- The owner usually holds the phone and narrates, but the flow has to make sense without narration.
- Real accounts: register (Turnstile CAPTCHA + disposable-email block) → upload CSV or connect a Plaid sandbox bank → dashboards + persistent Jo chat threads.
- Live at `askjomoney.site` (Render + Neon Postgres). Public GitHub repo; a README (Phase 19, still to write) will carry screenshots.

## Capabilities and Constraints

- **Pages:** Landing, Login/Register, Ask Jo (threads, 3 tone presets, retry on AI outage), Overview, Transactions (inline category correction), Categories, Subscriptions (subscriptions vs bills), Anomalies, Upload/Connect (CSV dropzone, Plaid sandbox, clear-all-data).
- **Ingestion:** CSV (Chase, BofA, Capital One, generic, messy) and Plaid **sandbox**: one bank connection per user, whose accounts merge into one transaction list.
- **Demo account:** stateless chat (nothing saved); real users get saved conversations.
- **AI limits:** Gemini free tier is tight (per-model RPM/RPD), mitigated by a multi-model fallback chain + daily cap; outages show a retryable error, never a context-free fallback answer.
- **Optional integrations are feature-flagged:** no keys means the feature is hidden, and the app still runs locally with zero keys.
- **Amount sign:** positive = money out, negative = money in.
- Stack: React + TS + Vite + Tailwind + Recharts + TanStack Query; FastAPI + SQLAlchemy + Alembic.

## Brand Commitments

- Product name **JoMoney**; the assistant is **Jo** and refers to itself as Jo. Repo/infra names (`FinancialAIAssistant`, Render `finance-ai`) stay as-is.
- Jo's voice: **warm but analytical**, concise, plain English, key figures in bold, stays on personal-finance topics. Presets: Friendly / Just the numbers / Coach.
- Light + dark themes, dark-first (set in the Phase 20 redesign).

## Evidence on Hand

- Categorizer: **95.8% accuracy / 94.6% macro-F1** on a merchant-disjoint split (vs ~34% keyword baseline), trained on the MIT-licensed `DoDataThings/us-bank-transaction-categories-v2` (68k rows). Reports in `backend/app/ml/reports/`.
- Anomaly detector: precision/recall/F1 = 1.00, **only on a controlled synthetic benchmark with injected labeled anomalies**. Always word it that way.
- Sample data is **synthetic** (`data/generate_sample_data.py`, 3 bank formats).
- Engineering decision log: `docs/ENGINEERING_NOTES.md`.
- **Absent, never fabricate:** real users, testimonials, customer logos, usage numbers, press, real-bank connections (Plaid is sandbox only), pricing.

## Product Principles

1. **Lead with Jo.** The grounded AI conversation is the differentiator and comes first; dashboards back it up.
2. **Every number is traceable.** Never show or imply a figure the tools didn't compute; say "not sure" rather than guess.
3. **Honest claims only.** Sandbox is called sandbox, synthetic is called synthetic, evals are stated with their method.
4. **Phone-first for the demo.** If it doesn't work one-handed at 375px, it isn't done.
5. **Degrade gracefully.** Missing keys, rate limits, and outages get a clear, recoverable state, never a broken page.
