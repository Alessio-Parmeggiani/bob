"""MCP server: small tools so agents search cheaply and fetch only what they need."""

from __future__ import annotations

from pathlib import Path

from mcp.server.mcpserver import MCPServer

from bob.entry import Entry
from bob.index import Index
from bob.store import Store

MAX_CARD_OUTPUT_CHARS = 1500


def format_card(entry: Entry) -> str:
    marker = "" if entry.status == "trusted" else f" ({entry.status})"
    return f"{entry.id} [{entry.type}]{marker} {entry.title}: {entry.summary}"


def build_server(project: Path) -> MCPServer:
    store = Store(project)
    index = Index(store)
    server = MCPServer("bob")

    # Handlers are async so they all run on the event loop; the index and files are not thread-safe.
    @server.tool()
    async def search(query: str, paths: list[str] | None = None, k: int = 3) -> str:
        """Find memory cards (id, title, one-line summary) for a task. Pass the files you are about to touch in `paths`."""
        cards = "\n".join(format_card(e) for e in index.search(query, paths, k))
        return cards[:MAX_CARD_OUTPUT_CHARS] or "No memory found."

    @server.tool()
    async def get(id: str) -> str:
        """Read the full text of one memory entry by id."""
        entry = store.get(id)
        if entry is None:
            return f"No entry '{id}'."
        files = f"\nFiles: {', '.join(entry.paths)}" if entry.paths else ""
        return f"{format_card(entry)}{files}\nVerified: {entry.verified}\n\n{entry.body}"

    @server.tool()
    async def add(type: str, title: str, summary: str, body: str = "",
            paths: list[str] | None = None, tags: list[str] | None = None) -> str:
        """Save something verified that a future session should know. Types: map, command, recipe, pitfall, decision. Summary is one line, body at most 40 lines."""
        try:
            saved = store.add(type, title, summary, body, paths, tags)
        except ValueError as error:
            return f"Not saved: {error}"
        similar = [e.id for e in index.search(f"{title} {summary}", k=3) if e.id != saved.id]
        hint = f" Possible overlap, merge with update/remove: {', '.join(similar)}." if similar else ""
        return f"Saved {saved.id}.{hint}"

    @server.tool()
    async def update(id: str, title: str | None = None, summary: str | None = None,
                     body: str | None = None, paths: list[str] | None = None,
                     tags: list[str] | None = None) -> str:
        """Correct or extend an existing entry; only the fields you pass are replaced. Use this instead of adding a near-duplicate."""
        try:
            return f"Updated {store.update(id, title, summary, body, paths, tags).id}."
        except KeyError:
            return f"No entry '{id}'."
        except ValueError as error:
            return f"Not updated: {error}"

    @server.tool()
    async def remove(id: str) -> str:
        """Delete an entry that is wrong, outdated or merged into another."""
        try:
            store.remove(id)
        except KeyError:
            return f"No entry '{id}'."
        return f"Removed {id}."

    @server.tool()
    async def feedback(id: str, useful: bool) -> str:
        """Report whether a memory entry helped (true) or was wrong or outdated (false)."""
        try:
            entry = store.record_feedback(id, useful)
        except KeyError:
            return f"No entry '{id}'."
        return f"{entry.id} is now {entry.status}."

    return server
