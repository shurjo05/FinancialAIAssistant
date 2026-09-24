import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePlaidLink } from "react-plaid-link";
import { Check, Copy, FileWarning, Landmark, Loader2, Trash2, UploadCloud } from "lucide-react";
import { api, isDemo } from "../services/api";
import type { UploadResult } from "../types";
import { Card, ConfirmDialog, PageHeader } from "../components/ui";
import { cn } from "../lib/utils";

/** Sandbox credential with one-tap copy (typing "user_good" on a phone is a chore). */
function CopyValue({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch { /* clipboard blocked; the value is visible anyway */ }
  };
  return (
    <button
      onClick={copy}
      aria-label={`Copy ${value}`}
      className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-line bg-bg px-3 font-mono text-sm text-text transition-colors hover:border-accent-a/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
    >
      {value}
      {copied ? <Check className="h-4 w-4 text-up" /> : <Copy className="h-4 w-4 text-muted" />}
    </button>
  );
}

/** Plaid "connect a bank": only rendered when the server reports Plaid configured. */
function PlaidConnect() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  // Fetch a Link token up front so the widget is ready when the user taps.
  useEffect(() => {
    api.plaidLinkToken()
      .then((r) => setLinkToken(r.link_token))
      .catch(() => setStatus("Couldn't start the bank connection. Reload the page to try again."));
  }, []);

  const handleSuccess = useCallback(async (publicToken: string) => {
    setBusy(true);
    setStatus("Connecting…");
    try {
      const item = await api.plaidExchange(publicToken);
      setStatus(`Syncing ${item.institution_name ?? "your bank"}…`);
      const res = await api.plaidSync();
      qc.invalidateQueries();
      if (res.added > 0) navigate("/overview");
      else setStatus("Connected. There are no new transactions to import yet.");
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [qc, navigate]);

  // Empty token until fetched → the hook stays not-ready (button disabled).
  const { open, ready } = usePlaidLink({
    token: linkToken ?? "",
    onSuccess: (publicToken) => { if (publicToken) void handleSuccess(publicToken); },
  });

  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent-a/10 text-accent-a">
          <Landmark className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <h2 className="font-display font-semibold text-text">Connect a bank</h2>
          <p className="mt-0.5 text-sm text-muted">
            Uses Plaid’s <strong className="font-semibold text-text">sandbox</strong>: test banks only, never a real account.
            Pick any bank, then sign in with:
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 sm:pl-[52px]">
        <CopyValue value="user_good" />
        <CopyValue value="pass_good" />
      </div>
      <button
        onClick={() => open()}
        disabled={!ready || !linkToken || busy}
        className="grad mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-medium text-white shadow-pop hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:opacity-50 sm:ml-[52px]"
      >
        {busy && <Loader2 className="h-4 w-4 animate-spin" />}
        {busy ? "Working…" : "Connect a sandbox bank"}
      </button>
      {status && <p role="status" className="mt-3 text-sm text-muted sm:pl-[52px]">{status}</p>}
    </Card>
  );
}

export default function UploadPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const demo = isDemo();

  const plaidStatus = useQuery({ queryKey: ["plaidStatus"], queryFn: api.plaidStatus });
  const [showClear, setShowClear] = useState(false);
  const [cleared, setCleared] = useState<number | null>(null);

  const upload = useMutation({
    mutationFn: api.uploadCsv,
    onSuccess: (result: UploadResult) => {
      qc.invalidateQueries();
      if (result.row_count > 0) navigate("/overview");
    },
  });

  const clear = useMutation({
    mutationFn: api.clearData,
    onSuccess: (res) => {
      qc.invalidateQueries();
      setShowClear(false);
      setCleared(res.transactions_deleted);
    },
  });

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) upload.mutate(files[0]);
  }, [upload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { "text/csv": [".csv"] }, multiple: false,
  });

  const busy = upload.isPending;
  const error = upload.error;
  const result = upload.data;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Add transactions"
        subtitle="Upload a CSV from Chase, Bank of America, Capital One, or any bank’s export."
      />

      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 py-12 text-center transition-colors sm:py-16",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60",
          isDragActive ? "border-accent-a bg-accent-a/10" : "border-line bg-card hover:border-accent-a/50",
        )}
      >
        <input {...getInputProps()} aria-label="Choose a CSV file" />
        {busy ? <Loader2 className="h-10 w-10 animate-spin text-accent-a" /> : <UploadCloud className="h-10 w-10 text-muted" />}
        <p className="mt-3 font-medium text-text">
          {busy ? "Reading and categorizing…" : isDragActive ? "Drop it here" : "Choose a CSV file"}
        </p>
        <p className="mt-1 text-sm text-muted">
          <span className="hidden md:inline">or drag one here. </span>Your data stays private to your account.
        </p>
      </div>

      {error && (
        <Card className="mt-4 border-down/30 bg-down/10 p-4">
          <p role="alert" className="flex items-start gap-2 text-sm font-medium text-down">
            <FileWarning className="mt-0.5 h-4 w-4 shrink-0" /> {(error as Error).message}
          </p>
        </Card>
      )}

      {result && (
        <Card className="mt-4 p-4">
          <p role="status" className="text-sm text-text">
            Imported <b className="num">{result.row_count}</b> transactions from <b>{result.filename}</b>
            {result.error_count > 0 && (
              <>. <span className="text-warn">{result.error_count} row(s) couldn’t be read and were skipped</span></>
            )}.
          </p>
        </Card>
      )}

      {plaidStatus.data?.configured && <div className="mt-4"><PlaidConnect /></div>}

      {cleared !== null && (
        <Card className="mt-4 p-4">
          <p role="status" className="text-sm text-text">Cleared <b className="num">{cleared}</b> transactions. Your account is empty.</p>
        </Card>
      )}

      {/* The shared demo can't be cleared (the server refuses too) */}
      {!demo && (
        <div className="mt-10 border-t border-line pt-5">
          <button
            onClick={() => setShowClear(true)}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg text-sm font-medium text-muted transition-colors hover:text-down focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
          >
            <Trash2 className="h-4 w-4" /> Clear all my data
          </button>
        </div>
      )}

      {showClear && (
        <ConfirmDialog
          title="Clear all your data?"
          message="This permanently deletes your transactions, uploads, subscriptions, anomalies, bank connections, and chat history. Your account stays. This can’t be undone."
          confirmLabel={clear.isPending ? "Clearing…" : "Yes, clear everything"}
          destructive
          busy={clear.isPending}
          onCancel={() => setShowClear(false)}
          onConfirm={() => clear.mutate()}
        />
      )}
    </div>
  );
}
