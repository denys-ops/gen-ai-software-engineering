# Screenshots

Captured from the live Claude Code session and embedded in the PR description:

| File | Capture |
|---|---|
| `spec-part1.png` … `-part4.png` | `/write-spec` producing `specification.md` (5 sections + Low-Level Tasks) |
| `pipeline-run.png` | Output of `uv run python integrator.py` (8 transactions processed) |
| `test-coverage.png` | `uv run pytest --cov` — 69 passed, 99% total coverage |
| `skill-run-pipeline-part1.png` … `-part3.png` | The `/run-pipeline` slash command executing in Claude Code |
| `hook-trigger.png` | The coverage-gate hook blocking a push (pytest gate fails → push blocked) |
| `mcp-integration-part1.png`, `-part2.png` | Custom MCP `get_transaction_status(TXN002)` result **and** a context7 FastMCP docs lookup |
| `readme-part1.png` … `-part3.png` | `README.md` showing the author name + ASCII diagram |
