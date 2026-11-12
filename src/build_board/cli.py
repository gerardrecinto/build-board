from __future__ import annotations

import argparse
import os
import sys

from . import __version__, graph, manifest, report


def _deps(data: dict) -> dict[str, list[str]]:
    return {m: list(v.get("deps", [])) for m, v in data["modules"].items()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="build-board", description="Build order, coverage gates and a build page for multi-module SDK builds.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("plan", help="print the build order, one parallel level per line")
    pl.add_argument("manifest")
    pl.add_argument("--changed", nargs="+", metavar="MODULE", help="only the modules that must rebuild for this change")

    ck = sub.add_parser("check", help="exit 1 if a build failed, coverage is low, or a tag or SDK pin is wrong")
    ck.add_argument("manifest")
    ck.add_argument("--min-coverage", type=float, help="override the manifest's min_coverage")

    rp = sub.add_parser("report", help="write the HTML page")
    rp.add_argument("manifest")
    rp.add_argument("--out", required=True, help="output directory (index.html is written inside)")
    rp.add_argument("--title", default="Build board")

    args = p.parse_args(argv)
    try:
        data = manifest.load(args.manifest)
        base = os.path.dirname(os.path.abspath(args.manifest))
        if args.cmd == "plan":
            deps = _deps(data)
            if args.changed:
                for m in graph.affected(deps, args.changed):
                    print(m)
            else:
                for i, level in enumerate(graph.levels(deps)):
                    print(f"level {i}: {' '.join(level)}")
            return 0
        board = manifest.build(data, base, getattr(args, "min_coverage", None))
        if args.cmd == "check":
            for prob in board.problems:
                print(prob)
            print(f"{len(board.problems)} problem(s) in {len(board.rows)} modules")
            return 1 if board.problems else 0
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "index.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report.render(board, args.title))
        print(f"wrote {path}")
        return 0
    except (graph.GraphError, KeyError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
