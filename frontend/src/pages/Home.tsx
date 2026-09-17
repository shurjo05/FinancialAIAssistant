import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, ListChecks, Check, Radar, Sun, Moon } from "lucide-react";
import { Logo } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../lib/theme";

function DemoBubble({ me, children }: { me?: boolean; children: React.ReactNode }) {
  return (
    <div className={`flex ${me ? "justify-end" : "justify-start"}`}>
      <div
        className={
          "max-w-[84%] rounded-2xl px-4 py-3 text-[14.5px] leading-relaxed " +
          (me
            ? "grad rounded-br-md text-white"
            : "rounded-bl-md border border-[rgb(var(--text)/0.1)] bg-[rgb(var(--text)/0.06)] text-text")
        }
      >
        {children}
      </div>
    </div>
  );
}

const FEATURES = [
  {
    icon: ListChecks,
    title: "Understands messy statements",
    body: "Every bank exports differently. JoMoney normalizes the mess and categorizes each line with a trained model — 95% accurate on merchants it has never seen.",
  },
  {
    icon: Check,
    title: "Answers you can trust",
    body: "Numbers are computed by real tools over your data, not written by the model. When it isn't sure, it tells you — and falls back to a deterministic engine.",
  },
  {
    icon: Radar,
    title: "Catches what you'd miss",
    body: "Recurring subscriptions, forgotten free trials, and unusual spikes — surfaced automatically, before they surprise you.",
  },
];

export default function Home() {
  const navigate = useNavigate();
  const { demo } = useAuth();
  const { theme, toggle } = useTheme();
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

  const ghost = "rounded-xl border border-[rgb(var(--text)/0.14)] bg-[rgb(var(--text)/0.05)] hover:border-[rgb(var(--text)/0.3)]";

  return (
    <div className="home-gradient min-h-screen">
      <div className="mx-auto max-w-6xl px-5">
        <nav className="flex items-center gap-5 py-6">
          <Logo />
          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={toggle}
              aria-label="Toggle light or dark theme"
              title="Toggle theme"
              className={`grid h-10 w-10 place-items-center rounded-xl text-muted hover:text-text ${ghost}`}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <Link to="/login" className={`px-4 py-2.5 text-sm font-medium ${ghost}`}>Sign in</Link>
            <Link to="/register" className="grad rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-pop hover:brightness-110">
              Create account
            </Link>
          </div>
        </nav>

        <section className="grid items-center gap-14 py-10 md:grid-cols-[1.05fr_1fr] md:py-16">
          <div>
            <h1 className="font-display text-[clamp(38px,6vw,62px)] font-bold leading-[1.02] tracking-tight [text-wrap:balance]">
              Ask your money anything.
            </h1>
            <p className="mt-5 max-w-[32ch] text-lg leading-relaxed text-muted">
              JoMoney reads your statements, learns your spending, and answers in plain English — every figure computed from your own data, never guessed.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button
                onClick={startDemo}
                disabled={busy}
                className="grad rounded-xl px-5 py-3 text-sm font-semibold text-white shadow-pop hover:brightness-110 disabled:opacity-60"
              >
                {busy ? "Loading demo…" : "Try the live demo"}
              </button>
              <Link to="/register" className={`px-5 py-3 text-sm font-semibold ${ghost}`}>Create account</Link>
            </div>
            <p className="mt-6 text-sm text-faint">Works with Chase, Amex, Capital One, or a plain CSV. No account linking required.</p>
          </div>

          <div className="rounded-3xl border border-[rgb(var(--text)/0.1)] bg-[rgb(var(--text)/0.05)] p-5 shadow-2xl backdrop-blur-md">
            <div className="mb-4 flex items-center gap-2 border-b border-[rgb(var(--text)/0.09)] pb-3.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[rgb(var(--text)/0.2)]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[rgb(var(--text)/0.2)]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[rgb(var(--text)/0.2)]" />
              <span className="ml-1.5 inline-flex items-center gap-1.5 text-xs text-faint">
                <Sparkles className="h-3.5 w-3.5" /> Ask Jo
              </span>
            </div>
            <div className="space-y-3">
              <DemoBubble me>How much did I spend on restaurants in March?</DemoBubble>
              <DemoBubble>
                You spent <b className="num">$412.68</b> on restaurants in March across 14 transactions — about 12% more than February (<b className="num">$368.20</b>).
              </DemoBubble>
              <DemoBubble me>Which of those was the biggest?</DemoBubble>
              <DemoBubble>Your largest was <b className="num">$96.40</b> at Nobu on Mar 22.</DemoBubble>
            </div>
          </div>
        </section>

        <section className="grid gap-8 py-10 pb-24 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title}>
              <span className="mb-3.5 grid h-9 w-9 place-items-center rounded-xl bg-[rgb(var(--text)/0.08)] text-accent-b">
                <Icon className="h-5 w-5" />
              </span>
              <h3 className="font-display text-[17px] font-semibold text-text">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
