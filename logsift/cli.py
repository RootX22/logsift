"""Command-line entry point. Reads stdin so it composes with tail -f."""

import argparse
import sys

from . import __version__
from .aggregate import Aggregator


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="logsift",
        description="Collapse noisy logs into patterns and surface the rare lines.",
    )
    parser.add_argument("-n", "--limit", type=int, default=10,
                        help="how many groups to show (default: 10)")
    parser.add_argument("-t", "--threshold", type=int, default=None,
                        help="only show groups seen at most this many times")
    parser.add_argument("--frequent", action="store_true",
                        help="show the most frequent patterns instead of the rarest")
    parser.add_argument("--follow", action="store_true",
                        help="stream mode: reprint the report after every N lines "
                             "(use with tail -f); see --every")
    parser.add_argument("--every", type=int, default=1000,
                        help="in --follow mode, refresh every N lines (default: 1000)")
    parser.add_argument("--version", action="version",
                        version=f"logsift {__version__}")
    return parser


def _format_report(agg, args):
    if args.frequent:
        groups = agg.frequent(limit=args.limit)
        heading = f"top {len(groups)} most frequent patterns"
    else:
        groups = agg.rare(limit=args.limit, threshold=args.threshold)
        heading = f"top {len(groups)} rarest patterns"

    lines = [
        f"{agg.total} lines -> {agg.group_count} patterns",
        heading,
        "",
    ]
    width = len(str(max((g.count for g in groups), default=1)))
    for group in groups:
        count = str(group.count).rjust(width)
        lines.append(f"  {count}x  {group.example}")
    return "\n".join(lines)


def main(argv=None):
    args = _build_parser().parse_args(argv)
    agg = Aggregator()

    if args.follow:
        for line in sys.stdin:
            agg.add(line)
            if agg.total % args.every == 0:
                sys.stdout.write("\033[2J\033[H")  # clear screen, cursor home
                sys.stdout.write(_format_report(agg, args) + "\n")
                sys.stdout.flush()
        # Final report after the stream ends.
        print(_format_report(agg, args))
        return 0

    for line in sys.stdin:
        agg.add(line)
    print(_format_report(agg, args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
