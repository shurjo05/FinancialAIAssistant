import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Receipt, PieChart, RefreshCw, AlertTriangle,
  Sparkles, Upload, Wallet,
} from "lucide-react";
import { cn } from "../lib/utils";

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/categories", label: "Categories", icon: PieChart },
  { to: "/subscriptions", label: "Subscriptions", icon: RefreshCw },
  { to: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { to: "/ask", label: "Ask AI", icon: Sparkles },
  { to: "/upload", label: "Upload", icon: Upload },
];

export default function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-900 text-slate-300">
      <div className="flex items-center gap-2 px-5 py-5 text-white">
        <Wallet className="h-6 w-6 text-brand-500" />
        <span className="font-semibold leading-tight">Finance AI</span>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive ? "bg-brand-600 text-white" : "hover:bg-slate-800 hover:text-white",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <p className="px-5 py-4 text-xs text-slate-500">Local-first · private by design</p>
    </aside>
  );
}
