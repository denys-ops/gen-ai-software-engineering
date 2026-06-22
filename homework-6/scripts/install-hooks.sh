#!/usr/bin/env bash
# Activate the committed git hooks for this repo (one-time, per clone).
# git won't auto-install hooks for security, so each participant runs this once.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
git -C "$REPO_ROOT" config core.hooksPath homework-6/.githooks
chmod +x \
  "$REPO_ROOT/homework-6/.githooks/pre-push" \
  "$REPO_ROOT/homework-6/scripts/coverage-gate.sh" \
  "$REPO_ROOT/homework-6/scripts/claude-push-gate.sh"
echo "Installed: core.hooksPath=homework-6/.githooks"
echo "  - pre-push: blocks pushes that include homework-6 changes if coverage < 80%"
