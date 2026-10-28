"""Reads and writes the entry files of one project."""

from __future__ import annotations

import hashlib
import os
import re
from datetime import date
from pathlib import Path

from bob.entry import ID_PATTERN, Entry, validate

# An entry becomes trusted after this many "useful" votes.
TRUST_AFTER_USEFUL = 2


def data_dir(project: Path) -> Path:
    """Memory lives outside the project so other agents do not find it by browsing the workspace."""
    home = Path(os.environ.get("BOB_HOME", Path.home() / ".bob"))
    digest = hashlib.sha256(str(project).encode()).hexdigest()[:8]
    return home / "projects" / f"{project.name}-{digest}"


class Store:
    def __init__(self, project: Path):
        root = data_dir(project.resolve())
        self.dir = root / "entries"
        self.removed_dir = root / "removed"

    def all(self) -> list[Entry]:
        return [self._read(path) for path in sorted(self.dir.glob("*.md"))]

    def get(self, entry_id: str) -> Entry | None:
        if not ID_PATTERN.match(entry_id):
            return None
        path = self._path(entry_id)
        return self._read(path) if path.exists() else None

    def signature(self) -> tuple:
        """Changes whenever any entry file is added, edited or removed."""
        return tuple((p.name, p.stat().st_mtime_ns) for p in sorted(self.dir.glob("*.md")))

    def add(self, entry_type: str, title: str, summary: str, body: str = "",
            paths: list[str] | None = None, tags: list[str] | None = None) -> Entry:
        entry = Entry(id=self._new_id(title), type=entry_type, title=title,
                      summary=summary, body=body, paths=paths or [], tags=tags or [])
        problems = validate(entry)
        if problems:
            raise ValueError("; ".join(problems))
        self._write(entry)
        return entry

    def update(self, entry_id: str, title: str | None = None, summary: str | None = None,
               body: str | None = None, paths: list[str] | None = None,
               tags: list[str] | None = None) -> Entry:
        """Replace the given fields; the entry counts as freshly verified."""
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        for name, value in ("title", title), ("summary", summary), ("body", body), ("paths", paths), ("tags", tags):
            if value is not None:
                setattr(entry, name, value)
        entry.verified = date.today().isoformat()
        if entry.status == "retired":
            entry.status, entry.wrong = "candidate", 0
        problems = validate(entry)
        if problems:
            raise ValueError("; ".join(problems))
        self._write(entry)
        return entry

    def remove(self, entry_id: str) -> None:
        """Take the entry out of search; the file is kept in `removed/` so a mistake can be undone."""
        if self.get(entry_id) is None:
            raise KeyError(entry_id)
        self.removed_dir.mkdir(parents=True, exist_ok=True)
        os.replace(self._path(entry_id), self.removed_dir / f"{entry_id}.md")

    def record_feedback(self, entry_id: str, useful: bool) -> Entry:
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError(entry_id)
        if useful:
            entry.useful += 1
            if entry.status == "candidate" and entry.useful >= TRUST_AFTER_USEFUL:
                entry.status = "trusted"
        else:
            entry.wrong += 1
            if entry.wrong >= 2 and entry.wrong > entry.useful:
                entry.status = "retired"
        self._write(entry)
        return entry

    def _new_id(self, title: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "entry"
        candidate, number = base, 2
        while self._path(candidate).exists():
            candidate, number = f"{base}-{number}", number + 1
        return candidate

    def _path(self, entry_id: str) -> Path:
        return self.dir / f"{entry_id}.md"

    def _read(self, path: Path) -> Entry:
        try:
            return Entry.from_markdown(path.read_text(encoding="utf-8"))
        except (ValueError, TypeError) as error:
            raise ValueError(f"{path.name}: {error}") from error

    def _write(self, entry: Entry) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._path(entry.id).write_text(entry.to_markdown(), encoding="utf-8")
