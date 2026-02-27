export type ProviderOption = "openai_api";
export type ModelCategory = "low" | "medium" | "high";
export type EmbeddingProviderOption = "openai_api";

export type EmbeddingProfileSummaryDto = {
  id: string;
  name: string;
  provider: EmbeddingProviderOption;
  model_id: string;
  dimensions: number;
  distance_metric: string;
  normalize_embeddings: boolean;
  input_prefix_mode: "e5" | "none" | "openai_native";
  qdrant_collection_name: string;
  qdrant_alias_name?: string | null;
  status: string;
  is_active: boolean;
  validation_status_json?: Record<string, unknown> | null;
};

export type EmbeddingSettingsDto = {
  namespace: string;
  key: string;
  value_json: Record<string, unknown>;
  version: number;
  updated_at?: string;
  active_profile?: EmbeddingProfileSummaryDto | null;
  latest_draft_profile?: EmbeddingProfileSummaryDto | null;
};

export type EmbeddingStatusDto = {
  active_alias_name: string;
  active_alias_target?: string | null;
  active_profile?: EmbeddingProfileSummaryDto | null;
  latest_draft_profile?: EmbeddingProfileSummaryDto | null;
  settings?: Record<string, unknown>;
  openai_key_status?: Record<string, unknown>;
  reindex_summary?: Record<string, unknown>;
};

export type EmbeddingValidationDto = {
  ok: boolean;
  provider: string;
  model_id: string;
  dimensions?: number | null;
  detail?: string | null;
  warnings?: string[];
  metadata?: Record<string, unknown>;
};

export type EmbeddingReindexRunDto = {
  id: string;
  status: string;
  target_embedding_profile_id: string;
  source_embedding_profile_id?: string | null;
  qdrant_staging_collection: string;
  summary_json?: Record<string, unknown> | null;
  drift_detected_count?: number;
  created_at?: string;
  updated_at?: string;
};

export type EmbeddingReindexRunItemDto = {
  id: string;
  run_id: string;
  document_id: string;
  status: string;
  attempt_count: number;
  indexed_chunk_count: number;
  needs_catchup: boolean;
  error_summary?: string | null;
  created_at?: string;
  updated_at?: string;
};

export function bytesToHuman(bytes: number) {
  if (!Number.isFinite(bytes) || bytes < 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
}
