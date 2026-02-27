import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../api/client";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { PageCard, ProviderBadge } from "../components/Ui";
import { useUiStore } from "../store/uiStore";

type NamespaceConfig = { value_json: Record<string, unknown> };

type OpenAIStatus = {
  has_key?: boolean;
  masked_preview?: string | null;
  last_rotated_at?: string | null;
  last_tested_at?: string | null;
  validation_status?: Record<string, unknown>;
};

type ModelsSettingsResponse = {
  namespace: string;
  key: string;
  value_json: {
    chat_model_id?: string;
    embedding_model_id?: string;
    embedding_batch_size?: number;
    eval_judge_model_id?: string | null;
    pdf_limits?: {
      max_upload_mb?: number;
      max_pdf_pages?: number;
    };
  };
  version: number;
};

type EmbeddingProfileSummary = {
  id: string;
  name: string;
  provider: "openai_api";
  model_id: string;
  dimensions: number;
  qdrant_collection_name: string;
  status: string;
};

type EmbeddingSettingsResponse = {
  value_json: {
    model_id?: string;
    batch_size?: number;
    input_prefix_mode?: "e5" | "none" | "openai_native";
    qdrant_alias_name?: string;
  };
  active_profile?: EmbeddingProfileSummary | null;
  latest_draft_profile?: EmbeddingProfileSummary | null;
};

type EmbeddingValidateResponse = {
  ok: boolean;
  provider: string;
  model_id: string;
  dimensions?: number | null;
  detail?: string | null;
  warnings?: string[];
};

type EmbeddingReindexRunResponse = { id: string; status: string };

