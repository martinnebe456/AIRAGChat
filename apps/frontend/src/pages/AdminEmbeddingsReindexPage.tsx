import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { ErrorState, LoadingState, PageCard } from "../components/Ui";
import { formatDateTime } from "../lib/formatters";
import { useUiStore } from "../store/uiStore";

type ReindexRun = {
  id: string;
  target_embedding_profile_id: string;
  source_embedding_profile_id?: string | null;
  status: string;
  qdrant_staging_collection: string;
  summary_json?: { total?: number; by_status?: Record<string, number>; needs_catchup?: number } | null;
  drift_detected_count?: number;
  started_at?: string | null;
  finished_at?: string | null;
  applied_at?: string | null;
  error_summary?: string | null;
  created_at: string;
};

type ReindexRunItem = {
  id: string;
  document_id: string;
  status: string;
  attempt_count: number;
  indexed_chunk_count: number;
  needs_catchup: boolean;
  error_summary?: string | null;
  updated_at: string;
};

type ReindexStatus = {
  active_alias_name: string;
  active_alias_target?: string | null;
  active_profile?: { id: string; provider: string; model_id: string; qdrant_collection_name: string } | null;
  latest_draft_profile?: { id: string; provider: string; model_id: string; dimensions: number } | null;
};

function runStatusClasses(status: string) {
  if (["applied", "apply_ready"].includes(status)) return "border-[#3674B5]/35 bg-[#578FCA]/12 text-[#3674B5]";
  if (["running", "catchup_running", "catchup_pending", "queued"].includes(status))
    return "border-[#FADA7A]/70 bg-[#FADA7A]/25 text-[#3674B5]";
  if (["failed"].includes(status)) return "border-[#FADA7A]/85 bg-[#F5F0CD]/95 text-[#3674B5]";
  return "border-[#578FCA]/25 bg-white/80 text-[#3674B5]/80";
}

