# Engineering Notes & Problems Solved

A running log of non-obvious problems hit while building this project, why they
happened, and how they were fixed. Kept for interview prep — each entry is a
"tell me about a challenge you faced" story.

---

## 1. Chosen training dataset became gated
- **Symptom:** `load_dataset("mitulshah/transaction-categorization")` failed with `DatasetNotFoundError: gated dataset`.
- **Cause:** the dataset owner enabled access-request gating after we scouted it; the Python client needs a token even when logged in on the website.
- **Fix:** switched to an open MIT alternative, `DoDataThings/us-bank-transaction-categories-v2` (68k rows, 17 US categories) — which also mapped more cleanly to our display taxonomy.
- **Takeaway:** verify a dataset is openly downloadable (not just "MIT") before designing around it; keep a backup option.

## 2. Inflated accuracy from train/test merchant overlap (data leakage)
- **Symptom:** the categorizer scored 99.85% accuracy — suspiciously high.
- **Cause:** a random train/test split scattered rows from the same ~500 base merchants into BOTH sets. The model memorized "SAFEWAY -> Groceries" in training and was then tested on more SAFEWAY rows — recognizing, not generalizing. (Not literal train-on-test; same *merchants*, different rows.)
- **Fix:** switched to a **merchant-disjoint split** (`GroupShuffleSplit` grouped by a merchant key) so test merchants never appear in training. Verified `overlap=0`. Accuracy dropped to an honest **95.76%** — the ~4-point gap was the memorization advantage.
- **Takeaway:** with grouped/entity data, split on the entity, not the row, or you leak identity and overstate generalization. This is the strongest interview story in the project.

## 3. Income vs Transfer — an irreducible text ambiguity
- **Symptom:** the model's one real weak spot — Income recall 0.46; income rows misclassified as Transfer (166), Subscription (112), Mortgage (77).
- **Cause:** deposit descriptions are ambiguous *as text* (`"PREAUTHORIZED DEPOSIT FROM DISCOVER BANK"` could be income or a transfer). No text-only model or dataset resolves this.
- **Fix:** a credit/debit override in the hybrid — the pipeline knows each transaction's direction (money in/out), which the text model never saw. A money-IN row predicted as an expense-only category (subscription/rent/grocery) is impossible, so it's corrected to income. Deliberately does NOT force income-vs-transfer, since both are legitimately money-in.
- **Takeaway:** some ambiguity is irreducible from one signal (text) but trivial with another (transaction direction). The hybrid architecture exists precisely so rules can supply context the model lacks.

## 4. Subscription detector: false positive from 2-occurrence groups
- **Symptom:** two Uber rides ~90 days apart were reported as a "quarterly subscription."
- **Cause:** any two data points form a single, "perfect" interval with zero amount variance — statistically indistinguishable from a real subscription.
- **Fix:** required a minimum of **3 occurrences** (`MIN_OCCURRENCES`) before calling something recurring. Two points is coincidence; three is evidence.
- **Takeaway:** be wary of statistics computed over tiny samples — a perfect fit on n=2 is meaningless.

## 5. Anomaly detector: false positives from low-value / multivariate outliers
- **Symptom:** IsolationForest flagged cheap transactions ($18 gas, $31 sandwich) with negative z-scores as anomalies.
- **Cause:** IsolationForest finds *multivariate* outliers (odd day-of-month / merchant frequency), but for a spending-anomaly feature the product only cares about unusually **high** spend.
- **Fix:** kept IsolationForest as the candidate generator, then filtered to high-side outliers only (`z_score >= 1.5`). Also raised contamination 0.03 -> 0.05 so multiple genuine spikes aren't missed.
- **Takeaway:** an unsupervised model's notion of "outlier" may not match the product's notion of "anomaly" — constrain its output to what the user actually cares about. After the fix the detector scored precision/recall/F1 = 1.00 **on a controlled synthetic benchmark with deliberately injected, labeled anomalies** — i.e. it reliably catches clear, large spikes by construction; this is not a claim about subtle or real-world anomaly detection.

## 6. "Subscriptions" total inflated by rent (product taxonomy)
- **Symptom:** the recurring-payment total read "$23,795/year in subscriptions" — dominated by an $1,800/mo rent charge.
- **Cause:** the detector finds *recurring payments*; rent/utilities are recurring but users don't think of them as "subscriptions."
- **Fix:** classify each recurring payment as `kind = "bill"` (rent/utilities/insurance/fees) or `"subscription"` (everything else) from its category, and split them into two tabs. Subscriptions now reads $52.97/mo; bills $1,930/mo.
- **Takeaway:** detection and presentation are different concerns — the model can be "correct" while the framing misleads. Match categories to the user's mental model.

