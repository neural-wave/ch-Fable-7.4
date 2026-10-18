#!/usr/bin/env bash
# The hand-in of the challenge (starter_kit/README.md): dist/my_solution/ with the task sources, requirements.txt and
# README.md of starter_kit/my_solution, and in tools/ every tool and its artifacts, in the layout of the repository.
# Only the files git does not ignore are copied, versioned or new (in a copy without .git: the files that .gitignore
# keeps), so no data, caches or .env.llm; lab/runs.zip, a raw export of the run folders, stays out too. The hand-in
# must stay below 15 MB, and the official check.py runs on the result.
# Usage: scripts/package.sh   (PYTHON chooses the interpreter, NEURON_LEGACY and NEURON_TARGETS the data folders)
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/dist/my_solution"
tools=(lab scripts .claude/skills docs)
exclude=(':(exclude)lab/runs.zip')
limit_mb=15

copy() {  # copy <folder of the repository> <destination> [paths inside the folder]
  local src="$root/$1" dest="$2"
  shift 2
  if git -C "$root" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$src" ls-files -z --cached --others --exclude-standard -- "${@:-.}" "${exclude[@]}" |
      while IFS= read -r -d '' file; do [ -e "$src/$file" ] && printf '%s\0' "$file"; done |
      tar -C "$src" --null -T - -cf - | tar -C "$dest" -xf -
  else
    (cd "$src" && rsync -aR --exclude-from="$root/.gitignore" --exclude=runs.zip "${@:-.}" "$dest/")
  fi
}

rm -rf "$out" && mkdir -p "$out/tools"
copy starter_kit/my_solution "$out"
copy . "$out/tools" "${tools[@]}"
size_kb=$(du -sk "$out" | cut -f1)
echo "hand-in: $out ($((size_kb / 1024)).$(( (size_kb % 1024) * 10 / 1024 )) MB)"
if [ "$size_kb" -gt $((limit_mb * 1024)) ]; then
  echo "the hand-in is larger than $limit_mb MB" >&2
  exit 1
fi
(cd "$root/starter_kit" && PYTHONDONTWRITEBYTECODE=1 "${PYTHON:-python3}" check.py --submission "$out" \
  --legacy "${NEURON_LEGACY:-$root/legacy}" --targets "${NEURON_TARGETS:-$root/targets}")  # no __pycache__ in the hand-in
