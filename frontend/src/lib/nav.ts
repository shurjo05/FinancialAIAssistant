import {
  AlertTriangle, BookOpen, LayoutDashboard, PieChart, Receipt, RefreshCw, Sparkles, Upload,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

/** Primary destinations: the desktop sidebar's first group and the phone tab bar. */
export const PRIMARY_NAV: NavItem[] = [
  { to: "/ask", label: "Ask Jo", icon: Sparkles },
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/transactions", label: "Transactions", icon: Receipt },
  { to: "/upload", label: "Upload", icon: Upload },
];

/** Secondary destinations: the sidebar's second group and the phone "More" sheet. */
export const SECONDARY_NAV: NavItem[] = [
  { to: "/categories", label: "Categories", icon: PieChart },
  { to: "/subscriptions", label: "Subscriptions", icon: RefreshCw },
  { to: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { to: "/how-it-works", label: "How it works", icon: BookOpen },
];

export const GITHUB_URL = "https://github.com/shurjo05/FinancialAIAssistant";
