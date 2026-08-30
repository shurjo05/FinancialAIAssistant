import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, Sparkles, FileWarning } from "lucide-react";
import { api } from "../services/api";
import type { UploadResult } from "../types";
import { Card, PageHeader } from "../components/ui";
import { cn } from "../lib/utils";

export default function UploadPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const onDone = (result: UploadResult) => {
    qc.invalidateQueries();
    if (result.row_count > 0) navigate("/");
  };

  const upload = useMutation({ mutationFn: api.uploadCsv, onSuccess: onDone });
  const sample = useMutation({ mutationFn: api.loadSample, onSuccess: onDone });

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) upload.mutate(files[0]);
  }, [upload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { "text/csv": [".csv"] }, multiple: false,
  });

  const busy = upload.isPending || sample.isPending;
  const error = upload.error || sample.error;
  const result = upload.data || sample.data;

  return (
    <div>
      <PageHeader
        title="Upload transactions"
        subtitle="Drop a bank or credit-card CSV — Chase, Bank of America, Capital One, or a generic export."
      />

      <div {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed bg-white py-16 transition-colors",
          isDragActive ? "border-brand-500 bg-brand-50" : "border-slate-300 hover:border-brand-400",
        )}
      >
        <input {...getInputProps()} />
        <UploadCloud className="h-10 w-10 text-slate-400" />
        <p className="mt-3 font-medium text-slate-700">
          {busy ? "Processing…" : "Drag a CSV here, or click to browse"}
        </p>
        <p className="mt-1 text-sm text-slate-400">Your data stays local.</p>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={() => sample.mutate()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          <Sparkles className="h-4 w-4" />
          Load sample data
        </button>
        <span className="text-sm text-slate-400">No CSV handy? Try 6 months of realistic data.</span>
      </div>

      {error && (
        <Card className="mt-4 border-red-200 bg-red-50">
          <p className="flex items-center gap-2 text-sm font-medium text-red-700">
            <FileWarning className="h-4 w-4" /> {(error as Error).message}
          </p>
        </Card>
      )}

      {result && (
        <Card className="mt-4">
          <p className="text-sm text-slate-700">
            Imported <b>{result.row_count}</b> transactions from{" "}
            <b>{result.filename}</b>
            {result.error_count > 0 && (
              <> · <span className="text-amber-600">{result.error_count} row(s) skipped</span></>
            )}.
          </p>
        </Card>
      )}
    </div>
  );
}
