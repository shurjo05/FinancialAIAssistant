# Engineering Notes & Problems Solved

A running log of non-obvious problems hit while building this project, why they
happened, and how they were fixed. Kept for interview prep — each entry is a
"tell me about a challenge you faced" story.

---

## 1. Repo cloned one level too deep
- **Symptom:** `git clone` created `C:\FinancialAIAssistant\FinancialAIAssistant\` — the repo nested inside the working folder.
- **Cause:** `git clone <url>` makes a folder named after the repo wherever it's run.
- **Fix:** moved contents (incl. hidden `.git`, `.gitignore`) up one level with `Get-ChildItem -Force | Move-Item`, removed the empty nested folder.
- **Takeaway:** `git clone <url> .` clones into the current directory; the trailing dot matters.

## 2. Packages installed into global Python instead of the venv
- **Symptom:** `fastapi` etc. landed in `C:\Python311` (global) and only partially in `.venv`.
- **Cause:** `pip install` targets whatever `pip` is first on PATH; a terminal opened before the venv existed still pointed at global.
- **Fix:** always install via the venv's interpreter explicitly: `.\.venv\Scripts\python.exe -m pip install ...`. Cleaned global with `pip uninstall -r requirements.txt`.
- **Takeaway:** `python -m pip` run through a specific interpreter can't target the wrong environment.

## 3. `datetime.date` name shadowing in the SQLAlchemy model
- **Symptom:** Pylance rejected `date: Mapped[date]` on the Transaction model.
- **Cause:** the column named `date` shadowed the imported `date` type inside the class, so the annotation resolved to the column, not the type.
- **Fix:** switched to a module import (`import datetime`) and referenced `datetime.date` — module-qualified, so nothing shadows it.
- **Takeaway:** when a field name collides with a type name, qualify the type through its module.

## 4. Chosen training dataset became gated
- **Symptom:** `load_dataset("mitulshah/transaction-categorization")` failed with `DatasetNotFoundError: gated dataset`.
- **Cause:** the dataset owner enabled access-request gating after we scouted it; the Python client needs a token even when logged in on the website.
- **Fix:** switched to an open MIT alternative, `DoDataThings/us-bank-transaction-categories-v2` (68k rows, 17 US categories) — which also mapped more cleanly to our display taxonomy.
- **Takeaway:** verify a dataset is openly downloadable (not just "MIT") before designing around it; keep a backup option.

## 5. Inflated accuracy from train/test merchant overlap (data leakage)
- **Symptom:** the categorizer scored 99.85% accuracy — suspiciously high.
- **Cause:** a random train/test split scattered rows from the same ~500 base merchants into BOTH sets. The model memorized "SAFEWAY -> Groceries" in training and was then tested on more SAFEWAY rows — recognizing, not generalizing. (Not literal train-on-test; same *merchants*, different rows.)
- **Fix:** switched to a **merchant-disjoint split** (`GroupShuffleSplit` grouped by a merchant key) so test merchants never appear in training. Verified `overlap=0`. Accuracy dropped to an honest **95.76%** — the ~4-point gap was the memorization advantage.
- **Takeaway:** with grouped/entity data, split on the entity, not the row, or you leak identity and overstate generalization. This is the strongest interview story in the project.

## 6. Income vs Transfer — an irreducible text ambiguity
- **Symptom:** the model's one real weak spot — Income recall 0.46; income rows misclassified as Transfer (166), Subscription (112), Mortgage (77).
- **Cause:** deposit descriptions are ambiguous *as text* (`"PREAUTHORIZED DEPOSIT FROM DISCOVER BANK"` could be income or a transfer). No text-only model or dataset resolves this.
- **Fix:** a credit/debit override in the hybrid — the pipeline knows each transaction's direction (money in/out), which the text model never saw. A money-IN row predicted as an expense-only category (subscription/rent/grocery) is impossible, so it's corrected to income. Deliberately does NOT force income-vs-transfer, since both are legitimately money-in.
- **Takeaway:** some ambiguity is irreducible from one signal (text) but trivial with another (transaction direction). The hybrid architecture exists precisely so rules can supply context the model lacks.

## 7. Subscription detector: false positive from 2-occurrence groups
- **Symptom:** two Uber rides ~90 days apart were reported as a "quarterly subscription."
- **Cause:** any two data points form a single, "perfect" interval with zero amount variance — statistically indistinguishable from a real subscription.
- **Fix:** required a minimum of **3 occurrences** (`MIN_OCCURRENCES`) before calling something recurring. Two points is coincidence; three is evidence.
- **Takeaway:** be wary of statistics computed over tiny samples — a perfect fit on n=2 is meaningless.

## 8. Anomaly detector: false positives from low-value / multivariate outliers
- **Symptom:** IsolationForest flagged cheap transactions ($18 gas, $31 sandwich) with negative z-scores as anomalies.
- **Cause:** IsolationForest finds *multivariate* outliers (odd day-of-month / merchant frequency), but for a spending-anomaly feature the product only cares about unusually **high** spend.
- **Fix:** kept IsolationForest as the candidate generator, then filtered to high-side outliers only (`z_score >= 1.5`). Also raised contamination 0.03 -> 0.05 so multiple genuine spikes aren't missed.
- **Takeaway:** an unsupervised model's notion of "outlier" may not match the product's notion of "anomaly" — constrain its output to what the user actually cares about. After the fix the detector scored precision/recall/F1 = 1.00 **on a controlled synthetic benchmark with deliberately injected, labeled anomalies** — i.e. it reliably catches clear, large spikes by construction; this is not a claim about subtle or real-world anomaly detection.

## 9. "Subscriptions" total inflated by rent (product taxonomy)
- **Symptom:** the recurring-payment total read "$23,795/year in subscriptions" — dominated by an $1,800/mo rent charge.
- **Cause:** the detector finds *recurring payments*; rent/utilities are recurring but users don't think of them as "subscriptions."
- **Fix:** classify each recurring payment as `kind = "bill"` (rent/utilities/insurance/fees) or `"subscription"` (everything else) from its category, and split them into two tabs. Subscriptions now reads $52.97/mo; bills $1,930/mo.
- **Takeaway:** detection and presentation are different concerns — the model can be "correct" while the framing misleads. Match categories to the user's mental model.

## 10. AI query layer: provider-agnostic with a guaranteed floor
- **Design:** `POST /api/query` answers NL questions via a provider chain — Gemini (function-calling) if a key is set, else a deterministic keyword engine — both calling the *same* data tools. Numerical/financial answers are **computed by deterministic DB tools rather than generated by the model**, which grounds the figures. (Tool *selection* or *interpretation* by the LLM can still be wrong — grounding constrains the numbers, not the reasoning.)
- **Why:** the app must work with zero API keys (portability/privacy), and financial figures should not be free-text generated by the model. Tool-calling grounds the numbers; the rule-based fallback guarantees the feature always works even with no LLM.
- **Takeaway:** for AI features over real data, "grounded via tools" + "graceful degradation" beats "call the LLM and hope." Same pattern scales to Ollama (local/private) later.

## 11. Retired model + live rate-limit fallback
- **Symptom:** first live Gemini call returned `404: gemini-2.0-flash is no longer available`; later, some queries in a rapid batch silently returned rule-based answers.
- **Cause:** (a) the pinned model name had been retired by Google; (b) the free tier's per-minute request limit was exceeded when firing several queries back-to-back (a multi-tool query makes several API round-trips).
- **Fix:** (a) updated the default model to `gemini-3.6-flash` (env-configurable so future bumps need no code change); (b) no fix needed for rate limits — the provider chain caught the 429 and fell back to the rule-based engine, exactly as designed. Confirmed each query works via Gemini when called individually.
- **Takeaway:** external model APIs change under you — keep the model name in config, not code. And graceful degradation isn't theoretical: the free-tier rate limit exercised the fallback path in a real run. For production, add retry/backoff + response caching.

## 12. Alembic batch migrations on SQLite require named constraints
- **Symptom:** the auth migration failed with `ValueError: Constraint must have a name`, rolled back, and left the DB at the previous revision (columns silently absent).
- **Cause:** SQLite can't `ALTER` a table to add a foreign key, so Alembic uses "batch" mode (recreate-table). Batch mode requires every constraint to have an explicit name, but autogenerate emitted `create_foreign_key(None, ...)`.
- **Fix:** gave each FK an explicit name (`fk_<table>_user_id_users`) in the migration (upgrade + downgrade). Verified the full chain applies and the `user_id` columns land. (A metadata-wide `naming_convention` is the longer-term fix for future migrations.)
- **Takeaway:** autogenerated migrations are a starting point, not gospel — Alembic literally prints "please adjust!". Always run the migration against a fresh DB before trusting it.

## 13. passlib is broken with modern bcrypt
- **Symptom:** password hashing raised `AttributeError: module 'bcrypt' has no attribute '__about__'` then a cascading `ValueError`; every auth test errored.
- **Cause:** passlib 1.7.x (effectively unmaintained) reads `bcrypt.__about__.__version__`, which bcrypt 4.1+ removed.
- **Fix:** dropped passlib and called the well-maintained `bcrypt` library directly (`hashpw`/`checkpw`), truncating to bcrypt's 72-byte limit explicitly so long inputs don't raise.
- **Takeaway:** a thin, well-maintained dependency beats a heavier abstraction that has gone stale. Prefer the primitive when the wrapper adds fragility, not value.

## 14. "Configurable for Postgres" wasn't the same as "portable"
- **Symptom:** the app read `DATABASE_URL` and looked Postgres-ready, but one query (`monthly_trend`) called `func.strftime("%Y-%m", ...)` — a SQLite-only function that would crash on the production Postgres.
- **Cause:** being *configurable* (swap the URL) is not the same as being *portable* (the SQL actually runs on the other engine). SQLite silently tolerated a dialect-specific call that Postgres doesn't have.
- **Fix:** replaced `strftime` with SQLAlchemy's dialect-agnostic `extract('year'/'month', ...)` — SQLAlchemy compiles it to `STRFTIME` on SQLite and `EXTRACT` on Postgres — grouping numerically and formatting the `YYYY-MM` label in Python. Then made the split *verifiable*: SQLite stays the fast default for the inner loop, but a CI job runs the **same** suite against a real `postgres:16` service container (`TEST_DATABASE_URL`), plus a migrations job that applies the Alembic chain to a fresh Postgres and runs `alembic check` for model/migration drift.
- **Takeaway:** parity you don't test is parity you don't have. Keep the fast local database, but gate merges on the production dialect so "works on my SQLite" can't reach prod.

## 15. Shipping a model to prod without bloating git or retraining on boot
- **Problem:** the 8.7 MB `categorizer.joblib` is gitignored (git handles large binaries badly), so it isn't in a clone or the Docker build context. But production must **not** retrain on startup — that needs the 68k-row dataset download, takes minutes, and is non-deterministic. The image needs the *one approved* artifact, pinned and traceable.
- **Fix:** publish the artifact as a **GitHub Release asset** (`model-v1`) — versioned, git-free, at a stable URL. Commit a small `model_metadata.json` (provenance: version, metrics, dataset, framework versions, git commit, **SHA-256**). A stdlib-only `scripts/fetch_model.py` downloads the pinned asset and **verifies the checksum**, and is idempotent (skips if present + matching); the Dockerfile runs it at build time. `train.py` regenerates the metadata on every run (preserving the release identity so version bumps are deliberate). `/api/health` reports which model version is loaded, or `rules-only` when absent.
- **Takeaway:** you don't need MLflow/S3/a registry to ship a model responsibly at this scale. A pinned release asset + a committed metadata record + a checksum gives you versioning, provenance, integrity, and reproducibility — the 90% that matters — with zero infra. Choose the artifact store that matches the problem's size.