## 7. AI query layer: provider-agnostic with a guaranteed floor
- **Design:** `POST /api/query` answers NL questions via a provider chain — Gemini (function-calling) if a key is set, else a deterministic keyword engine — both calling the *same* data tools. Numerical/financial answers are **computed by deterministic DB tools rather than generated by the model**, which grounds the figures. (Tool *selection* or *interpretation* by the LLM can still be wrong — grounding constrains the numbers, not the reasoning.)
- **Why:** the app must work with zero API keys (portability/privacy), and financial figures should not be free-text generated by the model. Tool-calling grounds the numbers; the rule-based fallback guarantees the feature always works even with no LLM.
- **Takeaway:** for AI features over real data, "grounded via tools" + "graceful degradation" beats "call the LLM and hope." Same pattern scales to Ollama (local/private) later.

## 8. Retired model + live rate-limit fallback
- **Symptom:** first live Gemini call returned `404: gemini-2.0-flash is no longer available`; later, some queries in a rapid batch silently returned rule-based answers.
- **Cause:** (a) the pinned model name had been retired by Google; (b) the free tier's per-minute request limit was exceeded when firing several queries back-to-back (a multi-tool query makes several API round-trips).
- **Fix:** (a) updated the default model to `gemini-3.6-flash` (env-configurable so future bumps need no code change); (b) no fix needed for rate limits — the provider chain caught the 429 and fell back to the rule-based engine, exactly as designed. Confirmed each query works via Gemini when called individually.
- **Takeaway:** external model APIs change under you — keep the model name in config, not code. And graceful degradation isn't theoretical: the free-tier rate limit exercised the fallback path in a real run. For production, add retry/backoff + response caching.

## 9. Alembic batch migrations on SQLite require named constraints
- **Symptom:** the auth migration failed with `ValueError: Constraint must have a name`, rolled back, and left the DB at the previous revision (columns silently absent).
- **Cause:** SQLite can't `ALTER` a table to add a foreign key, so Alembic uses "batch" mode (recreate-table). Batch mode requires every constraint to have an explicit name, but autogenerate emitted `create_foreign_key(None, ...)`.
- **Fix:** gave each FK an explicit name (`fk_<table>_user_id_users`) in the migration (upgrade + downgrade). Verified the full chain applies and the `user_id` columns land. (A metadata-wide `naming_convention` is the longer-term fix for future migrations.)
- **Takeaway:** autogenerated migrations are a starting point, not gospel — Alembic literally prints "please adjust!". Always run the migration against a fresh DB before trusting it.

## 10. passlib is broken with modern bcrypt
- **Symptom:** password hashing raised `AttributeError: module 'bcrypt' has no attribute '__about__'` then a cascading `ValueError`; every auth test errored.
- **Cause:** passlib 1.7.x (effectively unmaintained) reads `bcrypt.__about__.__version__`, which bcrypt 4.1+ removed.
- **Fix:** dropped passlib and called the well-maintained `bcrypt` library directly (`hashpw`/`checkpw`), truncating to bcrypt's 72-byte limit explicitly so long inputs don't raise.
- **Takeaway:** a thin, well-maintained dependency beats a heavier abstraction that has gone stale. Prefer the primitive when the wrapper adds fragility, not value.

## 11. "Configurable for Postgres" wasn't the same as "portable"
- **Symptom:** the app read `DATABASE_URL` and looked Postgres-ready, but one query (`monthly_trend`) called `func.strftime("%Y-%m", ...)` — a SQLite-only function that would crash on the production Postgres.
- **Cause:** being *configurable* (swap the URL) is not the same as being *portable* (the SQL actually runs on the other engine). SQLite silently tolerated a dialect-specific call that Postgres doesn't have.
- **Fix:** replaced `strftime` with SQLAlchemy's dialect-agnostic `extract('year'/'month', ...)` — SQLAlchemy compiles it to `STRFTIME` on SQLite and `EXTRACT` on Postgres — grouping numerically and formatting the `YYYY-MM` label in Python. Then made the split *verifiable*: SQLite stays the fast default for the inner loop, but a CI job runs the **same** suite against a real `postgres:16` service container (`TEST_DATABASE_URL`), plus a migrations job that applies the Alembic chain to a fresh Postgres and runs `alembic check` for model/migration drift.
- **Takeaway:** parity you don't test is parity you don't have. Keep the fast local database, but gate merges on the production dialect so "works on my SQLite" can't reach prod.

