import { NavLink, useNavigate } from "react-router-dom";
import {
  Sparkles, LayoutDashboard, Receipt, PieChart, RefreshCw,
  AlertTriangle, Upload, LogOut, ShieldOff,
} from "lucide-react";
import { cn } from "../lib/utils";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";
import { Spark, ThemeToggle } from "./ui";

const links = [
  { to: "/ask", label: "Ask Jo", icon: Sparkles },
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/categories", label: "Categories", icon: PieChart },
  { to: "/subscriptions", label: "Subscriptions", icon: RefreshCw },
  { to: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { to: "/upload", label: "Upload", icon: Upload },
];

export default function Sidebar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleLogoutAll = async () => {
    try { await api.logoutAll(); } catch { /* best-effort; sign out anyway */ }
    logout();
    navigate("/login");
  };

  return (
    <aside className="flex w-16 shrink-0 flex-col border-r border-line bg-surface md:w-60">
      <div className="flex items-center gap-2.5 px-3 py-5 md:px-4">
        <Spark className="h-[22px] w-[22px] shrink-0" />
        <span className="hidden font-display text-lg font-bold tracking-tight text-text md:inline">JoMoney</span>
      </div>

      <nav className="flex-1 space-y-1 px-2 md:px-3">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                "justify-center md:justify-start",
                isActive
                  ? "bg-accent-a/[0.14] text-text [&_svg]:text-accent-a"
                  : "text-muted hover:bg-line-soft hover:text-text",
              )
            }
          >
            <Icon className="h-[18px] w-[18px] shrink-0 opacity-90" />
            <span className="hidden md:inline">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="space-y-1 px-2 pb-3 md:px-3">
        <div className="flex items-center justify-center pb-2 md:justify-between md:px-1">
          <span className="hidden text-xs text-faint md:inline">Private by design</span>
          <ThemeToggle />
        </div>
        <button
          onClick={handleLogout}
          title="Log out"
          className="flex w-full items-center justify-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-line-soft hover:text-text md:justify-start"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span className="hidden md:inline">Log out</span>
        </button>
        <button
          onClick={handleLogoutAll}
          title="Log out of every device (revokes all sessions)"
          className="flex w-full items-center justify-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-line-soft hover:text-text md:justify-start"
        >
          <ShieldOff className="h-4 w-4 shrink-0" />
          <span className="hidden md:inline">Log out all devices</span>
        </button>
      </div>
    </aside>
  );
}
