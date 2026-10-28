"""Command line: `bob serve` runs the MCP server, `bob check` lints the entries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bob.entry import validate
from bob.store import Store


def check(project: Path) -> int:
    problems = 0
    for entry in Store(project).all():
        for problem in validate(entry):
            print(f"{entry.id}: {problem}")
            problems += 1
    return 1 if problems else 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="bob", description="Brain On Board")
    parser.add_argument("command", choices=["serve", "check"])
    parser.add_argument("--project", type=Path, default=Path.cwd(),
                        help="project root whose memory is used (default: current directory)")
    args = parser.parse_args()
    project = args.project.resolve()

    if args.command == "check":
        sys.exit(check(project))

    from bob.server import build_server  # imported late: `check` should not need the MCP SDK

    build_server(project).run()
