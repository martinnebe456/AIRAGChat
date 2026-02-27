import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuthStore } from "../store/authStore";

export function RequireRole({
  roles,
  children,
}: {
  roles: string[];
  children: ReactNode;
}) {
  const me = useAuthStore((s) => s.me);
  if (!me) return <Navigate to="/login" replace />;
  if (!roles.includes(me.role)) return <Navigate to="/chat" replace />;
  return <>{children}</>;
}
