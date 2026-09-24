import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { GithubMark, Logo, ThemeToggle } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { GITHUB_URL } from "../lib/nav";
import { cn } from "../lib/utils";

// Figures come from backend/app/ml/model_metadata.json and reports/ — keep in sync.
const PIPELINE = [
  {
    title: "Ingest",
    body: "Upload a CSV from Chase, Bank of America, Capital One, or any generic export, or connect a bank through Plaid’s sandbox. Every format is normalized to one schema: positive amounts are money out, negative are money in.",
  },
  {
    title: "Categorize",
    body: "A model trained for this project labels every transaction. Below 50% confidence it defers to keyword rules, and a credit can never be filed as a bill.",
  },
  {
    title: "Detect",
    body: "Recurring charges are found from their timing and amounts, then split into subscriptions and bills. An IsolationForest flags spending that doesn’t fit your pattern.",
  },
  {
    title: "Ask",
    body: "Jo, the assistant, chooses which data tools to call. The tools run real queries on your transactions, so every figure in an answer is computed, not written by the model.",
  },
];

const TOOLS = [
  "get_spending_by_category", "get_total", "top_merchants", "compare_periods",
  "list_subscriptions", "list_recurring_bills", "list_anomalies", "account_balances",
];

const PRODUCTION = [
  ["Accounts and isolation", "JWT auth with bcrypt, and every query scoped to the signed-in user."],
  ["Data", "PostgreSQL in production, schema managed by Alembic migrations, with drift checked in CI."],
  ["Delivery", "GitHub Actions runs tests, linting, and a model-accuracy gate before Docker deploys to Render."],
  ["Abuse and secrets", "Cloudflare Turnstile and a disposable-email block on signup; Plaid tokens encrypted at rest."],
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-12 first:mt-8">
      <h2 className="font-display text-xl font-bold tracking-tight text-text">{title}</h2>
      <div className="mt-3 space-y-4 text-[15px] leading-relaxed text-muted">{children}</div>
    </section>
  );
}

function Figure({ value, label }: { value: string; label: string }) {
  return (
    // dt before dd for valid markup; column-reverse shows the figure first.
    <div className="flex min-w-0 flex-col-reverse">
      <dt className="mt-2 text-sm leading-snug text-muted">{label}</dt>
      <dd className="num text-[clamp(1.5rem,7vw,2rem)] font-bold leading-none text-text">{value}</dd>
    </div>
  );
}