export function AdminEmbeddingsReindexPage() {
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const statusQuery = useQuery({
    queryKey: ["embeddings-status"],
    queryFn: async () => apiClient.get<ReindexStatus>("/admin/embeddings/status"),
    refetchInterval: 8000,
  });

  const runsQuery = useQuery({
    queryKey: ["embeddings-reindex-runs"],
    queryFn: async () => apiClient.get<{ items: ReindexRun[]; total: number }>("/admin/embeddings/reindex-runs"),
    refetchInterval: (query) => {
      const active = (query.state.data?.items ?? []).some((r) =>
        ["queued", "running", "catchup_running", "catchup_pending"].includes(r.status),
      );
      return active ? 3000 : 8000;
    },
  });

  const selectedRun = useMemo(
    () => (runsQuery.data?.items ?? []).find((r) => r.id === selectedRunId) ?? (runsQuery.data?.items?.[0] ?? null),
    [runsQuery.data, selectedRunId],
  );

  const itemsQuery = useQuery({
    queryKey: ["embeddings-reindex-run-items", selectedRun?.id],
    queryFn: async () =>
      selectedRun
        ? apiClient.get<{ items: ReindexRunItem[]; total: number }>(`/admin/embeddings/reindex-runs/${selectedRun.id}/items`)
        : { items: [] as ReindexRunItem[], total: 0 },
    enabled: !!selectedRun,
    refetchInterval: selectedRun && ["queued", "running", "catchup_running", "catchup_pending"].includes(selectedRun.status) ? 3000 : false,
  });

  const previewQuery = useQuery({
    queryKey: ["embeddings-reindex-preview", selectedRun?.id],
    queryFn: async () =>
      selectedRun
        ? apiClient.post<{ stale_item_count: number; stale_item_ids: string[]; apply_blocked: boolean }>(
            `/admin/embeddings/reindex-runs/${selectedRun.id}/catch-up-preview`,
          )
        : { stale_item_count: 0, stale_item_ids: [], apply_blocked: true },
    enabled: !!selectedRun,
    refetchInterval: selectedRun ? 8000 : false,
  });

  const applyMutation = useMutation({
    mutationFn: async (runId: string) => apiClient.post(`/admin/embeddings/reindex-runs/${runId}/apply`),
    onSuccess: async () => {
      addToast({ title: "Embedding reindex applied", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["embeddings-status"] });
      await qc.invalidateQueries({ queryKey: ["embeddings-reindex-runs"] });
      if (selectedRun?.id) {
        await qc.invalidateQueries({ queryKey: ["embeddings-reindex-run-items", selectedRun.id] });
        await qc.invalidateQueries({ queryKey: ["embeddings-reindex-preview", selectedRun.id] });
      }
    },
    onError: (e) => addToast({ title: "Apply failed", message: (e as Error).message, kind: "error" }),
  });

  const cancelMutation = useMutation({
    mutationFn: async (runId: string) => apiClient.post(`/admin/embeddings/reindex-runs/${runId}/cancel`),
    onSuccess: async () => {
      addToast({ title: "Reindex run cancelled", kind: "warning" });
      await qc.invalidateQueries({ queryKey: ["embeddings-reindex-runs"] });
      if (selectedRun?.id) {
        await qc.invalidateQueries({ queryKey: ["embeddings-reindex-run-items", selectedRun.id] });
      }
    },
    onError: (e) => addToast({ title: "Cancel failed", message: (e as Error).message, kind: "error" }),
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
      <PageCard title="Embedding Reindex Runs" subtitle="Monitor global embedding reindex runs and switch active vector index safely.">
        {runsQuery.isLoading ? (
          <LoadingState message="Loading reindex runs..." />
        ) : runsQuery.isError ? (
          <ErrorState message={(runsQuery.error as Error).message} />
        ) : (
          <div className="space-y-3">
            <div className="rounded-xl border border-ink/10 bg-white p-3 text-sm">
              <div className="mb-2 font-semibold text-ink">Active Embedding Index</div>
              <div className="text-ink/70">Alias: {statusQuery.data?.active_alias_name ?? "documents_chunks_active"}</div>
              <div className="text-ink/70">Target: {statusQuery.data?.active_alias_target ?? "-"}</div>
              <div className="text-ink/70">
                Profile: {statusQuery.data?.active_profile?.provider ?? "-"} / {statusQuery.data?.active_profile?.model_id ?? "-"}
              </div>
            </div>

            {(runsQuery.data?.items ?? []).map((run) => {
              const summary = run.summary_json || {};
              const total = summary.total ?? 0;
              const succeeded = summary.by_status?.succeeded ?? 0;
              const failed = summary.by_status?.failed ?? 0;
              const selected = selectedRun?.id === run.id;
              return (
                <button
                  key={run.id}
                  type="button"
                  onClick={() => setSelectedRunId(run.id)}
                  className={`block w-full rounded-xl border p-3 text-left transition ${
                    selected ? "border-ink/30 bg-white shadow-panel" : "border-ink/10 bg-white/80 hover:border-ink/20"
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-ink">{run.id.slice(0, 8)}</div>
                    <span className={`rounded-full border px-2 py-1 text-xs ${runStatusClasses(run.status)}`}>{run.status}</span>
                  </div>
                  <div className="text-xs text-ink/70">Target profile: {run.target_embedding_profile_id.slice(0, 8)}</div>
                  <div className="mt-1 text-xs text-ink/70">
                    Progress: {succeeded}/{total} succeeded, {failed} failed
                  </div>
                  <div className="mt-1 text-xs text-ink/50">Created: {formatDateTime(run.created_at)}</div>
                </button>
              );
            })}

            {(runsQuery.data?.items.length ?? 0) === 0 && (
              <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">
                No embedding reindex runs yet. Start one from Admin Settings after saving a draft embedding profile.
              </div>
            )}
          </div>
        )}
      </PageCard>

      <PageCard
        title="Run Detail"
        subtitle={selectedRun ? `Run ${selectedRun.id}` : "Select a run to inspect per-document status and apply"}
        actions={
          selectedRun ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => previewQuery.refetch()}
                className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
              >
                Refresh
              </button>
              <button
                type="button"
                onClick={() => cancelMutation.mutate(selectedRun.id)}
                disabled={!["queued", "running", "catchup_running", "catchup_pending"].includes(selectedRun.status)}
                className="rounded-lg border border-[#FADA7A]/80 bg-[#F5F0CD]/95 px-3 py-2 text-sm text-ink disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => applyMutation.mutate(selectedRun.id)}
                disabled={!["apply_ready", "completed", "failed"].includes(selectedRun.status) || applyMutation.isPending}
                className="rounded-lg bg-ink px-3 py-2 text-sm text-paper disabled:opacity-50"
              >
                {applyMutation.isPending ? "Applying..." : "Apply"}
              </button>
            </div>
          ) : undefined
        }
      >
        {!selectedRun ? (
          <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">
            Select a run from the list to inspect progress and run catch-up/apply.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-ink/10 bg-white p-3">
                <div className="text-xs uppercase tracking-[0.12em] text-ink/60">Staging Collection</div>
                <div className="mt-1 text-sm font-medium text-ink">{selectedRun.qdrant_staging_collection}</div>
              </div>
              <div className="rounded-xl border border-ink/10 bg-white p-3">
                <div className="text-xs uppercase tracking-[0.12em] text-ink/60">Catch-up Preview</div>
                <div className="mt-1 text-sm text-ink">
                  Stale items: {previewQuery.data?.stale_item_count ?? 0}
                </div>
              </div>
            </div>

            {selectedRun.error_summary && <ErrorState message={selectedRun.error_summary} />}

            {itemsQuery.isLoading ? (
              <LoadingState message="Loading run items..." />
            ) : itemsQuery.isError ? (
              <ErrorState message={(itemsQuery.error as Error).message} />
            ) : (
              <div className="max-h-[520px] overflow-auto rounded-xl border border-ink/10 bg-white">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-white">
                    <tr className="border-b border-ink/10 text-xs uppercase tracking-[0.12em] text-ink/60">
                      <th className="px-3 py-2">Document</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Chunks</th>
                      <th className="px-3 py-2">Catch-up</th>
                      <th className="px-3 py-2">Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(itemsQuery.data?.items ?? []).map((item) => (
                      <tr key={item.id} className="border-b border-ink/5 align-top">
                        <td className="px-3 py-2">
                          <div className="font-mono text-xs text-ink">{item.document_id.slice(0, 8)}</div>
                          {item.error_summary && <div className="mt-1 text-xs text-ink/80">{item.error_summary}</div>}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`rounded-full border px-2 py-1 text-xs ${runStatusClasses(item.status)}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-ink/70">{item.indexed_chunk_count}</td>
                        <td className="px-3 py-2 text-ink/70">{item.needs_catchup ? "yes" : "no"}</td>
                        <td className="px-3 py-2 text-ink/60">{formatDateTime(item.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </PageCard>
    </div>
  );
}
