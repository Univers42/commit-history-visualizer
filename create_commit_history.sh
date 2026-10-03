#!/usr/bin/bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="$script_dir/venv"
venv_python="$venv_dir/bin/python"

if [[ ! -x "$venv_python" ]]; then
    rm -rf "$venv_dir"
    if ! python3 -m venv "$venv_dir"; then
        echo "Unable to create a Python virtual environment at $venv_dir." >&2
        echo "Install the venv module for this Python (on Debian/Ubuntu: python3-venv) and run the script again." >&2
        exit 1
    fi
fi



"$venv_python" -m pip install --disable-pip-version-check -r "$script_dir/requirements.txt"
exec "$venv_python" "$script_dir/store_github_commit_history.py" "$@"
