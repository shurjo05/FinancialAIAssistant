import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { GithubMark, Logo, ThemeToggle } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { GITHUB_URL } from "../lib/nav";
import { cn } from "../lib/utils";

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

const PIPELINE = [
  { verb: "Ingest", line: "CSV exports from Chase, Bank of America, Capital One, or any bank. Or connect one through Plaid’s sandbox." },
  { verb: "Categorize", line: "A model trained for this project labels every transaction." },
  { verb: "Detect", line: "Subscriptions, recurring bills, and spending that breaks your pattern." },
  { verb: "Ask", line: "Jo answers in plain English, with every figure pulled from your data." },
];

const TOOLS = [
  "get_spending_by_category", "get_total", "top_merchants", "compare_periods",
  "list_subscriptions", "list_recurring_bills", "list_anomalies", "account_balances",
];

const STACK = ["FastAPI", "PostgreSQL", "Alembic", "scikit-learn", "Gemini", "React", "GitHub Actions", "Docker", "Render"];

export default function Home() {
  const navigate = useNavigate();
  const { demo } = useAuth();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const startDemo = async () => {
    setBusy(true);
    setFailed(false);
    try {
      await demo();
      navigate("/ask");
    } catch {
      setBusy(false);
      setFailed(true);
    }
  };

  return (
    <div className="home-gradient min-h-[100dvh]">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* Nav: one line, one quiet action */}
        <nav className="flex items-center gap-2 py-4 sm:py-6">
          <Link to="/" aria-label="JoMoney home" className={cn("rounded-lg", focusRing)}>
            <Logo />
          </Link>
          <div className="ml-auto flex items-center gap-1 sm:gap-2">
            <Link to="/how-it-works" className={cn("hidden min-h-11 items-center rounded-xl px-3 text-sm font-medium text-muted hover:text-text sm:inline-flex", focusRing)}>
              How it works
            </Link>
            <ThemeToggle className="size-11 border-transparent bg-transparent" />
            <Link to="/login" className={cn("inline-flex min-h-11 items-center rounded-xl px-3 text-sm font-medium text-text hover:text-accent-ink", focusRing)}>
              Sign in
            </Link>
          </div>
        </nav>

        {/* Hero: headline, one sentence, one primary action */}
        <section className="pb-16 pt-10 motion-safe:animate-[rise_600ms_cubic-bezier(0.16,1,0.3,1)] sm:pb-24 sm:pt-20">
          <h1 className="max-w-[14ch] font-display text-[clamp(2.6rem,11vw,4.5rem)] font-bold leading-[1.02] tracking-[-0.03em] text-text [text-wrap:balance]">
            Ask your money anything.
          </h1>
          <p className="mt-5 max-w-[34ch] text-lg leading-relaxed text-muted sm:text-xl">
            JoMoney reads your bank statements and answers in plain English. Every figure is computed from your data, never guessed.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-3">
            <button
              onClick={startDemo}
              disabled={busy}
              className={cn("grad inline-flex min-h-12 items-center gap-2 rounded-xl px-6 text-base font-semibold text-white shadow-pop hover:brightness-110 disabled:opacity-60", focusRing)}
            >
              {busy ? "Opening the demo…" : <>Try the live demo <ArrowRight className="h-4 w-4" /></>}
            </button>
            <Link to="/register" className={cn("inline-flex min-h-11 items-center rounded-lg text-base font-medium text-text underline decoration-line underline-offset-4 hover:decoration-accent-a", focusRing)}>
              or create an account
            </Link>
          </div>
          {failed && (
            <p role="alert" className="mt-4 text-sm text-down">The demo didn’t start. Check your connection and try again.</p>
          )}
        </section>

        {/* The three claims, each shown with its own kind of evidence */}
        <section aria-labelledby="claims" className="border-t border-line py-14 sm:py-20">
          <h2 id="claims" className="max-w-[22ch] font-display text-[clamp(1.6rem,6vw,2.25rem)] font-bold leading-tight tracking-tight text-text">
            Three things worth checking.
          </h2>

          <div className="mt-10 grid gap-12 lg:grid-cols-12 lg:gap-x-10">
            <div className="lg:col-span-5">
              <p className="num text-[clamp(3.5rem,16vw,5.5rem)] font-bold leading-none tracking-[-0.04em] text-text">95.8%</p>
              <h3 className="mt-4 font-display text-lg font-semibold text-text">A trained model, not a wrapper</h3>
              <p className="mt-2 max-w-[42ch] leading-relaxed text-muted">
                Accuracy categorizing transactions from 1,695 merchants the model never saw in training. Keyword rules managed 33.9%.
              </p>
            </div>

            <div className="lg:col-span-7">
              <ul className="flex flex-wrap gap-1.5" aria-label="Jo's data tools">
                {TOOLS.map((t) => (
                  <li key={t}>
                    <code className="block rounded-md bg-accent-a/10 px-2 py-1 font-mono text-xs text-accent-ink">{t}()</code>
                  </li>
                ))}
              </ul>
              <h3 className="mt-5 font-display text-lg font-semibold text-text">Answers are computed, not generated</h3>
              <p className="mt-2 max-w-[48ch] leading-relaxed text-muted">
                Jo calls data tools that query your transactions, and each answer lists the ones it used. If the AI is down, it says so instead of guessing.
              </p>
            </div>
          </div>

          <div className="mt-14 border-t border-line-soft pt-10">
            <h3 className="font-display text-lg font-semibold text-text">Built like production software</h3>
            <p className="mt-2 max-w-[60ch] leading-relaxed text-muted">
              Accounts with per-user data isolation, Postgres with migrations, a CI pipeline that blocks model regressions, and bank tokens encrypted at rest.
            </p>
            <ul className="mt-5 flex flex-wrap gap-2" aria-label="Tech stack">
              {STACK.map((s) => (
                <li key={s} className="rounded-lg border border-line bg-card px-2.5 py-1 text-sm text-muted">{s}</li>
              ))}
            </ul>
          </div>
        </section>

        {/* Pipeline: a sequence, so it reads left to right (top to bottom on phones) */}
        <section aria-labelledby="pipeline" className="border-t border-line py-14 sm:py-20">
          <h2 id="pipeline" className="font-display text-[clamp(1.6rem,6vw,2.25rem)] font-bold leading-tight tracking-tight text-text">
            From statement to answer.
          </h2>
          <ol className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
            {PIPELINE.map((p) => (
              <li key={p.verb} className="border-t-2 border-accent-a/40 pt-4">
                <h3 className="font-display text-base font-semibold text-text">{p.verb}</h3>
                <p className="mt-1.5 text-[15px] leading-relaxed text-muted">{p.line}</p>
              </li>
            ))}
          </ol>
          <Link
            to="/how-it-works"
            className={cn("mt-10 inline-flex min-h-11 items-center gap-1.5 rounded-lg text-base font-medium text-accent-ink hover:underline underline-offset-4", focusRing)}
          >
            How it works, with the evaluation details <ArrowRight className="h-4 w-4" />
          </Link>
        </section>

        <footer className="flex flex-col gap-4 border-t border-line py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>A portfolio project. The demo runs on synthetic data.</p>
          <div className="flex items-center gap-1">
            <a href={GITHUB_URL} target="_blank" rel="noreferrer" className={cn("inline-flex min-h-11 items-center gap-2 rounded-lg px-2 font-medium text-text hover:text-accent-ink", focusRing)}>
              <GithubMark className="h-4 w-4" /> Source on GitHub
            </a>
            <Link to="/register" className={cn("inline-flex min-h-11 items-center rounded-lg px-2 font-medium text-text hover:text-accent-ink", focusRing)}>
              Create account
            </Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
