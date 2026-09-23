import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, CreditCard, Landmark, Loader2, PiggyBank, RotateCw, Wallet } from "lucide-react";
import { api } from "../services/api";
import type { AccountBalances, BankAccount } from "../types";
import { cn, fmtAgo, fmtUSD } from "../lib/utils";
import { useBalances } from "../hooks/useBalances";
import { Card, Skeleton } from "./ui";

function AccountIcon({ account }: { account: BankAccount }) {
  const Icon = account.is_liability ? CreditCard : account.subtype === "savings" ? PiggyBank : Landmark;
  return (
    <span
      className={cn(
        "grid h-9 w-9 shrink-0 place-items-center rounded-xl",
        account.is_liability ? "bg-down/10 text-down" : "bg-accent-a/10 text-accent-a",
      )}
    >
      <Icon className="h-[18px] w-[18px]" />
    </span>
  );
}

function SampleTag() {
  return (
    <span
      title="Synthetic demo accounts, not real bank balances"
      className="rounded-full border border-line px-2 py-0.5 text-[11px] font-medium text-muted"
    >
      Sample
    </span>
  );
}

/** One account: name + institution ••mask on the left, balance on the right. */
function AccountRow({ account, compact }: { account: BankAccount; compact?: boolean }) {
  const bal = account.current_balance;
  return (
    <li className={cn("flex items-center gap-3", compact ? "py-2" : "py-3")}>
      {!compact && <AccountIcon account={account} />}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text">{account.name}</p>
        <p className="truncate text-xs text-faint">
          {[account.institution, account.mask && `••${account.mask}`].filter(Boolean).join(" ")}
        </p>
      </div>
      <div className="text-right">
        <p className={cn("num text-sm font-semibold", account.is_liability ? "text-down" : "text-text")}>
          {bal == null ? "—" : fmtUSD(bal)}
        </p>
        {account.is_liability && <p className="text-[11px] text-faint">owed</p>}
      </div>
    </li>
  );
}

function NoAccounts({ compact }: { compact?: boolean }) {
  return (
    <p className={cn("text-sm text-muted", compact && "text-xs")}>
      No connected accounts yet.{" "}
      <Link to="/upload" className="font-medium text-accent-a hover:underline">Connect a bank</Link>{" "}
      to see balances here.
    </p>
  );
}

/** Overview: net worth + every account, with a manual refresh for Plaid users. */
export function AccountsPanel() {
  const qc = useQueryClient();
  const balances = useBalances();
  const plaid = useQuery({ queryKey: ["plaidStatus"], queryFn: api.plaidStatus });
  const refresh = useMutation({
    mutationFn: api.plaidSync,
    onSuccess: () => qc.invalidateQueries(),
  });

  const b = balances.data;
  const canRefresh = Boolean(b?.bank_connected && plaid.data?.configured);

  return (
    <Card className="mb-4 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display font-semibold text-muted">Accounts</h3>
            {b?.sample && <SampleTag />}
          </div>
          {b && b.count > 0 && (
            <>
              <p className={cn("num mt-1.5 text-3xl font-bold leading-tight", b.net_worth < 0 ? "text-down" : "text-text")}>
                {fmtUSD(b.net_worth)}
              </p>
              <p className="mt-0.5 text-xs text-faint">
                Net worth · {fmtUSD(b.assets)} held, {fmtUSD(b.liabilities)} owed
              </p>
            </>
          )}
        </div>
        {canRefresh && (
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent-a/40 hover:text-text disabled:opacity-50"
          >
            {refresh.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCw className="h-3.5 w-3.5" />}
            {b?.as_of ? `Updated ${fmtAgo(b.as_of)}` : "Refresh"}
          </button>
        )}
      </div>

      {balances.isLoading ? (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-9 w-40" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : !b || b.count === 0 ? (
        <div className="mt-2">
          {canRefresh
            ? <p className="text-sm text-muted">Bank connected. Hit refresh to load your balances.</p>
            : <NoAccounts />}
        </div>
      ) : (
        <ul className="mt-3 grid grid-cols-1 divide-y divide-line-soft md:grid-cols-2 md:gap-x-8 md:divide-y-0">
          {b.accounts.map((a) => <AccountRow key={a.id} account={a} />)}
        </ul>
      )}
      {refresh.isError && <p className="mt-2 text-xs text-down">{(refresh.error as Error).message}</p>}
    </Card>
  );
}

function summaryLine(b: AccountBalances) {
  return `${fmtUSD(b.net_worth)} across ${b.count} account${b.count === 1 ? "" : "s"}`;
}

/** Ask Jo, below xl: a one-line balance strip that expands to the account list. */
export function BalanceStrip({ className }: { className?: string }) {
  const { data: b } = useBalances();
  const [open, setOpen] = useState(false);
  if (!b) return null;

  if (b.count === 0) {
    return <div className={cn("rounded-xl border border-line bg-card px-3.5 py-2.5", className)}><NoAccounts compact /></div>;
  }

  return (
    <div className={cn("rounded-xl border border-line bg-card", className)}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-2.5 px-3.5 py-2.5 text-left"
      >
        <Wallet className="h-4 w-4 shrink-0 text-accent-a" />
        <span className="min-w-0 flex-1 truncate text-sm text-muted">
          <span className="num font-semibold text-text">{fmtUSD(b.net_worth)}</span>
          {" "}net worth
          <span className="hidden sm:inline"> · {b.count} account{b.count === 1 ? "" : "s"}</span>
        </span>
        {b.sample && <SampleTag />}
        <ChevronDown className={cn("h-4 w-4 shrink-0 text-faint transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <ul className="divide-y divide-line-soft border-t border-line-soft px-3.5">
          {b.accounts.map((a) => <AccountRow key={a.id} account={a} compact />)}
        </ul>
      )}
    </div>
  );
}

/** Ask Jo, xl and up: the same preview as an always-visible side panel. */
export function BalancePanel({ className }: { className?: string }) {
  const { data: b } = useBalances();
  if (!b) return null;
  return (
    <aside className={cn("w-64 shrink-0", className)}>
      <div className="sticky top-6 rounded-2xl border border-line bg-card p-4 shadow-card">
        <div className="flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-muted">
            <Wallet className="h-4 w-4 text-accent-a" /> Your accounts
          </h3>
          {b.sample && <SampleTag />}
        </div>
        {b.count === 0 ? (
          <div className="mt-2"><NoAccounts compact /></div>
        ) : (
          <>
            <p className="num mt-2 text-xl font-bold text-text" title={summaryLine(b)}>{fmtUSD(b.net_worth)}</p>
            <p className="text-xs text-faint">net worth</p>
            <ul className="mt-2 divide-y divide-line-soft">
              {b.accounts.map((a) => <AccountRow key={a.id} account={a} compact />)}
            </ul>
            {b.as_of && <p className="mt-2 text-[11px] text-faint">Updated {fmtAgo(b.as_of)}</p>}
          </>
        )}
      </div>
    </aside>
  );
}
