#!/usr/bin/env bash
# The hand-in of the challenge (starter_kit/README.md): dist/my_solution/ with the task sources, requirements.txt and
# README.md of starter_kit/my_solution, and in tools/ every tool and its artifacts, in the layout of the repository.
# Only versioned files are copied: no data, caches or .env.llm. The official check.py runs on the result.
# Usage: scripts/package.sh
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/dist/my_solution"
tools=(lab scripts .claude/skills docs .env.llm.example)
rm -rf "$out" && mkdir -p "$out/tools"
git -C "$root/starter_kit/my_solution" ls-files -z | rsync -a --from0 --files-from=- "$root/starter_kit/my_solution/" "$out/"
git -C "$root" ls-files -z "${tools[@]}" | rsync -a --from0 --files-from=- "$root/" "$out/tools/"
echo "hand-in: $out"
(cd "$root/starter_kit" && PYTHONDONTWRITEBYTECODE=1 python3 check.py --submission "$out")  # no __pycache__ in the hand-in
