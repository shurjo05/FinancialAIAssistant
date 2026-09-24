import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Turnstile } from "@marsidev/react-turnstile";
import { Check, Circle, Eye, EyeOff } from "lucide-react";
import { cn } from "../lib/utils";
import { Logo, ThemeToggle } from "./ui";

// Cloudflare Turnstile public site key (build-time). Unset → widget hidden and
// the backend skips verification, so signup behaves exactly as before.
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined;

// Mirrors backend app/core/password_policy.py (the server is the authority).
const MAX_PASSWORD = 64;
const PASSWORD_RULES: { label: string; test: (p: string) => boolean }[] = [
  { label: "8+ characters", test: (p) => p.length >= 8 },
  { label: "Uppercase letter", test: (p) => /\p{Lu}/u.test(p) },
  { label: "Lowercase letter", test: (p) => /\p{Ll}/u.test(p) },
  { label: "Number", test: (p) => /\p{Nd}/u.test(p) },
  { label: "Symbol", test: (p) => /[^\p{L}\p{N}\s]/u.test(p) },
];

interface Props {
  title: string;
  submitLabel: string;
  onSubmit: (email: string, password: string, captchaToken?: string) => Promise<void>;
  footer: ReactNode;
  /** Signup: CAPTCHA, password rules, and a confirm field. */
  isRegister?: boolean;
}

function PasswordRules({ password }: { password: string }) {
  return (
    <ul id="password-rules" className="grid grid-cols-2 gap-x-3 gap-y-1 px-0.5 pt-0.5" aria-label="Password requirements">
      {PASSWORD_RULES.map((r) => {
        const ok = r.test(password);
        return (
          <li key={r.label} className={cn("flex items-center gap-1.5 text-xs transition-colors", ok ? "text-up" : "text-muted")}>
            {ok ? <Check className="h-3.5 w-3.5 shrink-0" strokeWidth={2.6} /> : <Circle className="h-3 w-3 shrink-0" />}
            {r.label}
            <span className="sr-only">{ok ? "(met)" : "(not met)"}</span>
          </li>
        );
      })}
    </ul>
  );
}

export default function AuthForm({ title, submitLabel, onSubmit, footer, isRegister }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const navigate = useNavigate();

  const captchaOn = Boolean(isRegister && TURNSTILE_SITE_KEY);
  const rulesMet = PASSWORD_RULES.every((r) => r.test(password));
  const mismatch = isRegister && confirm.length > 0 && confirm !== password;
  const blocked =
    busy ||
    (captchaOn && !captchaToken) ||
    (isRegister && (!rulesMet || confirm !== password));

  const handle = async (e: FormEvent) => {
    e.preventDefault();
    if (blocked) return;
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
    "w-full rounded-xl border border-line bg-card px-3.5 py-2.5 text-base text-text placeholder:text-muted focus:border-accent-a focus:outline-none focus:ring-2 focus:ring-accent-a/25 sm:text-sm";
  const pwType = showPassword ? "text" : "password";

  return (
    <div className="home-gradient relative flex min-h-screen items-center justify-center px-4 py-16">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm">
        <Link to="/" className="mb-6 flex justify-center">
          <Logo className="text-xl" />
        </Link>

        <div className="rounded-2xl border border-line bg-card p-6 shadow-card sm:p-8">
          <h1 className="mb-5 font-display text-xl font-bold text-text">{title}</h1>
          <form onSubmit={handle} className="space-y-3">
            <input type="email" required placeholder="Email" value={email} autoComplete="email"
              onChange={(e) => setEmail(e.target.value)} className={field} />

            <div className="relative">
              <input
                type={pwType}
                required
                placeholder="Password"
                value={password}
                maxLength={isRegister ? MAX_PASSWORD : undefined}
                autoComplete={isRegister ? "new-password" : "current-password"}
                aria-describedby={isRegister ? "password-rules" : undefined}
                onChange={(e) => setPassword(e.target.value)}
                className={cn(field, "pr-11")}
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-r-xl text-muted hover:text-text"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            {isRegister && (
              <>
                <PasswordRules password={password} />
                <input
                  type={pwType}
                  required
                  placeholder="Confirm password"
                  value={confirm}
                  maxLength={MAX_PASSWORD}
                  autoComplete="new-password"
                  aria-invalid={mismatch || undefined}
                  onChange={(e) => setConfirm(e.target.value)}
                  className={cn(field, mismatch && "border-down focus:border-down focus:ring-down/25")}
                />
                {mismatch && <p className="text-xs text-down">Passwords don’t match.</p>}
              </>
            )}

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
              disabled={blocked}
              className={cn(
                "grad w-full rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-pop hover:brightness-110",
                blocked && "cursor-not-allowed opacity-50 hover:brightness-100",
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
