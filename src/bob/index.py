"""Full-text search over the entries, rebuilt in memory when the files change."""

from __future__ import annotations

import re
import sqlite3
from fnmatch import fnmatch

from bob.entry import Entry
from bob.store import Store

PATH_MATCH_BONUS = 5.0
TRUSTED_BONUS = 1.0
CANDIDATE_POOL = 50


class Index:
    def __init__(self, store: Store):
        self.store = store
        self._signature: tuple | None = None
        self._entries: dict[str, Entry] = {}
        self._db = sqlite3.connect(":memory:", check_same_thread=False)

    def search(self, query: str, paths: list[str] | None = None, k: int = 3) -> list[Entry]:
        """Best entries for the query words, boosted when they list one of `paths`."""
        self._refresh()
        scores = self._text_scores(query)
        for entry in self._entries.values():
            if any(fnmatch(path, pattern) for path in paths or [] for pattern in entry.paths):
                scores[entry.id] = scores.get(entry.id, 0.0) + PATH_MATCH_BONUS
        ranked = []
        for entry_id, score in scores.items():
            entry = self._entries[entry_id]
            if entry.status == "retired":
                continue
            bonus = TRUSTED_BONUS if entry.status == "trusted" else 0.0
            ranked.append((score + bonus, entry))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in ranked[:k]]

    def _text_scores(self, query: str) -> dict[str, float]:
        words = re.findall(r"[A-Za-z0-9]+", query)
        if not words:
            return {}
        match = " OR ".join(f'"{word}"' for word in words)
        rows = self._db.execute(
            "SELECT id, bm25(fts, 0, 5, 3, 2, 2, 1) FROM fts WHERE fts MATCH ? "
            "ORDER BY 2 LIMIT ?", (match, CANDIDATE_POOL)).fetchall()
        return {entry_id: -rank for entry_id, rank in rows}  # bm25 is lower-is-better

    def _refresh(self) -> None:
        signature = self.store.signature()
        if signature == self._signature:
            return
        self._entries = {entry.id: entry for entry in self.store.all()}
        self._db.execute("DROP TABLE IF EXISTS fts")
        self._db.execute(
            "CREATE VIRTUAL TABLE fts USING fts5(id UNINDEXED, title, summary, tags, paths, body)")
        self._db.executemany(
            "INSERT INTO fts VALUES (?, ?, ?, ?, ?, ?)",
            [(e.id, e.title, e.summary, " ".join(e.tags), " ".join(e.paths), e.body)
             for e in self._entries.values()])
        self._signature = signature
