import { useEffect } from "react";

import { useUiStore } from "../store/uiStore";

function getToastClasses(kind?: "info" | "success" | "warning" | "error") {
  switch (kind) {
    case "success":
      return "border-[#3674B5]/35 bg-[#F5F0CD]/95";
    case "warning":
      return "border-[#FADA7A]/70 bg-[#FADA7A]/45";
    case "error":
      return "border-[#FADA7A]/85 bg-[#F5F0CD]/95";
    case "info":
    default:
      return "border-[#578FCA]/35 bg-white/95";
  }
}

function getToastAccent(kind?: "info" | "success" | "warning" | "error") {
  switch (kind) {
    case "success":
      return "bg-[#3674B5]";
    case "warning":
      return "bg-[#FADA7A]";
    case "error":
      return "bg-[#578FCA]";
    case "info":
    default:
      return "bg-[#578FCA]";
  }
}

export function ToastHost() {
  const toasts = useUiStore((s) => s.toasts);
  const dismiss = useUiStore((s) => s.dismissToast);

  useEffect(() => {
    const timers = toasts.map((toast) =>
      window.setTimeout(() => dismiss(toast.id), toast.durationMs ?? 3500),
    );
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [toasts, dismiss]);

  return (
    <div className="pointer-events-none fixed right-5 top-5 z-[110] flex w-[min(460px,95vw)] flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto relative overflow-hidden rounded-xl border p-3 shadow-panel backdrop-blur-md ring-1 ring-white/60 ${getToastClasses(toast.kind)}`}
        >
          <div className={`absolute inset-y-0 left-0 w-1 ${getToastAccent(toast.kind)}`} />
          <div className="flex items-start justify-between gap-3">
            <div className="pl-1">
              <div className="text-sm font-semibold text-ink">{toast.title}</div>
              {toast.message && <div className="mt-1 text-xs text-ink/70">{toast.message}</div>}
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="rounded px-2 py-1 text-xs text-ink/70 hover:bg-[#578FCA]/10"
            >
              Close
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
