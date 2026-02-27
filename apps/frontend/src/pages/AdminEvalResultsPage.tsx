import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { PageCard, ProviderBadge } from "../components/Ui";
import { formatDateTime } from "../lib/formatters";

type RunRow = {
  id: string;
  status: string;
  provider: string;
  model_category: string;
  resolved_model_id?: string | null;
  created_at: string;
};

type RunItem = {
  id: string;
  status: string;
  question: string;
  answer_text?: string | null;
  metrics_json?: Record<string, unknown> | null;
  latency_ms?: number | null;
};

type CompareResponse = {
  deltas: Record<string, unknown>;
  run_a: RunRow;
  run_b: RunRow;
};

export function AdminEvalResultsPage() {
  const [runA, setRunA] = useState<string>("");
  const [runB, setRunB] = useState<string>("");
  const [selectedRunDetails, setSelectedRunDetails] = useState<string>("");

  const runsQuery = useQuery({
    queryKey: ["eval-runs"],
    queryFn: async () => apiClient.get<{ items: RunRow[] }>("/evals/runs"),
  });

  const compareQuery = useQuery({
    queryKey: ["eval-compare", runA, runB],
    queryFn: async () =>
      runA && runB ? apiClient.get<CompareResponse>(`/evals/compare?run_a=${runA}&run_b=${runB}`) : null,
    enabled: !!runA && !!runB,
  });

  const runItemsQuery = useQuery({
    queryKey: ["eval-run-items", selectedRunDetails],
    queryFn: async () =>
      selectedRunDetails
        ? apiClient.get<{ items: RunItem[] }>(`/evals/runs/${selectedRunDetails}/items`)
        : { items: [] as RunItem[] },
    enabled: !!selectedRunDetails,
  });

  const runs = runsQuery.data?.items ?? [];
  const selectedRun = useMemo(() => runs.find((r) => r.id === selectedRunDetails), [runs, selectedRunDetails]);

  return (
    <div className="grid gap-4">
      <PageCard title="Evaluation Results" subtitle="Compare runs and drill into per-case outcomes and metrics.">
        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="mb-3 grid gap-3 md:grid-cols-2">
              <label className="block">
                <div className="mb-1 text-xs text-ink/60">Run A</div>
                <select value={runA} onChange={(e) => setRunA(e.target.value)} className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
                  <option value="">Select run</option>
                  {runs.map((r) => (
                    <option key={`a-${r.id}`} value={r.id}>
                      {r.id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <div className="mb-1 text-xs text-ink/60">Run B</div>
                <select value={runB} onChange={(e) => setRunB(e.target.value)} className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
                  <option value="">Select run</option>
                  {runs.map((r) => (
                    <option key={`b-${r.id}`} value={r.id}>
                      {r.id}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="rounded-xl border border-ink/10 bg-white p-3">
              <div className="mb-2 text-sm font-semibold text-ink">Comparison Deltas</div>
              <pre className="max-h-[360px] overflow-auto rounded-lg bg-ink p-3 text-xs text-paper">
                {JSON.stringify(compareQuery.data?.deltas ?? { message: "Select two runs to compare" }, null, 2)}
              </pre>
            </div>
          </div>
          <div className="space-y-2">
            {runs.map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => setSelectedRunDetails(run.id)}
                className={`w-full rounded-xl border p-3 text-left ${selectedRunDetails === run.id ? "border-ink/20 bg-ink text-paper" : "border-ink/10 bg-white"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-semibold">{run.id}</div>
                  <ProviderBadge provider={run.provider} category={run.model_category} />
                </div>
                <div className={`mt-2 grid gap-1 text-xs ${selectedRunDetails === run.id ? "text-paper/80" : "text-ink/60"}`}>
                  <div>Status: {run.status}</div>
                  <div>Model: {run.resolved_model_id || "-"}</div>
                  <div>Created: {formatDateTime(run.created_at)}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </PageCard>

      <PageCard title="Per-Case Drill-down" subtitle={selectedRun ? `Run ${selectedRun.id}` : "Select a run to inspect items."}>
        <div className="space-y-3">
          {(runItemsQuery.data?.items ?? []).map((item) => (
            <div key={item.id} className="rounded-xl border border-ink/10 bg-white p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="text-sm font-semibold text-ink">{item.question}</div>
                <span className="rounded-full border border-ink/10 bg-paper px-2 py-1 text-xs">{item.status}</span>
              </div>
              <div className="mb-2 whitespace-pre-wrap text-sm text-ink">{item.answer_text || "(no answer)"}</div>
              <div className="grid gap-2 md:grid-cols-[140px_1fr]">
                <div className="text-xs text-ink/55">Latency</div>
                <div className="text-xs text-ink">{item.latency_ms ?? "-"} ms</div>
                <div className="text-xs text-ink/55">Metrics</div>
                <pre className="overflow-auto rounded-lg bg-paper p-2 text-xs text-ink">
                  {JSON.stringify(item.metrics_json ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          ))}
          {selectedRunDetails && (runItemsQuery.data?.items.length ?? 0) === 0 && (
            <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">
              No evaluation items recorded yet for this run.
            </div>
          )}
        </div>
      </PageCard>
    </div>
  );
}

