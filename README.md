# logsift

Grepping production logs for the one request that failed means reading
thousands of lines of noise. `logsift` reads a log stream, groups lines that are
*structurally* the same (same shape, different ids/timestamps/latencies),
collapses each group into a single pattern with a count, and shows you the
**rarest** patterns first — because the line that appears once in 10,000 is
usually the one you are looking for.

It reads stdin, so it composes with `tail`, `kubectl logs`, `journalctl`, and
friends. It handles both JSON log lines and plain text. No dependencies beyond
the Python standard library.

## Why it exists

Anomalies hide in volume. A healthy service emits the same handful of request
lines millions of times; the failure you care about is a needle with a
different structure — a stack trace, a `pool exhausted`, a segfault. Sorting by
frequency ascending puts that needle at the top instead of on page 400.

## Install

```sh
pip install -e .
```

Requires Python 3.9+.

## Usage

Surface the 10 rarest patterns in a file:

```sh
logsift < app.log
```

Pipe from anything:

```sh
kubectl logs deploy/api --tail=-1 | logsift
journalctl -u nginx --no-pager | logsift -n 20
```

Only show patterns seen at most 3 times (drop the routine noise entirely):

```sh
logsift -t 3 < app.log
```

See the noise summary instead — the most frequent patterns:

```sh
logsift --frequent < app.log
```

Live tail: refresh the report every 500 lines as the stream flows:

```sh
tail -f app.log | logsift --follow --every 500
```

### Example

Given 10,000 request-log lines with three anomalies buried inside:

```
$ logsift < fixture.log
10000 lines -> 24 patterns
top 10 rarest patterns

    1x  CRITICAL kernel panic: unable to mount root fs on unknown-block(0,0)
    1x  {"level":"fatal","msg":"database connection pool exhausted","waiters":812,"pool":"primary"}
    1x  segfault at 0000dead ip 00007f8a in libssl.so.1.1 sbp 00007ffд error 6
  226x  2024-05-23T03:54:00Z GET /api/products 400 631ms from=10.0.237.39 rid=41995e174307df2e
  ...
```

All three anomalies surface at the top; the ~10k routine lines collapse into a
couple dozen patterns.

## How it works (and where it is a heuristic)

For each line, logsift builds a **template** by masking the parts that vary:

- JSON objects are grouped by their key set and the *types* of their values, so
  `{"level":"info","status":200}` and `{"level":"warn","status":500}` share a
  template but `{"level":..,"waiters":..}` does not.
- Plain lines are masked token by token: timestamps, UUIDs, IPv4 addresses,
  clock times, long hex blobs, quoted strings, and numbers become placeholders
  (`<TS>`, `<UUID>`, `<IP>`, `<HEX>`, `<STR>`, `<NUM>`).

Lines with the same template are one group. Groups are ranked by count,
ascending.

**This is a heuristic, not a parser.** It knows nothing about your log format.
It will sometimes merge two lines a human would keep apart (two different error
messages that happen to have the same token shape), and sometimes split lines a
human would merge (a value that looks like a number in one line and a word in
another). The masking rules are a fixed list in `logsift/template.py` — tuned
for common request/structured logs, not for every format. If your logs have a
structure these rules miss, the grouping degrades gracefully toward "group by
exact line", which is still useful but less compressive.

There are **no configurable custom patterns** yet, and no clustering of
near-but-not-identical templates (edit distance). Those are honest limitations,
not oversights.

## Development

```sh
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
```

The test suite includes the definition-of-done case: a generated 10,000-line
fixture with three planted anomalies, asserting all three appear in the top 10.

## License

MIT. See [LICENSE](LICENSE).
