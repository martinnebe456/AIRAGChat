from __future__ import annotations

from prometheus_client import Counter, Histogram

chat_requests_total = Counter(
    "airagchat_chat_requests_total",
    "Total chat requests handled",
    ["provider", "status"],
)

chat_latency_ms = Histogram(
    "airagchat_chat_latency_ms",
    "Chat response latency in milliseconds",
    buckets=(50, 100, 250, 500, 1000, 2000, 5000, 10000),
)

ingestion_jobs_total = Counter(
    "airagchat_ingestion_jobs_total",
    "Total ingestion jobs processed",
    ["status"],
)

