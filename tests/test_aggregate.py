from logsift.aggregate import Aggregator


def test_counts_grouped_lines():
    agg = Aggregator()
    for i in range(5):
        agg.add(f"GET /api/users 200 {i}ms")
    assert agg.total == 5
    assert agg.group_count == 1
    assert agg.rare()[0].count == 5


def test_blank_lines_ignored():
    agg = Aggregator()
    agg.add("")
    agg.add("   ")
    agg.add("\n")
    assert agg.total == 0
    assert agg.group_count == 0


def test_rare_ranks_least_frequent_first():
    agg = Aggregator()
    for _ in range(100):
        agg.add("GET /health 200 1ms")
    agg.add("FATAL disk full on /var")
    rarest = agg.rare(limit=1)[0]
    assert "FATAL" in rarest.example
    assert rarest.count == 1


def test_threshold_filters_out_noise():
    agg = Aggregator()
    for _ in range(50):
        agg.add("GET /health 200 1ms")
    agg.add("rare one")
    groups = agg.rare(threshold=1)
    assert len(groups) == 1
    assert groups[0].example == "rare one"


def test_frequent_ranks_most_frequent_first():
    agg = Aggregator()
    for _ in range(10):
        agg.add("GET /a 200")
    agg.add("GET /b 200")
    top = agg.frequent(limit=1)[0]
    assert top.count == 10
