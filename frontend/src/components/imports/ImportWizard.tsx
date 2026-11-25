"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FormField } from "@/components/ui/FormField";
import { Select } from "@/components/ui/Select";
import { getImportJob, previewImport, startImportJob } from "@/lib/api/dataImport";
import { ColumnMapping, ImportDataType, ImportSummaryResponse, PreviewResponse } from "@/types/dataImport";
import { useT } from "@/lib/i18n/LanguageProvider";

type Step = "pick" | "mapping" | "running" | "result";

const POLL_INTERVAL_MS = 1000;
// Poll hiccups (a dropped request, a brief cold start) shouldn't abandon an
// import that is still running fine on the server.
const MAX_CONSECUTIVE_POLL_FAILURES = 5;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function bestEffortMapping(canonicalFields: string[], headers: string[]): ColumnMapping {
  const mapping: ColumnMapping = {};
  for (const field of canonicalFields) {
    const normalizedField = field.replace(/_/g, "").toLowerCase();
    const match = headers.find((h) => h.replace(/[\s_]/g, "").toLowerCase() === normalizedField);
    if (match) mapping[field] = match;
  }
  return mapping;
}

export function ImportWizard({
  token,
  businessId,
  dataType,
}: {
  token: string | null;
  businessId: string;
  dataType: ImportDataType;
}) {
  const { t } = useT();
  const [step, setStep] = useState<Step>("pick");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>({});
  const [summary, setSummary] = useState<ImportSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ processed: number; total: number }>({ processed: 0, total: 0 });
  // Set when the wizard is left/reset so a running poll loop stops.
  const cancelled = useRef(false);

  useEffect(
    () => () => {
      cancelled.current = true;
    },
    []
  );

  function reset() {
    cancelled.current = true;
    setProgress({ processed: 0, total: 0 });
    setStep("pick");
    setFile(null);
    setPreview(null);
    setMapping({});
    setSummary(null);
    setError(null);
  }

  async function handlePreview() {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await previewImport(token, businessId, dataType, file);
      setPreview(result);
      setMapping(bestEffortMapping(result.canonical_fields, result.headers));
      setStep("mapping");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_preview_file"));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleImport() {
    if (!file) return;
    cancelled.current = false;
    setIsLoading(true);
    setError(null);
    try {
      const started = await startImportJob(token, businessId, dataType, file, mapping);
      setProgress({ processed: started.processed_rows, total: started.total_rows });
      setStep("running");

      let failures = 0;
      for (;;) {
        await sleep(POLL_INTERVAL_MS);
        if (cancelled.current) return;
        try {
          const job = await getImportJob(token, businessId, started.job_id);
          failures = 0;
          setProgress({ processed: job.processed_rows, total: job.total_rows });
          if (job.status === "done" && job.summary) {
            setSummary(job.summary);
            setStep("result");
            return;
          }
          if (job.status === "failed") {
            setError(job.error ?? t("import.stopped"));
            setStep("mapping");
            return;
          }
        } catch (err) {
          // 404 = the server forgot the job (restart); retrying can't help.
          if (err instanceof ApiError && err.status === 404) throw err;
          failures += 1;
          if (failures >= MAX_CONSECUTIVE_POLL_FAILURES) {
            throw new Error(
              t("import.lostContact")
            );
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("s.failed_to_import_file"));
      setStep("mapping");
    } finally {
      setIsLoading(false);
    }
  }

  if (step === "pick") {
    return (
      <div className="space-y-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <FormField label={t("s.csv_file")}>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-brand-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-700"
          />
        </FormField>
        <Button onClick={handlePreview} disabled={!file || isLoading}>
          {isLoading ? t("s.reading_file") : t("s.preview")}
        </Button>
      </div>
    );
  }

  if (step === "mapping" && preview) {
    return (
      <div className="space-y-6">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <p className="text-sm text-slate-600">
          {t("import.found", { n: preview.row_count })}
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {preview.canonical_fields.map((field) => {
            const isRequired = preview.required_fields.includes(field);
            return (
              <FormField key={field} label={isRequired ? `${field} *` : field}>
                <Select
                  value={mapping[field] ?? ""}
                  onChange={(e) =>
                    setMapping((prev) => ({ ...prev, [field]: e.target.value }))
                  }
                >
                  <option value="">{t("s.not_mapped")}</option>
                  {preview.headers.map((header) => (
                    <option key={header} value={header}>
                      {header}
                    </option>
                  ))}
                </Select>
              </FormField>
            );
          })}
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">{t("s.sample_rows")}</p>
          <div className="overflow-x-auto rounded-md border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  {preview.headers.map((header) => (
                    <th key={header} className="whitespace-nowrap px-3 py-2 font-medium text-slate-600">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-100 last:border-0">
                    {preview.headers.map((header) => (
                      <td key={header} className="whitespace-nowrap px-3 py-2 text-slate-600">
                        {row[header] ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex gap-3">
          <Button variant="secondary" onClick={reset} disabled={isLoading}>
            {t("s.start_over")}
          </Button>
          <Button onClick={handleImport} disabled={isLoading}>
            {isLoading ? t("s.importing") : t("s.import")}
          </Button>
        </div>
      </div>
    );
  }

  if (step === "running") {
    const percent =
      progress.total > 0 ? Math.min(100, Math.round((progress.processed / progress.total) * 100)) : 0;
    return (
      <div className="space-y-3" aria-live="polite">
        <p className="text-sm text-slate-700">
          {t("import.running", {
            done: progress.processed.toLocaleString(),
            total: progress.total.toLocaleString(),
          })}
        </p>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={t("s.import_progress")}
          className="h-2 w-full overflow-hidden rounded-full bg-slate-200"
        >
          <div className="h-full bg-brand-600 transition-all" style={{ width: `${percent}%` }} />
        </div>
        <p className="text-xs text-slate-500">
          {t("s.large_files_can_take_a_minute_or_t")}
        </p>
      </div>
    );
  }

  if (step === "result" && summary) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <Badge tone="success">{t("import.created", { n: summary.created })}</Badge>
          <Badge tone="neutral">{t("import.skipped", { n: summary.skipped_duplicates })}</Badge>
          <Badge tone={summary.errors.length > 0 ? "danger" : "neutral"}>{t("import.errors", { n: summary.errors.length })}</Badge>
          <Badge tone="neutral">{t("import.totalRows", { n: summary.total_rows })}</Badge>
        </div>

        {summary.errors.length > 0 && (
          <div className="overflow-x-auto rounded-md border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">{t("s.row")}</th>
                  <th className="px-3 py-2">{t("s.error")}</th>
                </tr>
              </thead>
              <tbody>
                {summary.errors.map((e) => (
                  <tr key={e.row_number} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2 text-slate-600">{e.row_number}</td>
                    <td className="px-3 py-2 text-slate-600">{e.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <Button variant="secondary" onClick={reset}>
          {t("s.import_another_file")}
        </Button>
      </div>
    );
  }

  return null;
}
