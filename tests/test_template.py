from logsift.template import templatize


def test_numbers_and_ids_collapse_to_same_template():
    a = templatize("GET /api/users 200 12ms rid=abcdef1234567890")
    b = templatize("GET /api/users 404 7ms rid=0011223344556677")
    assert a == b


def test_different_paths_stay_distinct():
    a = templatize("GET /api/users 200")
    b = templatize("GET /api/orders 200")
    assert a != b


def test_timestamp_is_masked():
    line = "2024-05-01T12:00:00Z started worker"
    assert "2024" not in templatize(line)
    assert "<TS>" in templatize(line)


def test_uuid_is_masked():
    line = "job 550e8400-e29b-41d4-a716-446655440000 done"
    assert "<UUID>" in templatize(line)
    assert "550e8400" not in templatize(line)


def test_ip_is_masked():
    assert "<IP>" in templatize("connection from 192.168.1.44:5432 opened")


def test_json_grouped_by_keys_and_value_shape():
    a = templatize('{"level":"info","status":200,"path":"/a"}')
    b = templatize('{"level":"warn","status":500,"path":"/a"}')
    # Same keys, same value types -> same template.
    assert a == b


def test_json_with_different_keys_is_distinct():
    a = templatize('{"level":"info","status":200}')
    b = templatize('{"level":"info","waiters":812}')
    assert a != b


def test_malformed_json_falls_back_to_text_masking():
    # Not valid JSON; must not crash, should mask the number.
    result = templatize('{not really json 500}')
    assert "<NUM>" in result
