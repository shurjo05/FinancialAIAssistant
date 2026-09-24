import {
  useEffect, useRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type Ref,
} from "react";
import { Link } from "react-router-dom";
import { Loader2, Moon, Sparkles, Sun } from "lucide-react";
import { cn, colorFor } from "../lib/utils";
import { useTheme } from "../lib/theme";

/* ── Brand ─────────────────────────────────────────────────────────────── */
export function Spark({ className }: { className?: string }) {
  return (
    <span className={cn("grad grid place-items-center rounded-[7px] shadow-pop", className)}>
      <Sparkles className="h-[13px] w-[13px] text-white" strokeWidth={2.4} />
    </span>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 font-display text-lg font-bold tracking-tight text-text", className)}>
      <Spark className="h-[22px] w-[22px]" />
      JoMoney
    </span>
  );
}

/** GitHub's mark (lucide no longer ships brand icons). */
export function GithubMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden className={className}>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

/* ── Controls ──────────────────────────────────────────────────────────── */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost";
  ref?: Ref<HTMLButtonElement>;
};
export function Button({ variant = "ghost", className, ...props }: BtnProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60",
        "disabled:pointer-events-none disabled:opacity-40",
        variant === "primary"
          ? "grad text-white shadow-pop hover:brightness-110"
          : "border border-line bg-card text-text hover:border-accent-a/40",
        className,
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-line bg-card px-3.5 py-2.5 text-sm text-text placeholder:text-muted",
        "focus:border-accent-a focus:outline-none focus:ring-2 focus:ring-accent-a/25",
        className,
      )}
      {...props}
    />
  );
}

/* ── Surfaces ──────────────────────────────────────────────────────────── */
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("rounded-2xl border border-line bg-card shadow-card", className)}>{children}</div>;
}

export function Chip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border border-line-soft bg-accent-a/10 px-2.5 py-1 text-xs text-muted", className)}>
      {children}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  // Color lives in the dot; the label stays readable ink (category hues fail
  // contrast as text, e.g. utilities' yellow on white).
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line px-2 py-0.5 text-xs font-medium capitalize text-text">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colorFor(category) }} aria-hidden />
      {category}
    </span>
  );
}

/* ── Feedback / states ─────────────────────────────────────────────────── */
export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-muted">
      <Loader2 className="h-5 w-5 animate-spin" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-lg bg-line-soft", className)} />;
}

export function EmptyState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-card py-16 text-center">
      <h2 className="font-display text-lg font-semibold text-text">{title}</h2>
      <p className="mt-1.5 max-w-sm text-sm text-muted">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function NoData() {
  return (
    <EmptyState
      title="No transactions yet"
      message="Upload a bank or card CSV, or connect a sandbox bank, to see your spending, subscriptions, and insights."
      action={
        <Link to="/upload" className="grad inline-flex min-h-11 items-center rounded-xl px-4 text-sm font-medium text-white shadow-pop focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-card">
          Add transactions
        </Link>
      }
    />
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-text">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/** Blocking confirmation for consequential actions. Esc or the backdrop cancels. */
export function ConfirmDialog({
  title, message, confirmLabel, onConfirm, onCancel, busy, destructive,
}: {
  title: string; message: ReactNode; confirmLabel: string;
  onConfirm: () => void; onCancel: () => void; busy?: boolean; destructive?: boolean;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy) onCancel(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel, busy]);

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-black/50 p-4" onClick={busy ? undefined : onCancel}>
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-2xl border border-line bg-card p-6 shadow-card"
      >
        <h2 id="confirm-title" className="font-display text-lg font-semibold text-text">{title}</h2>
        <div className="mt-2 text-sm leading-relaxed text-muted">{message}</div>
        <div className="mt-5 flex justify-end gap-2">
          <Button ref={cancelRef} onClick={onCancel} disabled={busy} className="min-h-11">Cancel</Button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className={cn(
              "inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-medium text-white transition hover:brightness-110 disabled:opacity-50",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-card",
              destructive ? "bg-down" : "grad",
            )}
          >
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      aria-label="Toggle light or dark theme"
      title="Toggle theme"
      className={cn("grid h-9 w-9 place-items-center rounded-xl border border-line bg-card text-muted hover:text-text", className)}
    >
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
