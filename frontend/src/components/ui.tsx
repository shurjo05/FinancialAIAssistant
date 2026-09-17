import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";
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

/* ── Controls ──────────────────────────────────────────────────────────── */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" };
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
        "w-full rounded-xl border border-line bg-card px-3.5 py-2.5 text-sm text-text placeholder:text-faint",
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

export function StatCard({
  label, value, sub, tone, hero, accent,
}: {
  label: string; value: string; sub?: string;
  tone?: "up" | "down"; hero?: boolean; accent?: string;
}) {
  return (
    <Card className={cn("p-5", hero && "border-accent-a/25 bg-gradient-to-br from-accent-a/15 to-accent-b/10")}>
      <p className="text-sm font-medium text-muted">{label}</p>
      <p
        className={cn(
          "num mt-2.5 text-2xl font-bold leading-tight",
          tone === "up" && "text-up",
          tone === "down" && "text-down",
        )}
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </p>
      {sub && <p className="mt-1.5 text-xs text-faint">{sub}</p>}
    </Card>
  );
}

export function CategoryBadge({ category }: { category: string }) {
  const color = colorFor(category);
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize"
      style={{ backgroundColor: `${color}1f`, color }}
    >
      {category}
    </span>
  );
}

/* ── Feedback / states ─────────────────────────────────────────────────── */
export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-faint">
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
      <h3 className="font-display text-lg font-semibold text-text">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-muted">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function NoData() {
  return (
    <EmptyState
      title="No transactions yet"
      message="Upload a bank or card CSV to see your spending, subscriptions, and insights."
      action={
        <Link to="/upload" className="grad inline-flex items-center rounded-xl px-4 py-2 text-sm font-medium text-white shadow-pop">
          Upload a CSV
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
