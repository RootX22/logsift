"""Reduce a log line to a structural template by masking variable tokens.

Two lines that differ only in their variable parts (ids, numbers, timestamps,
paths, quoted values) reduce to the same template. That template is the key we
group by. It is a heuristic: it will occasionally merge lines that a human
would keep apart, or split lines a human would merge. See README.
"""

import json
import re

# Ordered list of (compiled pattern, placeholder). Order matters: the most
# specific / longest patterns must come first so a UUID is not eaten piecemeal
# by the hex or number rules.
_RULES = [
    # ISO-8601 timestamps, with optional timezone and fractional seconds.
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),
     "<TS>"),
    # UUIDs.
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<UUID>"),
    # IPv4 (optionally with :port).
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b"), "<IP>"),
    # Clock times like 12:34:56 that did not get caught by the TS rule.
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(?:\.\d+)?\b"), "<TIME>"),
    # Long hex blobs (hashes, request ids). At least 8 hex chars.
    (re.compile(r"\b[0-9a-fA-F]{8,}\b"), "<HEX>"),
    # Quoted strings (single or double).
    (re.compile(r'"[^"]*"'), "<STR>"),
    (re.compile(r"'[^']*'"), "<STR>"),
    # Numbers (ints, floats, with optional sign), including a trailing unit
    # suffix like "12ms" or "3.5s" so the unit stays but the value collapses.
    # Not preceded by a word char, so it does not bite into ids like "abc123".
    (re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?"), "<NUM>"),
]


def _mask(text):
    for pattern, placeholder in _RULES:
        text = pattern.sub(placeholder, text)
    return text


def _flatten_json(obj, prefix=""):
    """Yield (dotted-key, value) leaves of a parsed JSON object.

    Keys are kept (they are structural); values are what varies, so the
    template is built from keys plus masked values.
    """
    if isinstance(obj, dict):
        for key in sorted(obj):
            yield from _flatten_json(obj[key], f"{prefix}{key}.")
        return
    if isinstance(obj, list):
        # Collapse list contents: only its shape matters for grouping.
        yield (prefix.rstrip("."), "<LIST>")
        return
    yield (prefix.rstrip("."), obj)


def _json_template(obj):
    parts = []
    for key, value in _flatten_json(obj):
        if isinstance(value, str):
            # A JSON string value is variable data; collapse it whole so lines
            # sharing a key shape group together regardless of the text.
            masked = "<STR>"
        elif isinstance(value, bool):
            masked = "<BOOL>"
        elif isinstance(value, (int, float)):
            masked = "<NUM>"
        elif value is None:
            masked = "<NULL>"
        else:
            masked = "<LIST>"
        parts.append(f"{key}={masked}")
    return "{" + " ".join(parts) + "}"


def templatize(line):
    """Return a structural template string for one raw log line.

    If the line is a JSON object, group by its keys and value shapes; that is
    far more robust than regex-masking serialized JSON. Otherwise fall back to
    token masking on the plain text.
    """
    stripped = line.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            obj = json.loads(stripped)
        except (ValueError, TypeError):
            obj = None
        if isinstance(obj, dict):
            return _json_template(obj)
    # Collapse runs of whitespace so alignment padding does not create noise.
    return re.sub(r"\s+", " ", _mask(stripped))
