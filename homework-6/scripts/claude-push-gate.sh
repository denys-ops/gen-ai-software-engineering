#!/usr/bin/env bash
# Claude Code PreToolUse hook wrapper.
# Receives the tool-call JSON on stdin; if the Bash command is a `git push`, it runs the shared
# coverage gate and blocks (exit 2) when coverage is below threshold. All other commands pass.
set -uo pipefail

input="$(cat)"
cmd="$(printf '%s' "$input" | python3 -c \
  'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' \
  2>/dev/null || true)"

case "$cmd" in
  *"git push"*)
    REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    if bash "$REPO_ROOT/homework-6/scripts/coverage-gate.sh"; then
      exit 0
    else
      echo "Coverage gate failed: homework-6 coverage < 80%. Push blocked." >&2
      exit 2   # exit 2 = block the tool call; stderr is shown to Claude
    fi
    ;;
  *)
    exit 0
    ;;
esac
