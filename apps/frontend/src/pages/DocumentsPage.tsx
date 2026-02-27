import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { bytesToHuman } from "../api/dtos";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { FormDialog } from "../components/FormDialog";
import { ErrorState, PageCard } from "../components/Ui";
import { formatDateTime } from "../lib/formatters";
import { useAuthStore } from "../store/authStore";
import { useUiStore } from "../store/uiStore";

type ProjectRow = { id: string; name: string; my_role?: string | null };
type DocRow = {
  id: string;
  project_id?: string | null;
  project_name?: string | null;
  filename_original: string;
  file_size_bytes: number;
  status: string;
  status_message?: string | null;
  page_count?: number | null;
  processing_progress?: Record<string, unknown> | null;
  created_at: string;
};
type JobEvent = { id: string; stage: string; level: string; message: string; details_json?: Record<string, unknown> | null; created_at: string };
type UploadResp = { document: DocRow; job: { id: string; status: string; progress_json?: Record<string, unknown> | null } };
type ReprocessResp = { document_id: string; job_id: string; status: string; progress_json?: Record<string, unknown> | null; queue_message?: string | null; already_queued?: boolean };
type ProcJob = {
  id: string; document_id: string; project_id?: string | null; requested_by_user_id?: string | null;
  status: string; job_type: string; celery_task_id?: string | null;
  dispatched_at?: string | null; dispatched_by_user_id?: string | null; dispatch_trigger?: string | null; dispatch_batch_id?: string | null;
  started_at?: string | null; finished_at?: string | null; error_summary?: string | null; attempt_count: number;
  progress_json?: Record<string, unknown> | null; created_at: string; updated_at: string;
};
type QueueJobSummary = { job: ProcJob; filename_original?: string | null; latest_event_stage?: string | null; latest_event_level?: string | null; latest_event_message?: string | null };
type QueueState = { timezone: string; last_midnight_run_local_date?: string | null; last_midnight_dispatch_at?: string | null; last_midnight_dispatched_count?: number; missed_run_detected?: boolean; next_midnight_at_utc?: string | null };
type QueueOverview = { project_id: string; queued_count: number; dispatched_count: number; running_count: number; succeeded_recent_count: number; failed_recent_count: number; active_jobs: QueueJobSummary[]; recent_jobs: QueueJobSummary[]; scheduler_state: QueueState };
type QueueDispatchResp = { project_id: string; dispatched_count: number; skipped_count: number; already_running_count: number; queued_remaining_count: number; batch_dispatch_id: string; job_ids: string[] };

const ACTIVE_DOC_STATUSES = new Set(["uploaded", "parsing", "chunking", "embedding"]);
const ACTIVE_JOB_STATUSES = new Set(["queued", "dispatched", "running"]);

const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const num = (v: unknown) => { const n = Number(v); return Number.isFinite(n) ? n : null; };
const isDocActive = (s: string) => ACTIVE_DOC_STATUSES.has(s);

function statusBadgeClasses(status: string) {
  if (status === "indexed") return "border-[#3674B5]/35 bg-[#578FCA]/12 text-[#3674B5]";
  if (status === "failed") return "border-[#FADA7A]/85 bg-[#F5F0CD]/95 text-[#3674B5]";
  if (isDocActive(status)) return "border-[#FADA7A]/70 bg-[#FADA7A]/25 text-[#3674B5]";
  return "border-[#578FCA]/25 bg-white/80 text-[#3674B5]/80";
}

function jobBadgeClasses(status: string) {
  if (status === "queued") return "border-[#FADA7A]/70 bg-[#FADA7A]/25 text-[#3674B5]";
  if (status === "dispatched" || status === "running" || status === "succeeded") return "border-[#3674B5]/35 bg-[#578FCA]/12 text-[#3674B5]";
  if (status === "failed") return "border-[#FADA7A]/85 bg-[#F5F0CD]/95 text-[#3674B5]";
  return "border-[#578FCA]/25 bg-white/80 text-[#3674B5]/80";
}

