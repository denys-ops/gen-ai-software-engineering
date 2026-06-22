# Homework 5 — MCP Server Configuration (GitHub, Filesystem, Jira, Custom FastMCP)

**Author:** Denys Kondratiuk
**Course:** GenAI and Agentic AI for Software Engineering

---

## Overview

This homework configures **three external MCP servers** and builds **one custom MCP server**,
all wired into **Claude Code** via a project-scoped `.mcp.json`:

| # | Server | Type | Transport | Purpose |
|---|--------|------|-----------|---------|
| 1 | **GitHub** | external (official) | remote HTTP + PAT | Query repos, PRs, commits, issues |
| 2 | **Filesystem** | external (official) | local stdio (npx) | List/read files in this repository |
| 3 | **Jira** | external (official Atlassian) | remote SSE + OAuth | Query a real Jira project (last 5 bugs) |
| 4 | **lorem-ipsum** | **custom (FastMCP)** | local stdio (uv) | Serve word-limited text from `lorem-ipsum.md` |

> ℹ️ The Jira project is a free Jira Cloud demo site created specifically for this homework
> (no production credentials are committed). Only ticket keys/numbers are shown in screenshots.

---

## Resources vs. Tools (MCP concepts)

The custom server demonstrates the two core MCP primitives:

- **Resources** are *URIs that Claude can read from* — files, APIs, or dynamic content. They are
  read-only, side-effect-free data sources (think "GET"). Here: `lorem://words/{word_count}`.
- **Tools** are *actions Claude can call* to perform operations — read a file, run a command,
  mutate state (think "POST"). Here: the `read` tool.

Both expose the same underlying logic (return the first *N* words of `lorem-ipsum.md`), showing
how the same capability can be offered as a passive resource or an invokable action.

---

## The Custom Server (`custom-mcp-server/`)

```
custom-mcp-server/
├── server.py          # FastMCP server: lorem://words/{word_count} resource + read tool
├── lorem-ipsum.md     # source text the resource/tool reads from
└── pyproject.toml     # dependencies (includes fastmcp) — managed by uv
```

- **Resource** `lorem://words/{word_count}` — reads `lorem-ipsum.md`, returns exactly
  `word_count` words (default **30**).
- **Tool** `read(word_count: int = 30)` — same behaviour as a callable action.
- Word count is clamped to `[1, total_words]` so bad input never breaks the call.

Verified locally over the real MCP protocol (stdio subprocess), e.g. `read(4)` →
`"Lorem ipsum dolor sit"`, resource `lorem://words/7` → 7 words.

---

## Files / Deliverables

| Deliverable | Location |
|-------------|----------|
| MCP configuration (all 4 servers) | [`.mcp.json`](.mcp.json) |
| Custom FastMCP server | [`custom-mcp-server/server.py`](custom-mcp-server/server.py) |
| Dependencies (incl. `fastmcp`) | [`custom-mcp-server/pyproject.toml`](custom-mcp-server/pyproject.toml) |
| Lorem ipsum source | [`custom-mcp-server/lorem-ipsum.md`](custom-mcp-server/lorem-ipsum.md) |
| Run / connect / usage instructions | [`HOWTORUN.md`](HOWTORUN.md) |
| Screenshots of MCP call results | [`docs/screenshots/`](docs/screenshots/) |

---

## AI Tools Used

- **Claude Code** (Opus 4.8) — scaffolding, server implementation, config, and protocol testing.
- **FastMCP 3.x** — framework for the custom server.
- **Official MCP servers** — GitHub (remote), Filesystem (`@modelcontextprotocol/server-filesystem`),
  Atlassian/Jira (remote).

See [`HOWTORUN.md`](HOWTORUN.md) for full setup and the exact prompts used to capture each screenshot.
