import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "../store/authStore";

export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  const me = useAuthStore((s) => s.me);
  const loading = useAuthStore((s) => s.loading);

  if (loading) {
    return <div className="p-8 text-center text-ink/70">Loading session...</div>;
  }
  if (!me) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
