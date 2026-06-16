# HOWTORUN — Homework 5 MCP Servers

This guide covers: **installing dependencies**, **running the custom server**, **connecting the
MCP configuration** to Claude Code, and **using/testing each server** (including the `read` tool).

> Prerequisites: macOS/Linux, [`uv`](https://docs.astral.sh/uv/), Node.js (for `npx`), and
> Claude Code (`claude`). A GitHub account, and a (free) Jira Cloud site for Task 3.

---

## 0. The MCP configuration: `.mcp.json`

All four servers are registered in [`.mcp.json`](.mcp.json). Claude Code auto-loads a project's
`.mcp.json` from the **repository root** (a copy of this file lives there too).

Every `claude mcp add` command below uses **`-s project`** so the server is written to the
**project-scoped** `.mcp.json` (committed, shared with the repo) — **not** to your account or to
the per-user local scope. This is what makes the configuration part of the homework deliverable.

> Scopes recap: `-s project` → repo `.mcp.json` (committed) · `-s local` (default) → private
> `~/.claude.json` for this project only · `-s user` → global across all your projects.
> On first load Claude Code asks **"Use this project's MCP servers?"** — approve it.

```jsonc
{
  "mcpServers": {
    "github":      { "type": "http", "url": "https://api.githubcopilot.com/mcp/" },
    "filesystem":  { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "<ABS_REPO_PATH>"] },
    "jira":        { "type": "sse",  "url": "https://mcp.atlassian.com/v1/sse" },
    "lorem-ipsum": { "command": "uv", "args": ["run", "--directory", "<ABS_PATH>/homework-5/custom-mcp-server", "server.py"] }
  }
}
```

Verify what Claude Code sees at any time:

```bash
claude mcp list        # lists registered servers + connection status
# inside a Claude Code session:
/mcp                   # interactive view; use it to complete OAuth for github/jira
```

---

## Task 1 — GitHub MCP (remote, PAT)

> ℹ️ The remote GitHub MCP endpoint does **not** support OAuth *dynamic client
> registration*, so Claude Code's automatic `/mcp` OAuth flow fails with
> `Incompatible auth server: does not support dynamic client registration`.
> Use a **Personal Access Token (PAT)** instead — the supported approach.

1. Create a **fine-grained PAT** (GitHub → Settings → Developer settings →
   Personal access tokens → Fine-grained): resource owner `denys-ops`,
   repository `gen-ai-software-engineering`, read permissions for *Contents,
   Pull requests, Issues, Metadata*. (A classic token with `repo` scope also works.)

2. Export the token, then register the server at **project scope** using the
   `${GITHUB_PAT}` placeholder. The single quotes keep the literal placeholder
   in `.mcp.json` so **the token itself is never written to the committed file**:

```bash
export GITHUB_PAT=github_pat_YOUR_TOKEN

claude mcp add -s project --transport http github https://api.githubcopilot.com/mcp/ \
  --header 'Authorization: Bearer ${GITHUB_PAT}'
```

Verify with `claude mcp list` → `github: ✓ connected`.

**Test prompt** (capture the result):
> "Using the github MCP, list the 5 most recent commits in
> `denys-ops/gen-ai-software-engineering` and summarize them."

📸 Save terminal screenshot → `docs/screenshots/github-mcp-result.png`

---

## Task 2 — Filesystem MCP (local, stdio)

```bash
claude mcp add -s project filesystem -- npx -y @modelcontextprotocol/server-filesystem \
  /Users/almin/PycharmProjects/gen-ai-software-engineering
```

No auth needed. The server is restricted to the directory you pass it.

**Test prompt** (capture the result):
> "Using the filesystem MCP, list the files in `homework-5/` and read
> `homework-5/custom-mcp-server/lorem-ipsum.md`."

📸 Save terminal screenshot → `docs/screenshots/filesystem-mcp-result.png`

---

## Task 3 — Jira MCP (remote Atlassian, OAuth)

One-time Jira setup: create a free **Jira Cloud** site, a project (e.g. `KAN`), and ~5 issues of
type **Bug**. Then register the official Atlassian remote MCP:

```bash
claude mcp add -s project --transport sse jira https://mcp.atlassian.com/v1/sse
```

Run `/mcp` → **jira** → complete OAuth (grants access to your Atlassian site).

**Required test prompt** (capture request + response):
> "Using the jira MCP, give me the tickets of the last 5 bugs on the KAN project."

> ⚠️ Show only ticket **keys/numbers** (e.g. `KAN-12`) in the screenshot — avoid sensitive data.

📸 Save terminal screenshot → `docs/screenshots/jira-mcp-result.png`

---

## Task 4 — Custom FastMCP server (`lorem-ipsum`)

### 4.1 Install dependencies

```bash
cd homework-5/custom-mcp-server
uv sync            # installs fastmcp (see pyproject.toml)
```

`fastmcp` is declared in [`pyproject.toml`](custom-mcp-server/pyproject.toml) under `dependencies`.

### 4.2 Run the server (verify it starts)

```bash
uv run server.py   # starts FastMCP over stdio; Ctrl-C to stop
```

You should see `Starting MCP server 'lorem-ipsum-server' with transport 'stdio'`.

### 4.3 Connect to Claude Code

```bash
claude mcp add -s project lorem-ipsum -- uv run \
  --directory /Users/almin/PycharmProjects/gen-ai-software-engineering/homework-5/custom-mcp-server \
  server.py
```

(Already present in `.mcp.json`.) Confirm with `claude mcp list` → `lorem-ipsum: ✓ connected`.

### 4.4 Use / test the `read` tool

**Test prompts** (capture the result):
> "Using the lorem-ipsum MCP, call the `read` tool with word_count=5."
> → expected: `Lorem ipsum dolor sit amet`

> "Read the resource `lorem://words/10`."
> → expected: 10 words.

> "Call `read` with no arguments." → expected: 30 words (default).

📸 Save terminal screenshot → `docs/screenshots/custom-mcp-read-tool-result.png`

### 4.5 Quick local sanity check (no Claude Code needed)

```bash
cd homework-5/custom-mcp-server
uv run python -c "
import asyncio
from fastmcp import Client
from server import mcp

async def main():
    async with Client(mcp) as c:
        print(await c.call_tool('read', {'word_count': 5}))

asyncio.run(main())
"
```

---

## Screenshot checklist

| File | Captured from |
|------|---------------|
| `docs/screenshots/github-mcp-result.png` | Claude Code terminal — github tool call + result |
| `docs/screenshots/filesystem-mcp-result.png` | Claude Code terminal — filesystem list/read |
| `docs/screenshots/jira-mcp-result.png` | Claude Code terminal — last 5 bug tickets |
| `docs/screenshots/custom-mcp-read-tool-result.png` | Claude Code terminal — `read` tool result |
