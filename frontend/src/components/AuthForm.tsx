import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Turnstile } from "@marsidev/react-turnstile";
import { cn } from "../lib/utils";
import { Logo, ThemeToggle } from "./ui";

// Cloudflare Turnstile public site key (build-time). Unset → widget hidden and
// the backend skips verification, so signup behaves exactly as before.
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined;

interface Props {
  title: string;
  submitLabel: string;
  onSubmit: (email: string, password: string, captchaToken?: string) => Promise<void>;
  footer: ReactNode;
  requireCaptcha?: boolean;
}

export default function AuthForm({ title, submitLabel, onSubmit, footer, requireCaptcha }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const navigate = useNavigate();

  const captchaOn = Boolean(requireCaptcha && TURNSTILE_SITE_KEY);

  const handle = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSubmit(email, password, captchaToken || undefined);
      navigate("/ask");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const field =
    "w-full rounded-xl border border-line bg-card px-3.5 py-2.5 text-sm text-text placeholder:text-faint focus:border-accent-a focus:outline-none focus:ring-2 focus:ring-accent-a/25";

  return (
    <div className="home-gradient relative flex min-h-screen items-center justify-center px-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm">
        <Link to="/" className="mb-6 flex justify-center">
          <Logo className="text-xl" />
        </Link>

        <div className="rounded-2xl border border-line bg-card p-8 shadow-card">
          <h1 className="mb-5 font-display text-xl font-bold text-text">{title}</h1>
          <form onSubmit={handle} className="space-y-3">
            <input type="email" required placeholder="Email" value={email}
              onChange={(e) => setEmail(e.target.value)} className={field} />
            <input type="password" required placeholder="Password" value={password}
              onChange={(e) => setPassword(e.target.value)} className={field} />
            {captchaOn && (
              <Turnstile
                siteKey={TURNSTILE_SITE_KEY!}
                onSuccess={setCaptchaToken}
                onExpire={() => setCaptchaToken("")}
                onError={() => setCaptchaToken("")}
                options={{ theme: "auto" }}
              />
            )}
            {error && <p className="text-sm text-down">{error}</p>}
            <button
              type="submit"
              disabled={busy || (captchaOn && !captchaToken)}
              className={cn(
                "grad w-full rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-pop hover:brightness-110",
                (busy || (captchaOn && !captchaToken)) && "opacity-50",
              )}
            >
              {busy ? "…" : submitLabel}
            </button>
          </form>
          <p className="mt-5 text-center text-sm text-muted">{footer}</p>
        </div>
      </div>
    </div>
  );
}
