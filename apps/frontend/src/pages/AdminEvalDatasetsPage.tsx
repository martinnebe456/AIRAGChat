import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { PageCard } from "../components/Ui";
import { formatDateTime } from "../lib/formatters";
import { useUiStore } from "../store/uiStore";

type DatasetRow = {
  id: string;
  name: string;
  description?: string | null;
  source_format: string;
  item_count: number;
  status: string;
  created_at: string;
};

export function AdminEvalDatasetsPage() {
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const [name, setName] = useState("Imported Dataset");
  const [jsonText, setJsonText] = useState(
    JSON.stringify(
      [
        {
          case_key: "demo-1",
          question: "What is RAG?",
          expected_answer: "retrieval augmented generation",
          expects_refusal: false,
        },
      ],
      null,
      2,
    ),
  );

  const datasetsQuery = useQuery({
    queryKey: ["eval-datasets"],
    queryFn: async () => apiClient.get<{ items: DatasetRow[] }>("/evals/datasets"),
  });

  const importMutation = useMutation({
    mutationFn: async () => {
      const items = JSON.parse(jsonText) as unknown[];
      return apiClient.post("/evals/datasets/import", {
        name,
        description: "Imported from Admin UI",
        source_format: "json",
        items,
      });
    },
    onSuccess: async () => {
      addToast({ title: "Dataset imported", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["eval-datasets"] });
    },
    onError: (e) => addToast({ title: "Import failed", message: (e as Error).message, kind: "error" }),
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <PageCard title="Evaluation Datasets" subtitle="Import and review datasets for RAG regression testing.">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink/10 text-xs uppercase tracking-[0.12em] text-ink/60">
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Format</th>
                <th className="px-2 py-2">Items</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {(datasetsQuery.data?.items ?? []).map((ds) => (
                <tr key={ds.id} className="border-b border-ink/5">
                  <td className="px-2 py-2">
                    <div className="font-medium text-ink">{ds.name}</div>
                    {ds.description && <div className="text-xs text-ink/55">{ds.description}</div>}
                  </td>
                  <td className="px-2 py-2">{ds.source_format}</td>
                  <td className="px-2 py-2">{ds.item_count}</td>
                  <td className="px-2 py-2">{ds.status}</td>
                  <td className="px-2 py-2 text-xs text-ink/60">{formatDateTime(ds.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PageCard>

      <PageCard title="Import Dataset" subtitle="JSON array upload/import for local evaluation test cases.">
        <div className="grid gap-3">
          <input value={name} onChange={(e) => setName(e.target.value)} className="rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm" placeholder="Dataset name" />
          <textarea value={jsonText} onChange={(e) => setJsonText(e.target.value)} className="min-h-[360px] rounded-lg border border-ink/15 bg-white px-3 py-2 font-mono text-xs" />
          <button type="button" onClick={() => importMutation.mutate()} className="rounded-lg bg-ink px-3 py-2 text-sm text-paper">
            Import JSON Dataset
          </button>
        </div>
      </PageCard>
    </div>
  );
}

