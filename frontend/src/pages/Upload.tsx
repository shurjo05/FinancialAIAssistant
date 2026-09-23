import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePlaidLink } from "react-plaid-link";
import { UploadCloud, FileWarning, Landmark, Loader2, Trash2, AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import type { UploadResult } from "../types";
import { Button, Card, PageHeader } from "../components/ui";
import { cn } from "../lib/utils";

/** Confirmation modal so data is never cleared by accident. */
function ClearDataModal({ onCancel, onConfirm, busy }: { onCancel: () => void; onConfirm: () => void; busy: boolean }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" onClick={onCancel}>
      <Card className="w-full max-w-sm p-6" >
        <div onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-down/10 text-down">
              <AlertTriangle className="h-5 w-5" />
            </span>
            <h3 className="font-display text-lg font-semibold text-text">Clear all your data?</h3>
          </div>
          <p className="mt-3 text-sm text-muted">
            This permanently deletes all your transactions, uploads, subscriptions, anomalies,
            bank connections, and chat history. Your account stays. This can’t be undone.
          </p>
          <div className="mt-5 flex justify-end gap-2">
            <Button onClick={onCancel} disabled={busy}>Cancel</Button>
            <button
              onClick={onConfirm}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-xl bg-down px-4 py-2.5 text-sm font-medium text-white hover:brightness-110 disabled:opacity-50"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {busy ? "Clearing…" : "Yes, clear everything"}
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}

/** Plaid "connect a bank" — only rendered when the server reports Plaid configured. */
function PlaidConnect() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  // Fetch a Link token up front so the widget is ready when the user clicks.
  useEffect(() => {
    api.plaidLinkToken()
      .then((r) => setLinkToken(r.link_token))
      .catch(() => setStatus("Couldn't start the bank connection."));
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
      else setStatus("Connected — no new transactions to import yet.");
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
    <Card className="mt-4 p-5">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent-a/10 text-accent-a">
          <Landmark className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <h3 className="font-display font-semibold text-text">Connect a bank</h3>
          <p className="text-sm text-faint">
            Plaid <b>sandbox</b> — no real bank. Log in with <code className="text-muted">user_good</code> / <code className="text-muted">pass_good</code>.
          </p>
        </div>
      </div>
      <button
        onClick={() => open()}
        disabled={!ready || !linkToken || busy}
        className="grad mt-4 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium text-white shadow-pop hover:brightness-110 disabled:opacity-50"
      >
        {busy && <Loader2 className="h-4 w-4 animate-spin" />}
        {busy ? "Working…" : "Connect a bank (sandbox)"}
      </button>
      {status && <p className="mt-3 text-sm text-muted">{status}</p>}
    </Card>
  );
}

export default function UploadPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

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
    <div>
      <PageHeader
        title="Add transactions"
        subtitle="Drop a bank or credit-card CSV — Chase, Bank of America, Capital One, or a generic export."
      />

      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed py-16 transition-colors",
          isDragActive ? "border-accent-a bg-accent-a/10" : "border-line bg-card hover:border-accent-a/50",
        )}
      >
        <input {...getInputProps()} />
        <UploadCloud className="h-10 w-10 text-faint" />
        <p className="mt-3 font-medium text-text">
          {busy ? "Processing…" : "Drag a CSV here, or click to browse"}
        </p>
        <p className="mt-1 text-sm text-faint">Your data stays private to your account.</p>
      </div>

      {error && (
        <Card className="mt-4 border-down/30 bg-down/10 p-4">
          <p className="flex items-center gap-2 text-sm font-medium text-down">
            <FileWarning className="h-4 w-4" /> {(error as Error).message}
          </p>
        </Card>
      )}

      {result && (
        <Card className="mt-4 p-4">
          <p className="text-sm text-text">
            Imported <b className="num">{result.row_count}</b> transactions from <b>{result.filename}</b>
            {result.error_count > 0 && (
              <> · <span className="text-amber-500">{result.error_count} row(s) skipped</span></>
            )}.
          </p>
        </Card>
      )}

      {plaidStatus.data?.configured && <PlaidConnect />}

      {cleared !== null && (
        <Card className="mt-4 p-4">
          <p className="text-sm text-text">Cleared <b className="num">{cleared}</b> transactions. Your account is empty.</p>
        </Card>
      )}

      <div className="mt-8 border-t border-line pt-5">
        <button
          onClick={() => setShowClear(true)}
          className="inline-flex items-center gap-2 text-sm font-medium text-faint transition-colors hover:text-down"
        >
          <Trash2 className="h-4 w-4" /> Clear all my data
        </button>
      </div>

      {showClear && (
        <ClearDataModal
          busy={clear.isPending}
          onCancel={() => setShowClear(false)}
          onConfirm={() => clear.mutate()}
        />
      )}
    </div>
  );
}
