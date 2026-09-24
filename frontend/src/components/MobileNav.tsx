import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { LogOut, Menu, Moon, ShieldOff, Sun, X } from "lucide-react";
import { cn } from "../lib/utils";
import { PRIMARY_NAV, SECONDARY_NAV } from "../lib/nav";
import { useTheme } from "../lib/theme";
import { useSignOut } from "../hooks/useSignOut";
import { isDemo } from "../services/api";
import { ConfirmDialog } from "./ui";

const tabClass = (active: boolean) =>
  cn(
    "flex min-h-14 flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-a/60",
    active ? "text-text" : "text-muted",
  );

/** The icon's pill background carries the active state, so it reads at a glance. */
function TabIcon({ icon: Icon, active }: { icon: typeof Menu; active: boolean }) {
  return (
    <span className={cn("grid h-7 w-12 place-items-center rounded-full transition-colors", active && "bg-accent-a/[0.16]")}>
      <Icon className={cn("h-5 w-5", active && "text-accent-a")} />
    </span>
  );
}

const sheetRow =
  "flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-[15px] font-medium text-text transition-colors hover:bg-line-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60";

/** "More": the secondary pages plus theme and sign-out, as a bottom sheet. */
function MoreSheet({ onClose }: { onClose: () => void }) {
  const { theme, toggle } = useTheme();
  const { signOut, signOutEverywhere } = useSignOut();
  const [confirmAll, setConfirmAll] = useState(false);
  const firstRef = useRef<HTMLAnchorElement>(null);
  const demo = isDemo();

  useEffect(() => {
    firstRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 md:hidden" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 motion-safe:animate-[fade-in_160ms_ease-out]" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="More"
        onClick={(e) => e.stopPropagation()}
        className="absolute inset-x-0 bottom-0 rounded-t-3xl border-t border-line bg-card px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2 shadow-card motion-safe:animate-[sheet-up_220ms_cubic-bezier(0.16,1,0.3,1)]"
      >
        <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line" aria-hidden />
        <div className="flex items-center justify-between px-3 pb-1">
          <h2 className="font-display text-base font-semibold text-text">More</h2>
          <button onClick={onClose} aria-label="Close" className="grid size-11 place-items-center rounded-xl text-muted hover:text-text">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav aria-label="More pages" className="space-y-0.5">
          {SECONDARY_NAV.map(({ to, label, icon: Icon }, i) => (
            <NavLink
              key={to}
              to={to}
              ref={i === 0 ? firstRef : undefined}
              onClick={onClose}
              className={({ isActive }) => cn(sheetRow, isActive && "bg-accent-a/[0.14] [&_svg]:text-accent-a")}
            >
              <Icon className="h-5 w-5 text-muted" /> {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-2 space-y-0.5 border-t border-line-soft pt-2">
          <button onClick={toggle} className={sheetRow}>
            {theme === "dark" ? <Sun className="h-5 w-5 text-muted" /> : <Moon className="h-5 w-5 text-muted" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <button onClick={signOut} className={sheetRow}>
            <LogOut className="h-5 w-5 text-muted" /> {demo ? "Leave the demo" : "Log out"}
          </button>
          {!demo && (
            <button onClick={() => setConfirmAll(true)} className={sheetRow}>
              <ShieldOff className="h-5 w-5 text-muted" /> Log out all devices
            </button>
          )}
        </div>
      </div>

      {confirmAll && (
        <ConfirmDialog
          title="Log out everywhere?"
          message="This signs you out on every device and browser, including this one."
          confirmLabel="Log out all devices"
          onCancel={() => setConfirmAll(false)}
          onConfirm={signOutEverywhere}
        />
      )}
    </div>
  );
}

/** Phone navigation: a bottom tab bar (four pages + More), within thumb reach. */
export default function MobileNav() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const moreActive = SECONDARY_NAV.some((n) => pathname.startsWith(n.to));

  return (
    <>
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {PRIMARY_NAV.map(({ to, label, icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => tabClass(isActive)}>
            {({ isActive }) => (
              <>
                <TabIcon icon={icon} active={isActive} />
                {label}
              </>
            )}
          </NavLink>
        ))}
        <button
          onClick={() => setOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={open}
          className={tabClass(moreActive || open)}
        >
          <TabIcon icon={Menu} active={moreActive || open} />
          More
        </button>
      </nav>
      {open && <MoreSheet onClose={() => setOpen(false)} />}
    </>
  );
}
