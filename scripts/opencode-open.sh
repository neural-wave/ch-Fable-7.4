#!/usr/bin/env bash
# OpenCode on an open-weights model; protocol, endpoint, key and model come from .env.llm (not versioned).
# Usage: scripts/opencode-open.sh [run|mini|models] [opencode arguments], e.g. scripts/opencode-open.sh run --auto "..."
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
env_file="$root/.env.llm"
if [[ ! -f "$env_file" ]]; then
  echo "missing $env_file: copy .env.llm.example and fill in endpoint, key, model and context" >&2
  exit 1
fi
set -a; source "$env_file"; set +a
if grep -q REPLACE_ME <<<"$OPEN_BASE_URL $OPEN_API_KEY $OPEN_MODEL $OPEN_CONTEXT"; then
  echo "fill in OPEN_BASE_URL, OPEN_API_KEY, OPEN_MODEL and OPEN_CONTEXT in $env_file" >&2
  exit 1
fi
export OPEN_PROTOCOL="${OPEN_PROTOCOL:-openai}"
export OPEN_BASE_URL="${OPEN_BASE_URL%/}"
export OPEN_MAX_OUTPUT="${OPEN_MAX_OUTPUT:-8192}"              # the 32000 default eats a small window
if [[ ! "$OPEN_PROTOCOL" =~ ^(openai|anthropic)$ || ! "$OPEN_CONTEXT" =~ ^[0-9]+$ || ! "$OPEN_MAX_OUTPUT" =~ ^[0-9]+$ ]]; then
  echo "OPEN_PROTOCOL must be openai or anthropic, OPEN_CONTEXT and OPEN_MAX_OUTPUT numbers of tokens" >&2
  exit 1
fi
export OPENCODE_CONFIG="$root/scripts/opencode-open.jsonc"     # provider "open" with this model, and no other
# --standalone: a private server started here reads the variables above, the shared background service does not
case "${1:-}" in
  run|mini|models) exec opencode "$1" --standalone "${@:2}" ;;
  *) exec opencode --standalone "$@" ;;
esac
