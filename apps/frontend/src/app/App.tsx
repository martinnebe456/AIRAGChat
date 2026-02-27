import { useEffect } from "react";

import { AppRouter } from "../routes/AppRouter";
import { ToastHost } from "../components/ToastHost";
import { useAuthStore } from "../store/authStore";
import { initOtel } from "../telemetry/otel";

export function App() {
  const refreshSession = useAuthStore((s) => s.refreshSession);

  useEffect(() => {
    initOtel();
    void refreshSession();
  }, [refreshSession]);

  return (
    <div className="app-shell">
      <AppRouter />
      <ToastHost />
    </div>
  );
}

