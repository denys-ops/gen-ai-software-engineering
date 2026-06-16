# Screenshots — MCP call results

Place one PNG per server here. Each should show the **MCP tool call and its result inside
Claude Code** (the terminal session). Exact prompts are in [`../../HOWTORUN.md`](../../HOWTORUN.md).

| File | Must show | Source prompt (short) |
|------|-----------|------------------------|
| `github-mcp-result.png` | github MCP call + list of recent commits/PRs | "list the 5 most recent commits in `denys-ops/gen-ai-software-engineering`" |
| `filesystem-mcp-result.png` | filesystem MCP listing/reading files in `homework-5/` | "list files in `homework-5/` and read `lorem-ipsum.md`" |
| `jira-mcp-result.png` | jira MCP returning last 5 **Bug** tickets (keys only) | "give me the tickets of the last 5 bugs on the KAN project" |
| `custom-mcp-read-tool-result.png` | lorem-ipsum `read` tool result (e.g. word_count=5) | "call the `read` tool with word_count=5" |

> Keep sensitive data out of screenshots — for Jira show only ticket **keys** (e.g. `KAN-12`).
> Optional supporting web screenshots (e.g. the Jira board) may be added as `*-web.png`.
