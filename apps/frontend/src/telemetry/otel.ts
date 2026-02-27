let initialized = false;

export function initOtel() {
  if (initialized) return;
  initialized = true;

  const enabled = String(import.meta.env.VITE_OTEL_ENABLED ?? "true") === "true";
  if (!enabled) return;

  // Minimal frontend telemetry hook. The runtime can be expanded with richer
  // instrumentation via OpenTelemetry web packages when desired.
  window.addEventListener("error", (event) => {
    // Keep local telemetry lightweight and avoid leaking sensitive data.
    // eslint-disable-next-line no-console
    console.debug("[otel:web] error", event.message);
  });
}