## 12. Shipping a model to prod without bloating git or retraining on boot
- **Problem:** the 8.7 MB `categorizer.joblib` is gitignored (git handles large binaries badly), so it isn't in a clone or the Docker build context. But production must **not** retrain on startup — that needs the 68k-row dataset download, takes minutes, and is non-deterministic. The image needs the *one approved* artifact, pinned and traceable.
- **Fix:** publish the artifact as a **GitHub Release asset** (`model-v1`) — versioned, git-free, at a stable URL. Commit a small `model_metadata.json` (provenance: version, metrics, dataset, framework versions, git commit, **SHA-256**). A stdlib-only `scripts/fetch_model.py` downloads the pinned asset and **verifies the checksum**, and is idempotent (skips if present + matching); the Dockerfile runs it at build time. `train.py` regenerates the metadata on every run (preserving the release identity so version bumps are deliberate). `/api/health` reports which model version is loaded, or `rules-only` when absent.
- **Takeaway:** you don't need MLflow/S3/a registry to ship a model responsibly at this scale. A pinned release asset + a committed metadata record + a checksum gives you versioning, provenance, integrity, and reproducibility — the 90% that matters — with zero infra. Choose the artifact store that matches the problem's size.

## 13. One image, one origin: multi-stage build for a single-service deploy
- **Problem:** package the React SPA + FastAPI API as one deployable artifact, without shipping a bloated image or breaking features that read files outside `backend/`.
- **Decisions:**
  - **Multi-stage build** — a `node` stage builds the frontend to `dist/`; a `python` stage installs deps, fetches the pinned model, and copies the built static in. Only the final stage ships, so Node/npm never reach the runtime image.
  - **Runtime vs training deps split** — moved `datasets`/`matplotlib` to `requirements-ml.txt` (dev/CI only). The container installs `requirements.txt` (inference stack: sklearn+joblib), since nothing at runtime imports the training libs. Meaningfully smaller image.
  - **Build context = repo root, not `backend/`** — the image needs `frontend/`, `backend/`, *and* `data/` (the sample CSV resolves to `repo_root/data/…` via `parents[3]`). `COPY` can't escape the context, so the context must contain all three; the Dockerfile preserves the repo layout so that path still resolves in-container.
  - **Single-origin serving** — the app mounts the built static and adds an SPA fallback (`index.html` for non-`/api` paths) *after* the API routers, so `/api/*` wins and deep links like `/transactions` still load. Frontend already used relative `/api` URLs, so no client changes.
  - **Migrations run at deploy time, not build time** — there's no DB during `docker build`; compose (and later Render) run `alembic upgrade head` as a start-up/release step, then launch uvicorn.
- **Gotcha caught in verification:** detectors run as a FastAPI **background task**, so right after `load-sample` the real uvicorn server briefly reports 0 subscriptions/anomalies (they populate a moment later). The test suite never saw this because Starlette's `TestClient` runs background tasks synchronously — a genuine dev/prod behavior difference, not a bug.
- **Takeaway:** a single-service image is the least-moving-parts way to ship a full-stack app; the discipline is keeping the runtime image lean (drop build/training-only deps) and getting the deploy-time steps (migrations) out of build time.

## 14. Deploying to Render with a decoupled database + fail-fast prod config
- **Problem:** stand up a real, auto-deploying public URL without hard-coupling to one provider or shipping insecure defaults — and dodge Render's free-Postgres ~90-day expiry.
- **Decisions:**
  - **Database decoupled from the host** — the app runs on Render but Postgres is **Neon** (free tier, no expiry). Because the DB is just a `DATABASE_URL`, swapping providers is a config change, not code. A `field_validator` rewrites the provider's `postgresql://` / `postgres://` string to the `postgresql+psycopg://` driver form, so the connection string pastes in verbatim.
  - **Fail-fast prod secret** — a `model_validator` refuses to boot when `ENVIRONMENT=production` while `JWT_SECRET` is still the dev default. A misconfigured deploy crashes loudly at startup instead of silently signing tokens with a public secret. Render generates the real secret (`generateValue: true`).
  - **Infra as code** — `render.yaml` (Blueprint) declares the service, health check, env vars, and the deploy command, so setup is reviewable and reproducible instead of click-ops.
  - **Migrations as the start command** — `dockerCommand: alembic upgrade head && uvicorn … --port $PORT`. On the free single instance this is simplest and idempotent; noted that a paid/multi-instance plan should move it to `preDeployCommand` to avoid concurrent-migration races. Binds Render's injected `$PORT`.
  - **CD with a Docker-build gate** — merge to `main` → CI (tests + lint + a Docker image build that catches Dockerfile breakage) → Render builds → migrates → health-checks `/api/health` → routes traffic.
