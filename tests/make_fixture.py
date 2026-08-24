"""Generate a deterministic 10k-line log fixture with exactly 3 anomalies.

The bulk is ordinary request-log noise (varying ids/latencies/paths). The three
anomalies are lines whose *structure* is unlike anything else, so a good
grouper collapses the noise into a few templates and leaves the anomalies as
count-1 (or near-1) groups. Deterministic: same output every run.
"""

import random

# The three anomalies. Each is structurally distinct from the request noise
# and from each other. These are what the tool must surface.
ANOMALIES = [
    'CRITICAL kernel panic: unable to mount root fs on unknown-block(0,0)',
    '{"level":"fatal","msg":"database connection pool exhausted","waiters":812,"pool":"primary"}',
    'segfault at 0000dead ip 00007f8a in libssl.so.1.1 sbp 00007ffд error 6',
]

PATHS = ["/api/users", "/api/orders", "/api/products", "/health", "/api/cart"]
METHODS = ["GET", "POST", "PUT", "DELETE"]
STATUSES = [200, 200, 200, 200, 201, 204, 304, 400, 404]


def _request_line(rng):
    method = rng.choice(METHODS)
    path = rng.choice(PATHS)
    status = rng.choice(STATUSES)
    latency = rng.randint(1, 900)
    ip = f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    rid = rng.randbytes(8).hex()
    hh, mm, ss = rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)
    ts = f"2024-05-{rng.randint(1, 28):02d}T{hh:02d}:{mm:02d}:{ss:02d}Z"
    if rng.random() < 0.5:
        # JSON structured variant.
        return (f'{{"ts":"{ts}","method":"{method}","path":"{path}",'
                f'"status":{status},"latency_ms":{latency},"ip":"{ip}","rid":"{rid}"}}')
    return (f'{ts} {method} {path} {status} {latency}ms '
            f'from={ip} rid={rid}')


def generate(total=10000, seed=1234):
    rng = random.Random(seed)
    lines = [_request_line(rng) for _ in range(total - len(ANOMALIES))]
    # Drop each anomaly at a fixed spot so its position is stable but buried.
    positions = [1500, 5000, 8500]
    for pos, anomaly in zip(positions, ANOMALIES):
        lines.insert(pos, anomaly)
    return lines


def write(path, **kwargs):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(generate(**kwargs)) + "\n")


if __name__ == "__main__":
    import sys
    write(sys.argv[1] if len(sys.argv) > 1 else "fixture.log")
