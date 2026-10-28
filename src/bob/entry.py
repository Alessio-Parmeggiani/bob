"""A memory entry is one markdown file: YAML front matter plus a short body."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date

import yaml

ENTRY_TYPES = ("map", "command", "recipe", "pitfall", "decision")
STATUSES = ("candidate", "trusted", "retired")

MAX_SUMMARY_CHARS = 120
MAX_BODY_LINES = 40

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class Entry:
    id: str
    type: str
    title: str
    summary: str
    body: str = ""
    paths: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    status: str = "candidate"
    verified: str = field(default_factory=lambda: date.today().isoformat())
    useful: int = 0
    wrong: int = 0

    def to_markdown(self) -> str:
        meta = asdict(self)
        meta.pop("body")
        header = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
        return f"---\n{header}---\n{self.body.strip()}\n"

    @classmethod
    def from_markdown(cls, text: str) -> Entry:
        _, header, body = text.split("---\n", 2)
        return cls(body=body.strip(), **yaml.safe_load(header))


def validate(entry: Entry) -> list[str]:
    """Return the problems that keep an entry within the size budget; empty if fine."""
    problems = []
    if not ID_PATTERN.match(entry.id):
        problems.append(f"id '{entry.id}' must be lowercase letters, digits and dashes")
    if entry.type not in ENTRY_TYPES:
        problems.append(f"type '{entry.type}' must be one of {ENTRY_TYPES}")
    if entry.status not in STATUSES:
        problems.append(f"status '{entry.status}' must be one of {STATUSES}")
    if not entry.title.strip():
        problems.append("title is empty")
    if not entry.summary.strip() or "\n" in entry.summary:
        problems.append("summary must be one non-empty line")
    if len(entry.summary) > MAX_SUMMARY_CHARS:
        problems.append(f"summary is {len(entry.summary)} chars, max {MAX_SUMMARY_CHARS}")
    body_lines = len(entry.body.strip().splitlines())
    if body_lines > MAX_BODY_LINES:
        problems.append(f"body is {body_lines} lines, max {MAX_BODY_LINES}")
    return problems