- **Takeaway:** treat the platform as replaceable — decouple the database, drive everything from env, and make bad prod config fail at boot. The result is a live URL with push-to-deploy, and an app that's already portable to the next host (the planned AWS App Runner target).

## 15. Making a silent fallback observable (and hardening the agent loop)
- **Symptom / risk:** the NL-query layer caught *every* Gemini failure with `except Exception: pass` and silently dropped to the rule-based engine. Rate-limit, bug, and bad tool-arg all looked identical and vanished — you couldn't tell *why* an answer was degraded, or even that it was.
- **Fixes (Phase 13):**
  - **Classify + log + surface the fallback reason** — a small `_classify_llm_error` buckets the failure (rate-limited / unavailable / timeout / error); we log it (never the question — it may be sensitive) and return `provider: "rule-based (gemini unavailable: <reason>)"` so the degradation is visible in the response itself.
  - **Bound the tool loop** — set `maximum_remote_calls` on the Gemini automatic-function-calling config, so a misbehaving loop can't run up cost; the ceiling is intentional, not an SDK default.
  - **Structured tool errors, not exceptions** — tools validate model-supplied args (clamp `kind`, reject malformed `YYYY-MM`) and return `{"error": ...}` the model can read and retry, instead of raising and forcing the whole request to fall back.
  - **Test the agentic path** — a mocked Gemini client (no live key) proves a forced failure falls back *with the logged reason* and increments the fallback counter — the path CI never exercised before (tests run key-less).
- **Observability added alongside:** stdlib-only **JSON logging** (a small custom formatter, no dependency), a **request-id + latency middleware** (logs path/status/latency, never payloads), a **DB-aware `/api/health`**, and an in-memory **`/api/metrics`** (query provider mix, fallback rate, tool-call count, LLM + ingest latency, low-confidence rate). Plus two efficiency wins: **gzip** on large JSON and a **batched INSERT** for ingest.
- **Takeaway:** "it silently kept working" is not the same as "it worked." Graceful degradation still has to be *observable* — log why you degraded, bound the loop, and give the model recoverable errors instead of swallowing them. And keep the tooling lean: JSON logs and in-memory counters beat pulling in Prometheus/LangChain at this scale.

## 16. Closing the ML loop: corrections as versioned training signal
- **Problem:** the categorizer is ~95% accurate, but there was no way for a user to fix a wrong label, and no way to capture those fixes as data to improve the model. A prediction is a dead end, not a loop.
- **Design (Phase 14):** a `PATCH /api/transactions/{id}/category` corrects the row *and* writes a `Correction` record — `original_category`, `corrected_category`, `original_confidence`, and crucially the **`model_version`** that made the prediction. The corrected row's confidence is set to `1.0` (human = ground truth) so it drops out of the review queue; the original confidence is preserved on the correction, so no extra column on `transactions` is needed. `GET /api/corrections` makes the store exportable.
- **Active learning:** a `low_confidence` filter surfaces the predictions the model was *least* sure about (`category_confidence < threshold`) — the rows most worth a human's attention, which is where correction effort pays off most.
- **Deliberately NOT automated:** corrections are stored and surfaced, but retraining stays a **manual, gated** step (export → review → retrain → re-publish the pinned model per Note 12). Auto-retraining on user edits would let a few mislabels poison the model with no review — a feature store / continuous-training pipeline is the wrong amount of machinery here.
- **Why `model_version` matters:** it ties each correction to the model that erred, so a future retrain can ignore mistakes a newer model already fixed, and you can measure error rate *per version*. That single field is what turns "a table of edits" into a real ML feedback loop.
- **Takeaway:** human-in-the-loop is mostly plumbing + discipline, not ML wizardry — capture the correction, stamp it with the model version, surface the low-confidence rows, and keep a human gate before anything reaches training.

