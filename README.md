# Bob

Bob (Brain On Board) is a per-project memory for coding agents. Agents search it before exploring a codebase and save what they verified afterwards, so later sessions start with less guessing and fewer tokens. It runs as an MCP server and is used from VS Code Copilot through a custom agent.

## Install

Requires Python 3.10+ and [Poetry](https://python-poetry.org/).

```bash
git clone https://github.com/Alessio-Parmeggiani/bob.git ~/bob
cd ~/bob
poetry install
```

The repo's `poetry.toml` puts the virtual environment in `~/bob/.venv`, so the launcher is `~/bob/.venv/bin/bob`.

## Set up a project

1. In the project, create `.vscode/mcp.json`. Use your own path to the launcher:

   ```json
   {
     "servers": {
       "bob": {
         "type": "stdio",
         "command": "/home/<you>/bob/.venv/bin/bob",
         "args": ["serve", "--project", "${workspaceFolder}"]
       }
     }
   }
   ```

   If the project's `.gitignore` does not already ignore `.vscode`, add the file there or to `.git/info/exclude`, because it contains a path on your machine.

2. Install the agent once for all projects:

   ```bash
   cp ~/bob/agents/bob.agent.md ~/.config/Code/User/prompts/
   ```

   Edit the "Coding priorities" section to match your own preferences.

3. In VS Code, reload the window, run **MCP: List Servers**, select `bob` and choose **Start**.

4. Run **Chat: Manage Tool Approval** and tick the `bob` server so its tools run without a prompt each time.

5. Pick **Bob** in the agent picker and give it a task.

## Where the memory lives

Each project has its own memory in `~/.bob/projects/<project-name>-<hash>/entries/`, one markdown file per entry. It is outside the workspace on purpose, so other agents browsing the project do not find it. Set `BOB_HOME` to use a different root.

An entry that is removed is moved to `removed/` next to `entries/`, so it can be restored by moving the file back.

## Tools

| Tool | Purpose |
|---|---|
| `search` | Find entries for a task. Returns one-line cards. Pass the files you will touch in `paths` to rank entries that list them higher. |
| `get` | Read the full text of one entry. |
| `add` | Save a verified fact. Types: `map`, `command`, `recipe`, `pitfall`, `decision`. The reply lists possibly overlapping entries. |
| `update` | Correct or extend an entry. Only the fields you pass change. |
| `remove` | Delete a wrong, outdated or merged entry. |
| `feedback` | Report that an entry helped or was wrong. Two useful votes make it trusted; wrong votes retire it. |

Size limits: summary at most 120 characters and one line, body at most 40 lines.

## Commands

```bash
bob serve --project <path>   # run the MCP server (the editor does this)
bob check --project <path>   # report entries that break the size limits
```

## Development

```bash
poetry install
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 poetry run pytest
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` is only needed when a ROS environment is sourced, because ROS registers pytest plugins that fail to load in this virtual environment.
