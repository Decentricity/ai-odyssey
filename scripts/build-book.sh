#!/usr/bin/env bash
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${AI_ODYSSEY_IN_PROOT:-}" ]] && { ! command -v pandoc >/dev/null 2>&1 || ! command -v chromium >/dev/null 2>&1; }; then
  if command -v proot-distro >/dev/null 2>&1; then
    quoted_root="$(printf "%q" "$repo_root")"
    quoted_args=()
    for arg in "$@"; do
      quoted_args+=("$(printf "%q" "$arg")")
    done
    exec proot-distro login debian -- bash -lc "cd $quoted_root && AI_ODYSSEY_IN_PROOT=1 bash scripts/build-book.sh ${quoted_args[*]}"
  fi
fi

python3 "$repo_root/scripts/build-book.py" "$@"