## 17. A model-regression gate in CI (without retraining every commit)
- **Problem:** code changes to the ML/taxonomy/hybrid path could quietly drop categorizer quality, and nothing would catch it before merge. But retraining on every PR (68k rows) is slow and wasteful, and the deployed model is a pinned artifact anyway.
- **Design (Phase 15):** a **separate** `ml-eval` workflow that runs only when `app/ml/**` or `categorizer.py` changes (or manually). It **evaluates the pinned model** — never retrains: `fetch_model` pulls the release artifact, `eval_categorizer.py` reproduces the *same* merchant-disjoint test split (seed 42) the model was scored on, predicts, computes native + display macro-F1, and **fails the build if either drops more than `TOLERANCE` (0.03) below the baseline** recorded in `model_metadata.json`. The HF dataset is cached between runs.
- **Why this shape:** the gate re-verifies the pinned artifact still performs *and* catches regressions in the code that can change per commit (taxonomy mapping, rule/override logic, split integrity). Keeping it off the main CI means normal PRs aren't slowed by a dataset download. The baseline living in `model_metadata.json` means "what good looks like" is versioned alongside the model.
- **Verified both directions:** on the current model it reproduces 0.9456 native / 0.9300 display and exits 0; with an impossible baseline injected it prints `REGRESSION detected` and exits 1 — so the gate genuinely bites, not just decorates.
- **Takeaway:** a regression gate doesn't need a training pipeline — evaluate the pinned artifact against a versioned baseline on a fixed split, tolerance-bounded, and only when the relevant code changes. Cheap, deterministic, and it actually blocks a bad merge.

## 18. Security pass: revocable JWTs, rate limits, and triaging a scanner finding
- **Token revocation (the real fix):** stateless JWTs meant a stolen/compromised token was valid for its full 24h with no way to cut it off — bad for a financial app. Added a per-user `token_version`: tokens carry a `ver` claim, `get_current_user` rejects any token whose `ver` ≠ the user's current version, and **"log out all devices"** + **password change** bump it — instantly killing every outstanding token. Near-zero cost because the request already loads the user. Chose this over a per-device session registry: it covers the security-critical case (revoke now) without the extra table/plumbing.
- **Rate limiting (slowapi):** per-IP on `/login` + `/register` (brute-force / enumeration), per-user on `/api/query` (LLM-budget abuse). Per-user keying works by stashing `user_id` on `request.state` in the auth dependency, which resolves before slowapi's key function runs. Disabled in tests so login-heavy fixtures aren't throttled; one dedicated test flips it on.
- **Triaging a scanner finding honestly:** `pip-audit` flagged `ecdsa` (PYSEC-2026-1325, transitive via `python-jose`, **no fix released**). Rather than pin-and-pray or disable the gate, verified it **doesn't apply** — we sign with HS256, so the ECDSA path is never exercised — and ignored *that specific advisory* with the reasoning documented in CI + `SECURITY.md`. (Migrating to `PyJWT` would drop the dep entirely; noted as future cleanup.)
- **The honest-limits doc:** `SECURITY.md` records what's built *and* what's deferred with rationale (RLS, per-device sessions, email-verification anti-enumeration) — because "I evaluated RLS and deferred it because my isolation is tested and RLS is Postgres-only with a silent-no-op footgun" is a stronger position than a half-wired backstop.
- **Takeaway:** security work is judgment as much as code — add the control that matches the real threat (revocation, rate limits), and when a scanner fires, *investigate applicability* and document the call rather than blanket-suppressing or blindly bumping.

## 19. Conversation memory, and why a wrong fallback is worse than a retry
- **Problem:** Jo was stateless, so follow-ups like "what about February?" failed. Once memory existed, the old safety net became a hazard: if Gemini failed, the deterministic engine answered the *latest message alone*, so a follow-up got a confident, context-free, often wrong reply.
- **Design (Phase 21):** server-side `Conversation` / `Message` tables with per-user isolation and a bounded, token-trimmed context window (~12 turns, text only, so Jo re-calls tools for fresh numbers). The shared demo stays stateless and sends its own short history. The fallback rule became **"is a key configured?"**: no key means offline mode and the deterministic engine *is* the answer; key set means any Gemini failure raises a typed `AIUnavailable` surfaced as a retryable 503, rendered as a Retry button, and a failed send persists nothing.
- **Free-tier reality:** quotas are per model (~5 RPM / 20 RPD each), so a **model chain** falls through on quota (429), retired-model (404 / "no longer available"), and transient 5xx errors, but never on client errors that would fail identically everywhere. A daily call cap counts **only successful** calls, so an outage doesn't burn budget.
- **Takeaway:** graceful degradation has to preserve correctness, not just availability. When the fallback can't see the context, "please retry" is the honest answer.

