import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { AlertTriangle, ChevronRight, RefreshCw, ShoppingBag } from "lucide-react";
import { api } from "../services/api";
import { Card, NoData, Skeleton } from "../components/ui";
import { AccountsPanel } from "../components/Accounts";
import { CategoryRanking } from "../components/CategoryRanking";
import { cn, fmtRange, fmtUSD, titleCase } from "../lib/utils";
import { useTokenColor } from "../lib/useTokenColor";

const tooltipStyle = {
  background: "rgb(var(--card))",
  border: "1px solid rgb(var(--line))",
  borderRadius: 12,
  color: "rgb(var(--text))",
  fontSize: 13,
};

const monthLabel = (ym: string) =>
  new Date(ym + "-01T00:00:00").toLocaleDateString("en-US", { month: "short" });

/** Four headline figures in one ledger block (fluid type so they never overflow). */
function Totals({ spending, income, net, rate }: { spending: number; income: number; net: number; rate: number }) {
  const cells = [
    { label: "Spent", value: fmtUSD(spending), tone: "" },
    { label: "Earned", value: fmtUSD(income), tone: "text-up" },
    { label: "Net", value: fmtUSD(net), tone: net >= 0 ? "text-up" : "text-down" },
    { label: "Savings rate", value: `${rate}%`, tone: "" },
  ];
  return (
    <Card className="p-4 sm:p-5">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4 xl:grid-cols-4">
        {cells.map((c) => (
          <div key={c.label} className="min-w-0">
            <dt className="text-sm text-muted">{c.label}</dt>
            <dd className={cn("num mt-1 truncate text-[clamp(1.05rem,5.2vw,1.5rem)] font-bold leading-tight", c.tone)}>
              {c.value}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function MonthlyTrend({ data }: { data: { month: string; income: number; spending: number }[] }) {
  const income = useTokenColor("--up");
  const spending = useTokenColor("--muted");
  const axis = useTokenColor("--muted");
  const grid = useTokenColor("--line");

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="font-display font-semibold text-text">Month by month</h2>
        <div className="flex gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: income }} />Earned</span>
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: spending }} />Spent</span>
        </div>
      </div>
      <div className="mt-3 h-56 sm:h-64" role="img" aria-label="Bar chart of money earned and spent per month">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 0, left: -12, bottom: 0 }} barGap={2}>
            <CartesianGrid stroke={grid} vertical={false} />
            <XAxis dataKey="month" tickFormatter={monthLabel} fontSize={12} tick={{ fill: axis }} axisLine={false} tickLine={false} />
            <YAxis fontSize={12} width={44} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} tick={{ fill: axis }} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={(v, name) => [fmtUSD(Number(v)), name === "income" ? "Earned" : "Spent"]}
              labelFormatter={(l) => monthLabel(String(l))}
              cursor={{ fill: "rgb(var(--text) / 0.04)" }}
              contentStyle={tooltipStyle}
            />
            <Bar dataKey="income" fill={income} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="spending" fill={spending} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

/** A finding that leads somewhere, instead of a dead stat tile. */
function FindingLink({ to, icon: Icon, title, detail }: { to: string; icon: typeof AlertTriangle; title: string; detail: string }) {
  return (
    <Link
      to={to}
      className="group flex min-h-16 items-center gap-3 rounded-2xl border border-line bg-card p-4 shadow-card transition-colors hover:border-accent-a/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
    >
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent-a/10 text-accent-a">
        <Icon className="h-5 w-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-text">{title}</span>
        <span className="block truncate text-sm text-muted">{detail}</span>
      </span>
      <ChevronRight className="h-5 w-5 shrink-0 text-muted transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

function OverviewSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading your dashboard">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="mt-2 h-4 w-52" />
      <Skeleton className="mt-6 h-44" />
      <Skeleton className="mt-4 h-28" />
      <div className="mt-4 grid gap-4 lg:grid-cols-2"><Skeleton className="h-72" /><Skeleton className="h-72" /></div>
    </div>
  );
}

export default function Overview() {
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary });
  const byCat = useQuery({ queryKey: ["byCategory"], queryFn: api.byCategory });
  const monthly = useQuery({ queryKey: ["monthly"], queryFn: api.monthly });

  if (summary.isLoading) return <OverviewSkeleton />;
  if (!summary.data || summary.data.transaction_count === 0) return <NoData />;

  const s = summary.data;
  const anomalies = s.anomaly_count;

  return (
    <div>
      <header className="mb-5">
        <h1 className="font-display text-2xl font-bold tracking-tight text-text">Overview</h1>
        {s.date_range.start && s.date_range.end && (
          <p className="mt-1 text-sm text-muted">
            {fmtRange(s.date_range.start, s.date_range.end)} · {s.transaction_count} transactions
          </p>
        )}
      </header>

      <AccountsPanel />

      <Totals spending={s.total_spending} income={s.total_income} net={s.net} rate={s.savings_rate} />

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <FindingLink
          to="/anomalies"
          icon={AlertTriangle}
          title={anomalies === 1 ? "1 unusual transaction" : `${anomalies} unusual transactions`}
          detail="Flagged by the anomaly detector"
        />
        <FindingLink
          to="/subscriptions"
          icon={RefreshCw}
          title={`${s.subscription_count} subscriptions · ${s.bill_count} bills`}
          detail="Recurring charges found automatically"
        />
        {s.top_merchant && (
          <FindingLink
            to="/transactions"
            icon={ShoppingBag}
            title={`Most spent at ${titleCase(s.top_merchant.merchant)}`}
            detail={`${fmtUSD(s.top_merchant.total)} excluding rent and bills`}
          />
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {byCat.data ? <CategoryRanking data={byCat.data.by_category} limit={6} /> : <Skeleton className="h-72" />}
        {monthly.data ? <MonthlyTrend data={monthly.data} /> : <Skeleton className="h-72" />}
      </div>
    </div>
  );
}
