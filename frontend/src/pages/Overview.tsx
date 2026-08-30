import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import { api } from "../services/api";
import { Card, StatCard, Spinner, NoData, PageHeader } from "../components/ui";
import { fmtUSD, colorFor } from "../lib/utils";

export default function Overview() {
  const summary = useQuery({ queryKey: ["summary"], queryFn: api.summary });
  const byCat = useQuery({ queryKey: ["byCategory"], queryFn: api.byCategory });
  const monthly = useQuery({ queryKey: ["monthly"], queryFn: api.monthly });

  if (summary.isLoading) return <Spinner label="Loading your dashboard…" />;
  if (!summary.data || summary.data.transaction_count === 0) return <NoData />;

  const s = summary.data;
  const pieData = Object.entries(byCat.data?.by_category ?? {})
    .map(([name, value]) => ({ name, value }));

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle={
          s.date_range.start
            ? `${s.date_range.start} → ${s.date_range.end}`
            : undefined
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total spending" value={fmtUSD(s.total_spending)} accent="#dc2626" />
        <StatCard label="Total income" value={fmtUSD(s.total_income)} accent="#16a34a" />
        <StatCard label="Net" value={fmtUSD(s.net)} accent={s.net >= 0 ? "#16a34a" : "#dc2626"} />
        <StatCard label="Savings rate" value={`${s.savings_rate}%`} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-2 font-semibold text-slate-700">Spending by category</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={2}>
                {pieData.map((d) => <Cell key={d.name} fill={colorFor(d.name)} />)}
              </Pie>
              <Tooltip formatter={(v) => fmtUSD(Number(v))} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <h3 className="mb-2 font-semibold text-slate-700">Monthly trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={monthly.data ?? []}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(v) => `$${v / 1000}k`} />
              <Tooltip formatter={(v) => fmtUSD(Number(v))} />
              <Legend />
              <Bar dataKey="income" fill="#16a34a" radius={[4, 4, 0, 0]} />
              <Bar dataKey="spending" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Top merchant"
          value={s.top_merchant?.merchant ?? "—"}
          sub={s.top_merchant ? fmtUSD(s.top_merchant.total) : undefined}
        />
        <StatCard
          label="Largest transaction"
          value={s.largest_transaction ? fmtUSD(s.largest_transaction.amount) : "—"}
          sub={s.largest_transaction?.merchant}
        />
        <StatCard
          label="Flags"
          value={`${s.anomaly_count} anomalies`}
          sub={`${s.subscription_count} subscriptions · ${s.bill_count} bills`}
        />
      </div>
    </div>
  );
}
