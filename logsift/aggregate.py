"""Group lines by template, count them, and rank so the rare ones surface."""

from dataclasses import dataclass, field

from .template import templatize


@dataclass
class Group:
    template: str
    count: int = 0
    first_line_no: int = 0
    example: str = ""
    # A few distinct raw examples, for context in the output.
    examples: list = field(default_factory=list)


class Aggregator:
    """Streaming accumulator: feed lines in, ask for the ranked report out."""

    def __init__(self, max_examples=1):
        self._groups = {}
        self._total = 0
        self._max_examples = max_examples

    def add(self, line, line_no=None):
        line = line.rstrip("\n")
        if not line.strip():
            return
        self._total += 1
        template = templatize(line)
        group = self._groups.get(template)
        if group is None:
            group = Group(template=template, first_line_no=line_no or self._total,
                          example=line)
            self._groups[template] = group
        group.count += 1
        if not group.example:
            group.example = line
        if len(group.examples) < self._max_examples and line not in group.examples:
            group.examples.append(line)

    @property
    def total(self):
        return self._total

    @property
    def group_count(self):
        return len(self._groups)

    def rare(self, limit=10, threshold=None):
        """Return groups ranked rarest-first.

        Ranking: ascending count, then earliest appearance. A pattern seen
        twice in 10k lines is what you are hunting for; a pattern seen 4000
        times is the noise you want to skip. When ``threshold`` is given, only
        groups with count <= threshold are returned.
        """
        groups = list(self._groups.values())
        if threshold is not None:
            groups = [g for g in groups if g.count <= threshold]
        groups.sort(key=lambda g: (g.count, g.first_line_no))
        return groups[:limit]

    def frequent(self, limit=10):
        """Return groups ranked most-frequent-first (the noise summary)."""
        groups = sorted(self._groups.values(),
                        key=lambda g: (-g.count, g.first_line_no))
        return groups[:limit]