## 20. Alembic drift from one missing keyword
- **Symptom:** CI's `alembic check` went red on main after the Jo merge. The migration created the new foreign keys with `ondelete="CASCADE"`, but the models declared plain `ForeignKey(...)`, so autogenerate saw a difference.
- **Fix:** declare `ondelete="CASCADE"` on the model columns (model-only change, no new migration), and keep the named constraints from Note 9.
- **Takeaway:** the drift check earns its keep on exactly this kind of one-word mismatch. Also: fix forward on main rather than reverting a merge, since reverting a merge commit makes re-merging the branch painful.

## 21. Signup abuse prevention, and local config reaching into the tests
- **Why now (Phase 17):** a paid Gemini key turns mass account creation into a budget DoS. 2FA protects existing logins, not signup volume, so the controls go on registration: **Cloudflare Turnstile** (verified server-side, fail-closed, skipped when no secret so local runs stay zero-key) and a bundled **disposable-email blocklist**. Email verification was deferred (needs an email provider).
- **Gotcha 1:** Vite `VITE_*` variables are baked in at *build* time, so the site key needed a Docker `ARG` and a Render build variable, not just a runtime env var.
- **Gotcha 2:** after adding the real secret to local `backend/.env`, unrelated auth tests failed. pydantic-settings reads `.env` in tests too, so CAPTCHA switched on and every test registration was rejected. Fixed by neutralizing optional integration keys in `conftest.py` before the app imports.
- **Takeaway:** tests must not inherit a developer's local secrets. Pin the environment the suite runs in.

## 22. Plaid sandbox: one pipeline, encrypted tokens
- **Design (Phase 18):** Link → public-token exchange → cursor-based `/transactions/sync`. The ingest path was refactored into `persist_rows()` so Plaid rows flow through the *same* categorize → persist → detect pipeline as CSV rows; Plaid's own category labels are ignored in favor of our model (one taxonomy, and it shows the model generalizing to a new source). Plaid's sign convention already matched ours (positive = money out).
- **Secrets at rest:** access tokens are **Fernet-encrypted** in the database and decrypted just-in-time. No key configured means an ephemeral dev key with a warning; production must set a stable one.
- **Balances (Phase 22):** `/accounts/get` (cached balances, free) instead of `/accounts/balance/get` (billed per call in production), refreshed on every sync. Credit and loan balances count as money owed, so net worth = assets − liabilities. The demo gets clearly labelled synthetic accounts so the demo path shows the feature, and a `bank_connected` flag lets connections made before balances existed load them with one refresh.
- **Takeaway:** reuse the pipeline, not just the UI. A second data source should be a new adapter, not a second system.

## 23. Designing for the 60-second phone demo
- **Problem (Phase 23):** the real audience is a recruiter looking at a phone for about a minute. A structured design critique (design review + automated detector + live measurements at 375px) scored the key screens 21/40: Overview overflowed, 27 of 30 tap targets were under 44px, the landing's scripted chat quoted numbers the demo couldn't reproduce, and nothing on screen *showed* the grounding or the model.
- **Fixes:** a bottom tab bar, a composer pinned above it, fluid figures, a ranked category list instead of a hover-only donut, and every Jo answer showing the tools it called (`Computed via list_subscriptions()`). The fake chat was removed and a public How it works page states the eval method and the model's known weak spot. Contrast was measured, not eyeballed: violet text on dark was 2.8:1, so a text-safe violet token was added, and the dark gradient was deepened until white button text cleared 4.5:1.
- **Shared-demo guards:** the demo is one account used by every visitor, so "log out all devices" (which revokes every token) and "clear all data" are refused server-side for it, not just hidden.
- **Takeaway:** make the claim visible where the user already is, and treat a shared demo account as multi-tenant: any destructive action on it is an action against every viewer.
