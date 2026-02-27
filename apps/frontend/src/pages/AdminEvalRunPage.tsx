import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { PageCard, ProviderBadge } from "../components/Ui";
import { formatDateTime } from "../lib/formatters";
import { useUiStore } from "../store/uiStore";

type DatasetRow = { id: string; name: string; item_count: number };
type ProjectRow = { id: string; name: string };
type RunRow = {
  id: string;
  status: string;
  provider: string;
  model_category: string;
  resolved_model_id?: string | null;
  created_at: string;
};

export function AdminEvalRunPage() {
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const [datasetId, setDatasetId] = useState<string>("sample-default");
  const [modelCategory, setModelCategory] = useState<"low" | "medium" | "high">("low");
  const [projectId, setProjectId] = useState<string>("");

  const datasetsQuery = useQuery({
    queryKey: ["eval-datasets"],
    queryFn: async () => apiClient.get<{ items: DatasetRow[] }>("/evals/datasets"),
  });
  const runsQuery = useQuery({
    queryKey: ["eval-runs"],
    queryFn: async () => apiClient.get<{ items: RunRow[] }>("/evals/runs"),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects-for-evals"],
    queryFn: async () => apiClient.get<{ items: ProjectRow[] }>("/projects"),
  });

  const runMutation = useMutation({
    mutationFn: async () =>
      apiClient.post<RunRow>("/evals/runs", {
        dataset_id: datasetId,
        provider: "openai_api",
        model_category: modelCategory,
        rag_overrides: projectId ? { project_id: projectId } : {},
      }),
    onSuccess: async (run) => {
      addToast({ title: "Evaluation queued", message: run.id, kind: "success" });
      await qc.invalidateQueries({ queryKey: ["eval-runs"] });
    },
    onError: (e) => addToast({ title: "Eval run failed", message: (e as Error).message, kind: "error" }),
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <PageCard title="Run Evaluation" subtitle="OpenAI-only eval runs with optional project scope.">
        <div className="grid gap-3">
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Dataset</div>
            <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
              <option value="sample-default">sample-default (seed alias)</option>
              {(datasetsQuery.data?.items ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.item_count})
                </option>
              ))}
            </select>
          </label>
          <div className="rounded-lg border border-sky/20 bg-sky/5 px-3 py-2 text-sm text-sky">
            Provider is fixed to <span className="font-semibold">openai_api</span>.
          </div>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Project scope (optional; defaults to first active project)</div>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
              <option value="">Auto-select first project</option>
              {(projectsQuery.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Model category</div>
            <select value={modelCategory} onChange={(e) => setModelCategory(e.target.value as "low" | "medium" | "high")} className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
            </select>
          </label>
          <button type="button" onClick={() => runMutation.mutate()} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper">
            Start Evaluation Run
          </button>
        </div>
      </PageCard>

      <PageCard title="Recent Runs" subtitle="Quick visibility into run queue and completion state.">
        <div className="space-y-2">
          {(runsQuery.data?.items ?? []).map((run) => (
            <div key={run.id} className="rounded-xl border border-ink/10 bg-white p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-semibold text-ink">{run.id}</div>
                <ProviderBadge provider={run.provider} category={run.model_category} />
              </div>
              <div className="mt-2 grid gap-1 text-xs text-ink/60">
                <div>Status: {run.status}</div>
                <div>Model: {run.resolved_model_id || "-"}</div>
                <div>Created: {formatDateTime(run.created_at)}</div>
              </div>
            </div>
          ))}
        </div>
      </PageCard>
    </div>
  );
}
