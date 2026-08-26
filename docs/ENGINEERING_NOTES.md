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
