import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileWarning } from "lucide-react";
import { api } from "../services/api";
import type { UploadResult } from "../types";
import { Card, PageHeader } from "../components/ui";
import { cn } from "../lib/utils";

export default function UploadPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const upload = useMutation({
    mutationFn: api.uploadCsv,
    onSuccess: (result: UploadResult) => {
      qc.invalidateQueries();
      if (result.row_count > 0) navigate("/overview");
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
        title="Upload transactions"
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
    </div>
  );
}