function Body() {
  return (
    <article className="mx-auto max-w-3xl">
      <header>
        <h1 className="font-display text-[clamp(1.75rem,6vw,2.5rem)] font-bold leading-tight tracking-tight text-text [text-wrap:balance]">
          How JoMoney works
        </h1>
        <p className="mt-3 max-w-[60ch] text-base leading-relaxed text-muted">
          Every number Jo tells you is computed from your own transactions. This is the machinery
          behind that, with the evaluation numbers and how they were measured.
        </p>
      </header>

      <Section title="From statement to answer">
        <ol className="relative space-y-6 border-l border-line pl-6">
          {PIPELINE.map((step, i) => (
            <li key={step.title} className="relative">
              <span className="num absolute -left-[37px] grid h-6 w-6 place-items-center rounded-full border border-line bg-card text-xs font-semibold text-text">
                {i + 1}
              </span>
              <h3 className="font-display text-base font-semibold text-text">{step.title}</h3>
              <p className="mt-1">{step.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="The categorizer is a real model">
        <p>
          TF-IDF features (word and character n-grams) feed a logistic regression, trained on
          68,000 labeled bank transactions from an open, MIT-licensed dataset.
        </p>
        <dl className="grid grid-cols-1 gap-6 rounded-2xl border border-line bg-card p-5 shadow-card sm:grid-cols-3">
          <Figure value="95.8%" label="accuracy on 1,695 merchants the model never saw in training" />
          <Figure value="0.93" label="macro-F1 across the app’s 13 categories" />
          <Figure value="33.9%" label="accuracy of the keyword-rule baseline it replaced" />
        </dl>
        <p>
          <strong className="font-semibold text-text">How it was measured.</strong> The test set is
          merchant-disjoint: no merchant in it appears in training, so the score reflects
          merchants the model has genuinely never seen rather than memorized names.
        </p>
        <p>
          <strong className="font-semibold text-text">Known weak spot.</strong> Income is recalled
          only 46% of the time, because a paycheck and a transfer can read alike. At inference, the
          transaction’s direction settles it: money coming in is never filed as a bill.
        </p>
      </Section>

      <Section title="Answers are grounded, not generated">
        <p>
          Jo runs on Gemini with function calling. The model decides which tool to call; the tool
          runs a query scoped to your account and returns the figure. Each answer shows the tools
          it used.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {TOOLS.map((t) => (
            <code key={t} className="rounded-md bg-accent-a/10 px-2 py-1 font-mono text-xs text-accent-ink">{t}()</code>
          ))}
        </div>
        <p>
          With no API key, a deterministic engine calls the same tools, so the app still works
          offline. If the AI service is down, Jo says so and offers a retry rather than guessing.
        </p>
      </Section>

      <Section title="Detectors">
        <p>
          <strong className="font-semibold text-text">Subscriptions and bills.</strong> A merchant
          charged at least three times at a steady interval, for a consistent amount, is
          recurring. Rent and utilities are classed as bills; streaming, gyms, and software as
          subscriptions.
        </p>
        <p>
          <strong className="font-semibold text-text">Anomalies.</strong> An IsolationForest with
          guardrails: income, transfers, and rent are skipped, and only unusually high spending is
          flagged. On a small synthetic benchmark it caught all 5 injected anomalies with no false
          alarms. That’s a controlled test, not a claim about real-world accuracy.
        </p>
      </Section>

      <Section title="Built like production software">
        <dl className="divide-y divide-line-soft rounded-2xl border border-line bg-card px-5 shadow-card">
          {PRODUCTION.map(([k, v]) => (
            <div key={k} className="py-4 sm:grid sm:grid-cols-[11rem_1fr] sm:gap-4">
              <dt className="font-medium text-text">{k}</dt>
              <dd className="mt-1 sm:mt-0">{v}</dd>
            </div>
          ))}
        </dl>
        <p>
          The demo runs on synthetic sample data, and bank connections use Plaid’s sandbox with
          test institutions only.
        </p>
      </Section>

      <div className="mt-12 flex flex-wrap gap-3 border-t border-line pt-8">
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line bg-card px-4 text-sm font-medium text-text transition-colors hover:border-accent-a/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
        >
          <GithubMark className="h-4 w-4" /> Read the code on GitHub
        </a>
      </div>
    </article>
  );
}

/** Public header, used when a signed-out visitor arrives from the landing page. */
function PublicHeader() {
  const { demo } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const startDemo = async () => {
    setBusy(true);
    try {
      await demo();
      navigate("/ask");
    } catch {
      setBusy(false);
    }
  };

  return (
    <header className="flex items-center gap-3 py-5">
      <Link to="/" aria-label="JoMoney home" className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60">
        <Logo />
      </Link>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle className="size-11" />
        <button
          onClick={startDemo}
          disabled={busy}
          className={cn(
            "grad inline-flex min-h-11 items-center gap-1.5 rounded-xl px-4 text-sm font-semibold text-white shadow-pop hover:brightness-110 disabled:opacity-60",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
          )}
        >
          {busy ? "Loading…" : <>Try the demo <ArrowRight className="h-4 w-4" /></>}
        </button>
      </div>
    </header>
  );
}

export default function HowItWorks() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <Body />;
  return (
    <div className="min-h-[100dvh] bg-bg px-4 pb-16 md:px-8">
      <div className="mx-auto max-w-3xl">
        <PublicHeader />
        <Body />
      </div>
    </div>
  );
}
