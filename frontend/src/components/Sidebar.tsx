import { useState } from "react";
import { NavLink } from "react-router-dom";
import { LogOut, ShieldOff } from "lucide-react";
import { cn } from "../lib/utils";
import { PRIMARY_NAV, SECONDARY_NAV, type NavItem } from "../lib/nav";
import { useSignOut } from "../hooks/useSignOut";
import { isDemo } from "../services/api";
import { ConfirmDialog, Spark, ThemeToggle } from "./ui";

const itemClass = (active: boolean) =>
  cn(
    "flex min-h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60",
    active ? "bg-accent-a/[0.14] text-text [&_svg]:text-accent-a" : "text-muted hover:bg-line-soft hover:text-text",
  );

function NavGroup({ items }: { items: NavItem[] }) {
  return (
    <div className="space-y-1">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} className={({ isActive }) => itemClass(isActive)}>
          <Icon className="h-[18px] w-[18px] shrink-0 opacity-90" />
          {label}
        </NavLink>
      ))}
    </div>
  );
}

/** Desktop navigation (md and up). Phones use MobileNav's bottom tab bar instead. */
export default function Sidebar() {
  const { signOut, signOutEverywhere } = useSignOut();
  const [confirmAll, setConfirmAll] = useState(false);
  const demo = isDemo();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-surface md:flex">
      <div className="flex items-center gap-2.5 px-4 py-5">
        <Spark className="h-[22px] w-[22px] shrink-0" />
        <span className="font-display text-lg font-bold tracking-tight text-text">JoMoney</span>
      </div>

      <nav aria-label="Main" className="flex-1 space-y-5 px-3">
        <NavGroup items={PRIMARY_NAV} />
        <div className="border-t border-line-soft pt-5">
          <NavGroup items={SECONDARY_NAV} />
        </div>
      </nav>

      <div className="space-y-1 px-3 pb-3">
        <div className="flex items-center justify-between px-1 pb-2">
          <span className="text-xs text-muted">{demo ? "Demo account" : "Private by design"}</span>
          <ThemeToggle />
        </div>
        <button onClick={signOut} className={itemClass(false) + " w-full"}>
          <LogOut className="h-4 w-4 shrink-0" /> Log out
        </button>
        {!demo && (
          <button onClick={() => setConfirmAll(true)} className={itemClass(false) + " w-full"}>
            <ShieldOff className="h-4 w-4 shrink-0" /> Log out all devices
          </button>
        )}
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
    </aside>
  );
}
