from prometheus_client import Counter, Gauge, Histogram

# COUNTER: only goes up. Sliced by backend, status, and cache hit.
REQUESTS = Counter(
    "gateway_requests_total",
    "Total inference requests handled",
    ["backend", "status", "cached"],
)

# HISTOGRAM: buckets latency so we can compute p50/p95/p99 later.
LATENCY = Histogram(
    "gateway_request_latency_seconds",
    "End-to-end request latency in seconds",
    ["backend"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# GAUGE: goes up and down. How many requests are in flight right now.
IN_FLIGHT = Gauge(
    "gateway_in_flight_requests",
    "Requests currently being processed",
)
