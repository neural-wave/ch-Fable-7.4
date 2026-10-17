#!/usr/bin/env bash
# Claude Code on an open-weights model; endpoint, key and model come from .env.llm (not versioned).
# Usage: scripts/claude-open.sh [claude arguments], e.g. scripts/claude-open.sh -p "..." --allowedTools "Bash"
set -euo pipefail
env_file="$(cd "$(dirname "$0")/.." && pwd)/.env.llm"
if [[ ! -f "$env_file" ]]; then
  echo "missing $env_file: copy .env.llm.example and fill in endpoint, key and model" >&2
  exit 1
fi
set -a; source "$env_file"; set +a
if grep -q REPLACE_ME <<<"$ANTHROPIC_AUTH_TOKEN $OPEN_MODEL $OPEN_CONTEXT"; then
  echo "fill in ANTHROPIC_AUTH_TOKEN, OPEN_MODEL and OPEN_CONTEXT in $env_file" >&2
  exit 1
fi
export ANTHROPIC_API_KEY=""                                    # bearer token only, as in the Ollama docs
export ANTHROPIC_MODEL="$OPEN_MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$OPEN_MODEL"              # every alias resolves to the open model,
export ANTHROPIC_DEFAULT_SONNET_MODEL="$OPEN_MODEL"            # so subagents and background tasks never
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$OPEN_MODEL"             # ask the server for a Claude model ID
export CLAUDE_CODE_SUBAGENT_MODEL="$OPEN_MODEL"
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="$OPEN_CONTEXT"          # real window, so compaction happens in time
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${OPEN_MAX_OUTPUT:-8192}" # the 32000 default eats a small window
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1                # no pre-release fields the server does not know
exec claude --model "$OPEN_MODEL" "$@"
