#!/usr/bin/env bash
# The hand-in of the challenge (starter_kit/README.md): dist/my_solution/ with the task sources, requirements.txt and
# README.md of starter_kit/my_solution, and in tools/ every tool and its artifacts, in the layout of the repository.
# Only versioned files are copied (in a copy without .git: the files that .gitignore keeps), so no data, caches or
# .env.llm. The official check.py runs on the result.
# Usage: scripts/package.sh
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/dist/my_solution"
tools=(lab scripts .claude/skills docs)

copy() {  # copy <folder of the repository> <destination> [paths inside the folder]
  local src="$root/$1" dest="$2"
  shift 2
  if git -C "$root" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$src" ls-files -z "$@" | rsync -a --from0 --files-from=- "$src/" "$dest/"
  else
    (cd "$src" && rsync -aR --exclude-from="$root/.gitignore" "${@:-.}" "$dest/")
  fi
}

rm -rf "$out" && mkdir -p "$out/tools"
copy starter_kit/my_solution "$out"
copy . "$out/tools" "${tools[@]}"
echo "hand-in: $out"
(cd "$root/starter_kit" && PYTHONDONTWRITEBYTECODE=1 python3 check.py --submission "$out")  # no __pycache__ in the hand-in