function summarizeProgress(progress?: Record<string, unknown> | null, fallback?: string) {
  if (!isObj(progress)) return null;
  const stage = typeof progress.stage === "string" ? progress.stage : fallback;
  const pp = num(progress.pages_processed); const pt = num(progress.pages_total);
  const ct = num(progress.chunks_total); const ec = num(progress.embedded_chunks); const ic = num(progress.indexed_chunks);
  if (stage === "queued") return "Queued for daily/manual processing";
  if (pp !== null && pt !== null) return `${stage ?? "processing"} · pages ${pp}/${pt}`;
  if (ec !== null && ct !== null) return `${stage ?? "embedding"} · embedded ${ec}/${ct}`;
  if (ic !== null && ct !== null) return `${stage ?? "indexing"} · indexed ${ic}/${ct}`;
  if (ct !== null) return `${stage ?? "chunking"} · chunks ${ct}`;
  return stage ?? null;
}

function statusToastPayload(doc: DocRow) {
  const base = doc.filename_original;
  const msg = doc.status_message || undefined;
  switch ((doc.status || "").toLowerCase()) {
    case "uploaded": return { title: "Processing queued", message: msg ?? `${base} was queued for processing.`, kind: "info" as const, durationMs: 3500 };
    case "parsing": return { title: "Processing started", message: msg ?? `${base}: parsing document text.`, kind: "warning" as const, durationMs: 4000 };
    case "chunking": return { title: "Processing in progress", message: msg ?? `${base}: chunking extracted text.`, kind: "warning" as const, durationMs: 4000 };
    case "embedding": return { title: "Processing in progress", message: msg ?? `${base}: generating embeddings and indexing.`, kind: "warning" as const, durationMs: 4000 };
    case "indexed": return { title: "Processing completed", message: msg ?? `${base} is indexed and ready for chat.`, kind: "success" as const, durationMs: 5000 };
    case "failed": return { title: "Processing failed", message: msg ?? `${base} failed during processing. Check logs for details.`, kind: "error" as const, durationMs: 7000 };
    default: return { title: "Document status updated", message: msg ?? `${base}: ${doc.status}`, kind: "info" as const, durationMs: 3500 };
  }
}