export function AdminSettingsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const [openAiKeyInput, setOpenAiKeyInput] = useState("");
  const [modelsDraft, setModelsDraft] = useState({
    chat_model_id: "gpt-4o-mini",
    embedding_model_id: "text-embedding-3-small",
    embedding_batch_size: 32,
    eval_judge_model_id: "gpt-4o-mini",
    pdf_limits: { max_upload_mb: 100, max_pdf_pages: 1000 },
  });
  const [ragDraft, setRagDraft] = useState<Record<string, unknown>>({});
  const [telemetryDraft, setTelemetryDraft] = useState<Record<string, unknown>>({});
  const [ragDraftText, setRagDraftText] = useState("{}");
  const [telemetryDraftText, setTelemetryDraftText] = useState("{}");
  const [embeddingDraft, setEmbeddingDraft] = useState({
    provider: "openai_api" as const,
    model_id: "text-embedding-3-small",
    batch_size: 32,
    input_prefix_mode: "openai_native" as "e5" | "none" | "openai_native",
    distance_metric: "cosine",
    normalize_embeddings: true,
    qdrant_alias_name: "documents_chunks_active",
    create_draft_profile: true,
  });
  const [embeddingValidation, setEmbeddingValidation] = useState<EmbeddingValidateResponse | null>(null);
  const [confirmRemoveKeyOpen, setConfirmRemoveKeyOpen] = useState(false);

  const openAiStatusQuery = useQuery({
    queryKey: ["admin-openai-status"],
    queryFn: async () => apiClient.get<OpenAIStatus>("/admin/openai/status"),
  });
  const modelsSettingsQuery = useQuery({
    queryKey: ["settings-models"],
    queryFn: async () => apiClient.get<ModelsSettingsResponse>("/settings/models"),
  });
  const ragSettingsQuery = useQuery({
    queryKey: ["settings-rag"],
    queryFn: async () => apiClient.get<NamespaceConfig>("/settings/rag"),
  });
  const telemetrySettingsQuery = useQuery({
    queryKey: ["settings-telemetry"],
    queryFn: async () => apiClient.get<NamespaceConfig>("/settings/telemetry"),
  });
  const embeddingSettingsQuery = useQuery({
    queryKey: ["settings-embeddings"],
    queryFn: async () => apiClient.get<EmbeddingSettingsResponse>("/settings/embeddings"),
  });

  useEffect(() => {
    const v = modelsSettingsQuery.data?.value_json;
    if (!v) return;
    setModelsDraft({
      chat_model_id: String(v.chat_model_id ?? "gpt-4o-mini"),
      embedding_model_id: String(v.embedding_model_id ?? "text-embedding-3-small"),
      embedding_batch_size: Number(v.embedding_batch_size ?? 32),
      eval_judge_model_id: String(v.eval_judge_model_id ?? v.chat_model_id ?? "gpt-4o-mini"),
      pdf_limits: {
        max_upload_mb: Number(v.pdf_limits?.max_upload_mb ?? 100),
        max_pdf_pages: Number(v.pdf_limits?.max_pdf_pages ?? 1000),
      },
    });
  }, [modelsSettingsQuery.data]);

  useEffect(() => {
    if (ragSettingsQuery.data) {
      const next = (ragSettingsQuery.data.value_json ?? {}) as Record<string, unknown>;
      setRagDraft(next);
      setRagDraftText(JSON.stringify(next, null, 2));
    }
  }, [ragSettingsQuery.data]);
  useEffect(() => {
    if (telemetrySettingsQuery.data) {
      const next = (telemetrySettingsQuery.data.value_json ?? {}) as Record<string, unknown>;
      setTelemetryDraft(next);
      setTelemetryDraftText(JSON.stringify(next, null, 2));
    }
  }, [telemetrySettingsQuery.data]);
  useEffect(() => {
    const v = embeddingSettingsQuery.data?.value_json;
    if (!v) return;
    setEmbeddingDraft((prev) => ({
      ...prev,
      provider: "openai_api",
      model_id: String(v.model_id ?? prev.model_id),
      batch_size: Number(v.batch_size ?? prev.batch_size),
      input_prefix_mode: (v.input_prefix_mode as "e5" | "none" | "openai_native") ?? prev.input_prefix_mode,
      qdrant_alias_name: String(v.qdrant_alias_name ?? prev.qdrant_alias_name),
    }));
  }, [embeddingSettingsQuery.data]);

  const saveKeyMutation = useMutation({
    mutationFn: async () => apiClient.put("/admin/openai/key", { api_key: openAiKeyInput }),
    onSuccess: async () => {
      setOpenAiKeyInput("");
      addToast({ title: "OpenAI key saved", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["admin-openai-status"] });
    },
    onError: (e) => addToast({ title: "Key save failed", message: (e as Error).message, kind: "error" }),
  });
  const testKeyMutation = useMutation({
    mutationFn: async () => apiClient.post("/admin/openai/key/test", openAiKeyInput ? { api_key: openAiKeyInput } : {}),
    onSuccess: async () => {
      addToast({ title: "OpenAI key test complete", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["admin-openai-status"] });
    },
    onError: (e) => addToast({ title: "Key test failed", message: (e as Error).message, kind: "error" }),
  });
  const rotateKeyMutation = useMutation({
    mutationFn: async () => apiClient.post("/admin/openai/key/rotate", { api_key: openAiKeyInput }),
    onSuccess: async () => {
      setOpenAiKeyInput("");
      addToast({ title: "OpenAI key rotated", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["admin-openai-status"] });
    },
    onError: (e) => addToast({ title: "Key rotation failed", message: (e as Error).message, kind: "error" }),
  });
  const deleteKeyMutation = useMutation({
    mutationFn: async () => apiClient.delete("/admin/openai/key"),
    onSuccess: async () => {
      addToast({ title: "OpenAI key removed", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["admin-openai-status"] });
    },
    onError: (e) => addToast({ title: "Key removal failed", message: (e as Error).message, kind: "error" }),
  });

  const saveModelsMutation = useMutation({
    mutationFn: async () => apiClient.put("/settings/models", modelsDraft),
    onSuccess: async () => {
      addToast({ title: "Model settings saved", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["settings-models"] });
    },
    onError: (e) => addToast({ title: "Model settings save failed", message: (e as Error).message, kind: "error" }),
  });

  const saveRagMutation = useMutation({
    mutationFn: async () => {
      const parsed = JSON.parse(ragDraftText) as Record<string, unknown>;
      setRagDraft(parsed);
      return apiClient.put("/settings/rag", { value_json: parsed });
    },
    onSuccess: async () => {
      addToast({ title: "RAG settings saved", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["settings-rag"] });
    },
    onError: (e) => addToast({ title: "RAG settings save failed", message: (e as Error).message, kind: "error" }),
  });
  const saveTelemetryMutation = useMutation({
    mutationFn: async () => {
      const parsed = JSON.parse(telemetryDraftText) as Record<string, unknown>;
      setTelemetryDraft(parsed);
      return apiClient.put("/settings/telemetry", { value_json: parsed });
    },
    onSuccess: async () => {
      addToast({ title: "Telemetry settings saved", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["settings-telemetry"] });
    },
    onError: (e) => addToast({ title: "Telemetry settings save failed", message: (e as Error).message, kind: "error" }),
  });

  const validateEmbeddingsMutation = useMutation({
    mutationFn: async () =>
      apiClient.post<EmbeddingValidateResponse>("/admin/embeddings/validate", {
        provider: "openai_api",
        model_id: embeddingDraft.model_id,
        batch_size: embeddingDraft.batch_size,
        input_prefix_mode: embeddingDraft.input_prefix_mode,
      }),
    onSuccess: (result) => {
      setEmbeddingValidation(result);
      addToast({ title: "Embedding config validated", kind: "success" });
    },
    onError: (e) => addToast({ title: "Embedding validation failed", message: (e as Error).message, kind: "error" }),
  });

  const saveEmbeddingsMutation = useMutation({
    mutationFn: async () => apiClient.put("/settings/embeddings", embeddingDraft),
    onSuccess: async () => {
      addToast({ title: "Embedding draft saved", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["settings-embeddings"] });
      await qc.invalidateQueries({ queryKey: ["settings-models"] });
    },
    onError: (e) => addToast({ title: "Embedding settings save failed", message: (e as Error).message, kind: "error" }),
  });

  const startReindexMutation = useMutation({
    mutationFn: async () =>
      apiClient.post<EmbeddingReindexRunResponse>("/admin/embeddings/reindex-runs", {
        use_latest_draft: true,
        scope: { kind: "all_documents" },
      }),
    onSuccess: async (run) => {
      addToast({ title: "Embedding reindex started", message: `Run ${run.id.slice(0, 8)}`, kind: "info" });
      await qc.invalidateQueries({ queryKey: ["embeddings-reindex-runs"] });
      navigate("/admin/embeddings/reindex");
    },
    onError: (e) => addToast({ title: "Start reindex failed", message: (e as Error).message, kind: "error" }),
  });

  const openAiStatus = openAiStatusQuery.data;
  const keyMeta = openAiStatus ?? {};
  const activeProfile = embeddingSettingsQuery.data?.active_profile ?? null;
  const draftProfile = embeddingSettingsQuery.data?.latest_draft_profile ?? null;

  return (
    <div className="grid gap-4">
      <PageCard title="Runtime Mode" subtitle="OpenAI-only runtime (local Ollama/Llama Stack removed).">
        <div className="flex items-center justify-between rounded-xl border border-ink/10 bg-white p-4">
          <div>
            <div className="text-sm font-semibold text-ink">Inference + Embeddings Provider</div>
            <div className="text-xs text-ink/60">
              All chat and document embeddings run through OpenAI API (backend-only key storage).
            </div>
          </div>
          <ProviderBadge provider="openai_api" />
        </div>
      </PageCard>

      <PageCard title="OpenAI Key" subtitle="Backend-only encrypted API key for chat and embeddings.">
        <div className="grid gap-4 xl:grid-cols-[0.6fr_0.4fr]">
          <div className="rounded-xl border border-ink/10 bg-white p-4">
            <div className="mb-2 text-sm text-ink/70">
              Stored key:{" "}
              <span className="font-medium text-ink">
                {keyMeta.has_key ? keyMeta.masked_preview || "masked" : "not configured"}
              </span>
            </div>
            <input
              type="password"
              value={openAiKeyInput}
              onChange={(e) => setOpenAiKeyInput(e.target.value)}
              placeholder="Paste OpenAI API key"
              className="mb-3 w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => saveKeyMutation.mutate()}
                disabled={!openAiKeyInput || saveKeyMutation.isPending}
                className="rounded-lg bg-ink px-3 py-2 text-sm text-paper disabled:opacity-60"
              >
                Save
              </button>
              <button type="button" onClick={() => testKeyMutation.mutate()} className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
                Test
              </button>
              <button
                type="button"
                onClick={() => rotateKeyMutation.mutate()}
                disabled={!openAiKeyInput || rotateKeyMutation.isPending}
                className="rounded-lg border border-sky/30 bg-sky/10 px-3 py-2 text-sm text-sky disabled:opacity-60"
              >
                Rotate
              </button>
              <button
                type="button"
                onClick={() => setConfirmRemoveKeyOpen(true)}
                className="rounded-lg border border-[#FADA7A]/80 bg-[#F5F0CD]/95 px-3 py-2 text-sm text-ink"
              >
                Remove
              </button>
            </div>
          </div>
          <div className="rounded-xl border border-ink/10 bg-white p-4">
            <div className="mb-2 text-sm font-semibold text-ink">Validation status</div>
            <pre className="overflow-auto rounded-lg bg-ink p-3 text-xs text-paper">
              {JSON.stringify(keyMeta.validation_status ?? {}, null, 2)}
            </pre>
          </div>
        </div>
      </PageCard>

      <PageCard title="OpenAI Models & PDF Limits" subtitle="Single chat model, embedding model, and large PDF safeguards.">
        <div className="grid gap-3 rounded-xl border border-ink/10 bg-white p-4 md:grid-cols-2">
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Chat model</div>
            <input
              value={modelsDraft.chat_model_id}
              onChange={(e) => setModelsDraft((p) => ({ ...p, chat_model_id: e.target.value }))}
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Embedding model</div>
            <input
              value={modelsDraft.embedding_model_id}
              onChange={(e) => setModelsDraft((p) => ({ ...p, embedding_model_id: e.target.value }))}
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Embedding batch size</div>
            <input
              type="number"
              min={1}
              max={256}
              value={modelsDraft.embedding_batch_size}
              onChange={(e) => setModelsDraft((p) => ({ ...p, embedding_batch_size: Math.max(1, Number(e.target.value) || 1) }))}
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Eval judge model (optional)</div>
            <input
              value={modelsDraft.eval_judge_model_id ?? ""}
              onChange={(e) => setModelsDraft((p) => ({ ...p, eval_judge_model_id: e.target.value }))}
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Max upload size (MB)</div>
            <input
              type="number"
              min={1}
              max={500}
              value={modelsDraft.pdf_limits.max_upload_mb}
              onChange={(e) =>
                setModelsDraft((p) => ({
                  ...p,
                  pdf_limits: { ...p.pdf_limits, max_upload_mb: Math.max(1, Number(e.target.value) || 1) },
                }))
              }
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="block">
            <div className="mb-1 text-xs text-ink/60">Max PDF pages</div>
            <input
              type="number"
              min={1}
              max={5000}
              value={modelsDraft.pdf_limits.max_pdf_pages}
              onChange={(e) =>
                setModelsDraft((p) => ({
                  ...p,
                  pdf_limits: { ...p.pdf_limits, max_pdf_pages: Math.max(1, Number(e.target.value) || 1) },
                }))
              }
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
          <div className="md:col-span-2">
            <button
              type="button"
              onClick={() => saveModelsMutation.mutate()}
              disabled={saveModelsMutation.isPending}
              className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-paper disabled:opacity-60"
            >
              {saveModelsMutation.isPending ? "Saving..." : "Save Model Settings"}
            </button>
          </div>
        </div>
      </PageCard>

      <PageCard title="Embeddings (OpenAI-only)" subtitle="Validate, save draft profile, and run safe reindex using staging collection + alias apply.">
        <div className="grid gap-4 xl:grid-cols-[0.58fr_0.42fr]">
          <div className="space-y-4">
            <div className="rounded-xl border border-ink/10 bg-white p-4">
              <div className="mb-2 text-sm font-semibold text-ink">Draft Embedding Config</div>
              <div className="grid gap-3">
                <label className="block">
                  <div className="mb-1 text-xs text-ink/60">Embedding model</div>
                  <input
                    value={embeddingDraft.model_id}
                    onChange={(e) => setEmbeddingDraft((p) => ({ ...p, model_id: e.target.value }))}
                    className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
                  />
                </label>
                <div className="grid gap-3 md:grid-cols-2">
                  <label className="block">
                    <div className="mb-1 text-xs text-ink/60">Batch size</div>
                    <input
                      type="number"
                      min={1}
                      max={256}
                      value={embeddingDraft.batch_size}
                      onChange={(e) => setEmbeddingDraft((p) => ({ ...p, batch_size: Math.max(1, Number(e.target.value) || 1) }))}
                      className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="block">
                    <div className="mb-1 text-xs text-ink/60">Prefix mode</div>
                    <select
                      value={embeddingDraft.input_prefix_mode}
                      onChange={(e) => setEmbeddingDraft((p) => ({ ...p, input_prefix_mode: e.target.value as "e5" | "none" | "openai_native" }))}
                      className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
                    >
                      <option value="openai_native">openai_native</option>
                      <option value="none">none</option>
                      <option value="e5">e5</option>
                    </select>
                  </label>
                </div>
                <label className="block">
                  <div className="mb-1 text-xs text-ink/60">Qdrant alias name</div>
                  <input
                    value={embeddingDraft.qdrant_alias_name}
                    onChange={(e) => setEmbeddingDraft((p) => ({ ...p, qdrant_alias_name: e.target.value }))}
                    className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
                  />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={() => validateEmbeddingsMutation.mutate()} className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
                  Validate
                </button>
                <button type="button" onClick={() => saveEmbeddingsMutation.mutate()} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper">
                  Save Draft
                </button>
                <button
                  type="button"
                  onClick={() => startReindexMutation.mutate()}
                  disabled={startReindexMutation.isPending}
                  className="rounded-lg border border-sky/30 bg-sky/10 px-3 py-2 text-sm text-sky disabled:opacity-60"
                >
                  Start Reindex
                </button>
                <button type="button" onClick={() => navigate("/admin/embeddings/reindex")} className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm">
                  Reindex Dashboard
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-ink/10 bg-white p-4">
              <div className="mb-2 text-sm font-semibold text-ink">Active Profile</div>
              <div className="text-sm text-ink/70">
                <div>Provider: <span className="font-medium text-ink">{activeProfile?.provider ?? "-"}</span></div>
                <div>Model: <span className="font-medium text-ink">{activeProfile?.model_id ?? "-"}</span></div>
                <div>Dimensions: <span className="font-medium text-ink">{activeProfile?.dimensions ?? "-"}</span></div>
                <div className="truncate">Collection: <span className="font-mono text-xs text-ink">{activeProfile?.qdrant_collection_name ?? "-"}</span></div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-xl border border-[#FADA7A]/80 bg-[#F5F0CD]/95 p-4 text-sm text-ink">
              <div className="mb-1 font-semibold">Large PDF processing safeguards</div>
              <div>Uploads are async and progress-aware. Limits are enforced server-side (`max_upload_mb`, `max_pdf_pages`). OCR is currently disabled.</div>
            </div>
            <div className="rounded-xl border border-ink/10 bg-white p-4">
              <div className="mb-2 text-sm font-semibold text-ink">Validation Result</div>
              {embeddingValidation ? (
                <div className="space-y-1 text-sm text-ink/70">
                  <div>Status: <span className={embeddingValidation.ok ? "font-semibold text-[#3674B5]" : "font-semibold text-[#578FCA]"}>{embeddingValidation.ok ? "OK" : "Failed"}</span></div>
                  <div>Provider / Model: {embeddingValidation.provider} / {embeddingValidation.model_id}</div>
                  <div>Dimensions: {embeddingValidation.dimensions ?? "-"}</div>
                  {embeddingValidation.detail && <div>Detail: {embeddingValidation.detail}</div>}
                  {(embeddingValidation.warnings?.length ?? 0) > 0 && (
                    <ul className="mt-2 list-disc pl-5 text-xs text-ink/80">
                      {embeddingValidation.warnings?.map((w) => <li key={w}>{w}</li>)}
                    </ul>
                  )}
                </div>
              ) : (
                <div className="text-sm text-ink/60">Run validation to probe OpenAI embeddings and detect dimensions.</div>
              )}
            </div>
            <div className="rounded-xl border border-ink/10 bg-white p-4">
              <div className="mb-2 text-sm font-semibold text-ink">Draft Profile</div>
              {draftProfile ? (
                <div className="space-y-1 text-sm text-ink/70">
                  <div>Name: <span className="font-medium text-ink">{draftProfile.name}</span></div>
                  <div>Model: <span className="font-medium text-ink">{draftProfile.model_id}</span></div>
                  <div>Dimensions: <span className="font-medium text-ink">{draftProfile.dimensions}</span></div>
                  <div>Status: <span className="font-medium text-ink">{draftProfile.status}</span></div>
                </div>
              ) : (
                <div className="text-sm text-ink/60">No draft profile yet.</div>
              )}
            </div>
          </div>
        </div>
      </PageCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <PageCard title="RAG Defaults" subtitle="Advanced retrieval/answer behavior settings (JSON).">
          <textarea
            value={ragDraftText}
            onChange={(e) => setRagDraftText(e.target.value)}
            className="h-72 w-full rounded-xl border border-ink/15 bg-white p-3 font-mono text-xs"
          />
          <div className="mt-3">
            <button type="button" onClick={() => saveRagMutation.mutate()} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper">
              Save RAG Settings
            </button>
          </div>
        </PageCard>

        <PageCard title="Telemetry Settings" subtitle="Frontend telemetry runtime settings (JSON).">
          <textarea
            value={telemetryDraftText}
            onChange={(e) => setTelemetryDraftText(e.target.value)}
            className="h-72 w-full rounded-xl border border-ink/15 bg-white p-3 font-mono text-xs"
          />
          <div className="mt-3">
            <button type="button" onClick={() => saveTelemetryMutation.mutate()} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper">
              Save Telemetry Settings
            </button>
          </div>
        </PageCard>
      </div>

      <ConfirmDialog
        open={confirmRemoveKeyOpen}
        onOpenChange={setConfirmRemoveKeyOpen}
        title="Remove OpenAI API key"
        description="Remove the stored OpenAI API key from encrypted backend storage?"
        confirmLabel="Remove key"
        tone="warning"
        isPending={deleteKeyMutation.isPending}
        onConfirm={() => deleteKeyMutation.mutate(undefined, { onSuccess: () => setConfirmRemoveKeyOpen(false) })}
      />
    </div>
  );
}
