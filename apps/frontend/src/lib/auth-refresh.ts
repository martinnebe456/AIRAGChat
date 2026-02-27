import { useAuthStore } from "../store/authStore";

export async function ensureSession(): Promise<boolean> {
  const me = useAuthStore.getState().me;
  if (me) return true;
  return useAuthStore.getState().refreshSession();
}

