import { create } from "zustand";

type Toast = {
  id: string;
  title: string;
  message?: string;
  kind?: "info" | "success" | "warning" | "error";
  durationMs?: number;
};

type UiState = {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  dismissToast: (id: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: crypto.randomUUID() }],
    })),
  dismissToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));
