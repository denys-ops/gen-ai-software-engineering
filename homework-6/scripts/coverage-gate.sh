#!/usr/bin/env bash
# Shared coverage gate for homework-6.
# Runs the test suite with coverage and fails (non-zero exit) if total coverage is below the
# threshold. Used by both the git pre-push hook and the Claude Code PreToolUse hook.
set -uo pipefail

THRESHOLD="${COVERAGE_THRESHOLD:-80}"
HW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # homework-6/
cd "$HW_DIR" || exit 1

echo "[coverage-gate] running homework-6 tests (threshold ${THRESHOLD}%)..."
uv run pytest --cov --cov-report=term-missing --cov-fail-under="${THRESHOLD}" -q
rc=$?

if [ "$rc" -eq 0 ]; then
  echo "[coverage-gate] PASS: coverage >= ${THRESHOLD}%"
  exit 0
elif [ "$rc" -gt 128 ]; then
  # 128+N == terminated by signal N (e.g. 139 == SIGSEGV): a crash, not a coverage result.
  echo "[coverage-gate] ERROR: pytest crashed (exit ${rc}); cannot verify coverage — push blocked" >&2
  exit 1
else
  echo "[coverage-gate] FAIL: tests failed or coverage < ${THRESHOLD}% — push blocked" >&2
  exit 1
fi
