#!/usr/bin/bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
list_file="$script_dir/transcendence_local.txt"

if [[ ! -f "$list_file" ]]; then
  echo "Missing list file: $list_file" >&2
  exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" || "$line" == \#* ]] && continue

  repo_path="${line/#\~/$HOME}"
  repo_name="$(basename "$repo_path")"
  parent_dir="$(dirname "$repo_path")"

  mkdir -p "$parent_dir" || exit 1

  if [[ -d "$repo_path" ]]; then
    git switch main
    git -C "$repo_path" pull --rebase origin main
  else
    git clone "https://github.com/Univers42/${repo_name}.git" "$repo_path"
  fi
done < "$list_file"