export function DocumentsPage() {
  const me = useAuthStore((s) => s.me);
  const addToast = useUiStore((s) => s.addToast);
  const qc = useQueryClient();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<DocRow | null>(null);
  const initStatuses = useRef(false);
  const prevStatusMap = useRef<Map<string, { status: string; statusMessage?: string | null }>>(new Map());

  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: async () => apiClient.get<{ items: ProjectRow[] }>("/projects") });

  useEffect(() => {
    if (!selectedProjectId && projectsQuery.data?.items?.length) setSelectedProjectId(projectsQuery.data.items[0].id);
  }, [projectsQuery.data, selectedProjectId]);

  const selectedProject = useMemo(() => (projectsQuery.data?.items ?? []).find((p) => p.id === selectedProjectId) ?? null, [projectsQuery.data, selectedProjectId]);
  const canUpload = me?.role === "admin" || selectedProject?.my_role === "contributor" || selectedProject?.my_role === "manager";
  const isAdmin = me?.role === "admin";

  const docsQuery = useQuery({
    queryKey: ["documents", selectedProjectId],
    enabled: !!selectedProjectId,
    queryFn: async () => selectedProjectId ? apiClient.get<{ items: DocRow[] }>(`/documents?project_id=${encodeURIComponent(selectedProjectId)}`) : { items: [] as DocRow[] },
    refetchInterval: (q) => (q.state.data?.items ?? []).some((d) => isDocActive(d.status)) ? 3000 : 8000,
    refetchIntervalInBackground: true,
  });

  const selectedDoc = useMemo(() => (docsQuery.data?.items ?? []).find((d) => d.id === selectedDocId) ?? null, [docsQuery.data, selectedDocId]);

  const logsQuery = useQuery({
    queryKey: ["document-logs", selectedDocId],
    enabled: !!selectedDocId,
    queryFn: async () => selectedDocId ? apiClient.get<{ items: JobEvent[] }>(`/documents/${selectedDocId}/processing-logs`) : { items: [] as JobEvent[] },
    refetchInterval: selectedDoc && isDocActive(selectedDoc.status) ? 2000 : false,
    refetchIntervalInBackground: true,
  });

  const queueOverviewQuery = useQuery({
    queryKey: ["queue-overview", selectedProjectId],
    enabled: !!selectedProjectId,
    queryFn: async () => selectedProjectId ? apiClient.get<QueueOverview>(`/ingestion/queue/overview?project_id=${encodeURIComponent(selectedProjectId)}`) : null,
    refetchInterval: (q) => {
      const d = q.state.data as QueueOverview | null | undefined;
      if (!d) return false;
      return d.queued_count || d.dispatched_count || d.running_count ? 3000 : 8000;
    },
    refetchIntervalInBackground: true,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error("Select a file first");
      if (!selectedProjectId) throw new Error("Select a project first");
      const fd = new FormData(); fd.append("project_id", selectedProjectId); fd.append("file", uploadFile);
      return apiClient.postForm<UploadResp>("/documents/upload", fd);
    },
    onMutate: () => addToast({ title: "Upload started", message: uploadFile ? `Uploading ${uploadFile.name}...` : "Uploading document...", kind: "info", durationMs: 2500 }),
    onSuccess: async (resp) => {
      setUploadFile(null); setSelectedDocId(resp.document.id); setIsUploadDialogOpen(false);
      addToast({ title: "Upload completed", message: `${resp.document.filename_original} uploaded and queued.`, kind: "success" });
      addToast(statusToastPayload(resp.document));
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["documents"] }),
        qc.invalidateQueries({ queryKey: ["queue-overview"] }),
      ]);
    },
    onError: (e) => addToast({ title: "Upload failed", message: (e as Error).message, kind: "error" }),
  });

  const reprocessMutation = useMutation({
    mutationFn: async (doc: DocRow) => ({ doc, resp: await apiClient.post<ReprocessResp>(`/documents/${doc.id}/reprocess`) }),
    onSuccess: async ({ doc, resp }) => {
      setSelectedDocId(doc.id);
      addToast({
        title: resp.already_queued ? "Already queued" : "Reprocess queued",
        message: resp.queue_message ?? `${doc.filename_original} was queued for daily/manual processing.`,
        kind: resp.already_queued ? "warning" : "success",
        durationMs: 4500,
      });
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["documents"] }),
        qc.invalidateQueries({ queryKey: ["queue-overview"] }),
        qc.invalidateQueries({ queryKey: ["document-logs", doc.id] }),
      ]);
    },
    onError: (e) => addToast({ title: "Reprocess failed", message: (e as Error).message, kind: "error" }),
  });

  const dispatchMutation = useMutation({
    mutationFn: async () => {
      if (!selectedProjectId) throw new Error("Select a project first");
      return apiClient.post<QueueDispatchResp>("/ingestion/queue/dispatch", { project_id: selectedProjectId, queued_only: true });
    },
    onSuccess: async (resp) => {
      addToast({ title: "Queued processing started", message: `Dispatched ${resp.dispatched_count} job(s) for selected project.`, kind: resp.dispatched_count > 0 ? "success" : "warning", durationMs: 5000 });
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["documents"] }),
        qc.invalidateQueries({ queryKey: ["queue-overview"] }),
      ]);
    },
    onError: (e) => addToast({ title: "Queue dispatch failed", message: (e as Error).message, kind: "error" }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (docId: string) => apiClient.delete(`/documents/${docId}`),
    onSuccess: async () => {
      setDocToDelete(null);
      addToast({ title: "Document deleted", kind: "success" });
      setSelectedDocId(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["documents"] }),
        qc.invalidateQueries({ queryKey: ["queue-overview"] }),
      ]);
    },
    onError: (e) => addToast({ title: "Delete failed", message: (e as Error).message, kind: "error" }),
  });

  useEffect(() => {
    const items = docsQuery.data?.items;
    if (!items) return;
    const next = new Map<string, { status: string; statusMessage?: string | null }>();
    for (const d of items) next.set(d.id, { status: d.status, statusMessage: d.status_message });
    if (!initStatuses.current) { prevStatusMap.current = next; initStatuses.current = true; return; }
    for (const d of items) {
      const prev = prevStatusMap.current.get(d.id);
      if (!prev || prev.status === d.status) continue;
      if (d.id !== selectedDocId && d.status !== "failed") continue;
      addToast(statusToastPayload(d));
    }
    prevStatusMap.current = next;
  }, [docsQuery.data?.items, addToast, selectedDocId]);

  const queueOverview = queueOverviewQuery.data ?? null;
  const activeJobs = queueOverview?.active_jobs ?? [];
  const recentJobs = queueOverview?.recent_jobs ?? [];

  return (
    <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
      <PageCard
        title="Document Library"
        subtitle="Project-scoped documents with queue-first processing and progress tracking."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select value={selectedProjectId ?? ""} onChange={(e) => { setSelectedProjectId(e.target.value || null); setSelectedDocId(null); }} className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
              <option value="">Select project</option>
              {(projectsQuery.data?.items ?? []).map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
            </select>
            {canUpload ? (
              <>
                <button
                  type="button"
                  onClick={() => setIsUploadDialogOpen(true)}
                  disabled={!selectedProjectId}
                  className="rounded-lg bg-ink px-3 py-2 text-sm text-paper disabled:opacity-60"
                >Upload</button>
              </>
            ) : (
              <span className="text-xs text-ink/50">{selectedProject ? "Read-only project access" : "Select a project"}</span>
            )}
          </div>
        }
      >
        {!selectedProjectId ? (
          <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">Select a project to view and manage documents.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-ink/10 text-xs uppercase tracking-[0.12em] text-ink/60"><th className="px-2 py-2">Project</th><th className="px-2 py-2">Filename</th><th className="px-2 py-2">Status</th><th className="px-2 py-2">Size</th><th className="px-2 py-2">Pages</th><th className="px-2 py-2">Created</th><th className="px-2 py-2">Actions</th></tr></thead>
              <tbody>
                {(docsQuery.data?.items ?? []).map((doc) => {
                  const progressLine = summarizeProgress(doc.processing_progress ?? null, doc.status);
                  return (
                    <tr key={doc.id} className="border-b border-ink/5">
                      <td className="px-2 py-2 text-ink/65">{doc.project_name ?? selectedProject?.name ?? "-"}</td>
                      <td className="px-2 py-2">
                        <button type="button" className="max-w-[280px] truncate text-left font-medium text-ink hover:underline" onClick={() => setSelectedDocId(doc.id)}>{doc.filename_original}</button>
                        {doc.status_message && <div className="text-xs text-ink/55">{doc.status_message}</div>}
                        {progressLine && <div className="text-xs text-ink/55">{progressLine}</div>}
                      </td>
                      <td className="px-2 py-2"><span className={`rounded-full border px-2 py-1 text-xs ${statusBadgeClasses(doc.status)}`}>{doc.status}</span></td>
                      <td className="px-2 py-2 text-ink/70">{bytesToHuman(doc.file_size_bytes)}</td>
                      <td className="px-2 py-2 text-ink/70">{doc.page_count ?? "-"}</td>
                      <td className="px-2 py-2 text-ink/70">{formatDateTime(doc.created_at)}</td>
                      <td className="px-2 py-2">
                        {canUpload ? (
                          <div className="flex gap-2">
                            <button type="button" onClick={() => reprocessMutation.mutate(doc)} disabled={reprocessMutation.isPending} className="rounded-md border border-ink/15 bg-white px-2 py-1 text-xs disabled:opacity-60">Reprocess</button>
                            <button type="button" onClick={() => setDocToDelete(doc)} className="rounded-md border border-[#FADA7A]/80 bg-[#F5F0CD]/95 px-2 py-1 text-xs text-ink">Delete</button>
                          </div>
                        ) : <span className="text-xs text-ink/40">Read-only</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!docsQuery.isLoading && (docsQuery.data?.items.length ?? 0) === 0 && <div className="mt-4 rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">{selectedProjectId ? "No documents available in this project yet." : "No project selected."}</div>}
      </PageCard>

      <div className="space-y-4">
        <PageCard
          title="Queue & Processing Monitor"
          subtitle={selectedProject ? `Queued/dispatched/running jobs and recent results for ${selectedProject.name}` : "Select a project to monitor processing queue"}
          actions={isAdmin && selectedProjectId ? (
            <button type="button" onClick={() => dispatchMutation.mutate()} disabled={dispatchMutation.isPending || !queueOverview || queueOverview.queued_count <= 0} className="rounded-lg border border-sky/30 bg-sky/10 px-3 py-2 text-sm text-sky disabled:opacity-60">{dispatchMutation.isPending ? "Starting..." : "Start queued now"}</button>
          ) : undefined}
        >
          {!selectedProjectId ? (
            <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">Select a project to see queued and running embedding jobs.</div>
          ) : queueOverviewQuery.isError ? (
            <ErrorState message={(queueOverviewQuery.error as Error).message} />
          ) : !queueOverview ? (
            <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">Loading queue overview...</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-lg border border-ink/10 bg-white p-3"><div className="text-xs uppercase tracking-[0.12em] text-ink/55">Queued</div><div className="mt-1 text-lg font-semibold text-ink">{queueOverview.queued_count}</div></div>
                <div className="rounded-lg border border-ink/10 bg-white p-3"><div className="text-xs uppercase tracking-[0.12em] text-ink/55">Dispatched</div><div className="mt-1 text-lg font-semibold text-ink">{queueOverview.dispatched_count}</div></div>
                <div className="rounded-lg border border-ink/10 bg-white p-3"><div className="text-xs uppercase tracking-[0.12em] text-ink/55">Running</div><div className="mt-1 text-lg font-semibold text-ink">{queueOverview.running_count}</div></div>
                <div className="rounded-lg border border-ink/10 bg-white p-3"><div className="text-xs uppercase tracking-[0.12em] text-ink/55">Failed (24h)</div><div className="mt-1 text-lg font-semibold text-ink">{queueOverview.failed_recent_count}</div></div>
              </div>

              <div className="rounded-lg border border-ink/10 bg-white p-3 text-xs text-ink/70">
                <div>Scheduler ({queueOverview.scheduler_state.timezone}) next run: <span className="font-medium text-ink">{queueOverview.scheduler_state.next_midnight_at_utc ? formatDateTime(queueOverview.scheduler_state.next_midnight_at_utc) : "-"}</span></div>
                <div>Last midnight run: <span className="font-medium text-ink">{queueOverview.scheduler_state.last_midnight_run_local_date ?? "not recorded"}</span></div>
                {queueOverview.scheduler_state.missed_run_detected && <div className="mt-1 text-ink">Missed midnight run detected; queued jobs will be started on next backend startup.</div>}
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-ink/60">Active Queue</div>
                {activeJobs.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-ink/15 p-4 text-sm text-ink/60">No queued/dispatched/running jobs in this project.</div>
                ) : (
                  <div className="max-h-[280px] space-y-2 overflow-auto pr-1">
                    {activeJobs.map((row) => (
                      <button key={row.job.id} type="button" onClick={() => setSelectedDocId(row.job.document_id)} className={`block w-full rounded-lg border p-3 text-left ${row.job.document_id === selectedDocId ? "border-[#3674B5]/35 bg-[#578FCA]/10" : "border-ink/10 bg-white hover:border-[#578FCA]/35"}`}>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="min-w-0"><div className="truncate text-sm font-medium text-ink">{row.filename_original ?? row.job.document_id}</div><div className="text-xs text-ink/55">{row.job.job_type} · queued {formatDateTime(row.job.created_at)}</div></div>
                          <span className={`rounded-full border px-2 py-1 text-xs ${jobBadgeClasses(row.job.status)}`}>{row.job.status}</span>
                        </div>
                        {summarizeProgress(row.job.progress_json ?? null, row.job.status) && <div className="mt-1 text-xs text-ink/70">{summarizeProgress(row.job.progress_json ?? null, row.job.status)}</div>}
                        {row.latest_event_message && <div className="mt-1 text-xs text-ink/60">{row.latest_event_stage ? `${row.latest_event_stage}: ` : ""}{row.latest_event_message}</div>}
                        {row.job.error_summary && <div className="mt-1 text-xs text-ink/75">{row.job.error_summary}</div>}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-ink/60">Recent Results (24h)</div>
                {recentJobs.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-ink/15 p-4 text-sm text-ink/60">No recent completed/failed jobs for this project.</div>
                ) : (
                  <div className="max-h-[240px] space-y-2 overflow-auto pr-1">
                    {recentJobs.map((row) => (
                      <button key={row.job.id} type="button" onClick={() => setSelectedDocId(row.job.document_id)} className="block w-full rounded-lg border border-ink/10 bg-white p-3 text-left hover:border-[#578FCA]/35">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="min-w-0"><div className="truncate text-sm font-medium text-ink">{row.filename_original ?? row.job.document_id}</div><div className="text-xs text-ink/55">{row.job.job_type} · {formatDateTime(row.job.finished_at ?? row.job.updated_at)}</div></div>
                          <span className={`rounded-full border px-2 py-1 text-xs ${jobBadgeClasses(row.job.status)}`}>{row.job.status}</span>
                        </div>
                        {summarizeProgress(row.job.progress_json ?? null, row.job.status) && <div className="mt-1 text-xs text-ink/70">{summarizeProgress(row.job.progress_json ?? null, row.job.status)}</div>}
                        {row.latest_event_message && <div className="mt-1 text-xs text-ink/60">{row.latest_event_stage ? `${row.latest_event_stage}: ` : ""}{row.latest_event_message}</div>}
                        {row.job.error_summary && <div className="mt-1 text-xs text-ink/75">{row.job.error_summary}</div>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </PageCard>

        <PageCard title="Processing Logs" subtitle={selectedDoc ? `Showing ingestion logs for ${selectedDoc.filename_original}` : "Select a document or queue item to inspect job events"}>
          {!selectedDocId ? (
            <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">Select a document row or queue item to view parsing/chunking/embedding/indexing logs.</div>
          ) : (
            <div className="space-y-2">
              {(logsQuery.data?.items ?? []).map((event) => (
                <div key={event.id} className="rounded-lg border border-ink/10 bg-white p-3">
                  <div className="flex items-center justify-between gap-2 text-xs"><div className="font-semibold uppercase tracking-[0.12em] text-ink/60">{event.stage} / {event.level}</div><div className="text-ink/50">{formatDateTime(event.created_at)}</div></div>
                  <div className="mt-1 text-sm text-ink">{event.message}</div>
                  {event.details_json && <pre className="mt-2 overflow-auto rounded bg-paper/80 p-2 text-xs text-ink/70">{JSON.stringify(event.details_json, null, 2)}</pre>}
                </div>
              ))}
              {(logsQuery.data?.items.length ?? 0) === 0 && <div className="rounded-xl border border-dashed border-ink/15 p-6 text-sm text-ink/60">No processing logs yet for this document.</div>}
            </div>
          )}
        </PageCard>
      </div>

      <FormDialog
        open={isUploadDialogOpen}
        onOpenChange={(open) => {
          setIsUploadDialogOpen(open);
          if (!open && !uploadMutation.isPending) setUploadFile(null);
        }}
        title="Upload document"
        description="Choose target project and file. The document will be queued for processing."
        submitLabel="Upload"
        isSubmitting={uploadMutation.isPending}
        onSubmit={() => {
          if (!uploadFile) {
            addToast({ title: "No file selected", message: "Select a .txt, .md, .pdf, or .docx file before uploading.", kind: "warning" });
            return;
          }
          if (!selectedProjectId) {
            addToast({ title: "No project selected", message: "Choose a target project before uploading.", kind: "warning" });
            return;
          }
          uploadMutation.mutate();
        }}
      >
        <label className="block">
          <div className="mb-1 text-xs text-ink/60">Project</div>
          <select
            value={selectedProjectId ?? ""}
            onChange={(e) => setSelectedProjectId(e.target.value || null)}
            className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
          >
            <option value="">Select project</option>
            {(projectsQuery.data?.items ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <div className="mb-1 text-xs text-ink/60">File</div>
          <input
            type="file"
            accept=".txt,.md,.pdf,.docx"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            className="block w-full rounded-lg border border-ink/12 bg-white px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-[#578FCA]/15 file:px-2 file:py-1 file:text-xs file:font-medium file:text-ink"
          />
        </label>
        {uploadFile ? (
          <div className="rounded-lg bg-white/70 px-3 py-2 text-xs text-ink/70">
            Selected: <span className="font-medium text-ink">{uploadFile.name}</span> ({bytesToHuman(uploadFile.size)})
          </div>
        ) : null}
      </FormDialog>

      <ConfirmDialog
        open={!!docToDelete}
        onOpenChange={(open) => {
          if (!open) setDocToDelete(null);
        }}
        title="Delete document"
        description={
          docToDelete
            ? `Delete ${docToDelete.filename_original}? This removes metadata and indexed vectors for the document.`
            : undefined
        }
        confirmLabel="Delete"
        tone="warning"
        isPending={deleteMutation.isPending}
        onConfirm={() => {
          if (!docToDelete) return;
          deleteMutation.mutate(docToDelete.id);
        }}
      />
    </div>
  );
}

