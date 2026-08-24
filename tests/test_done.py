"""Definition-of-done: 10k lines, 3 anomalies, all 3 in the top 10 rare output."""

import subprocess
import sys

from make_fixture import generate

from logsift.aggregate import Aggregator


def test_all_three_anomalies_in_top_ten():
    agg = Aggregator()
    for line in generate():
        agg.add(line)

    top = agg.rare(limit=10)
    joined = "\n".join(g.example for g in top)

    # kernel panic
    assert "kernel panic" in joined
    # exhausted pool (JSON anomaly)
    assert "database connection pool exhausted" in joined
    # segfault
    assert "segfault" in joined


def test_noise_is_actually_collapsed():
    agg = Aggregator()
    for line in generate():
        agg.add(line)
    # 10k lines of request noise must collapse to a small number of patterns,
    # otherwise "grouping" is doing nothing.
    assert agg.total == 10000
    assert agg.group_count < 50


def test_cli_end_to_end(tmp_path):
    fixture = tmp_path / "fixture.log"
    fixture.write_text("\n".join(generate()) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "logsift", "-n", "10"],
        stdin=fixture.open(encoding="utf-8"),
        capture_output=True, text=True, check=True,
    )
    for needle in ("kernel panic", "database connection pool exhausted", "segfault"):
        assert needle in result.stdout, f"missing {needle!r} in output:\n{result.stdout}"
