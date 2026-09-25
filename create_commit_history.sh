#!/usr/bin/bash

cd 42/transcendence || exit 0

rm -rf commits.sqlite3

python3 store_github_commit_history.py --repos-file transcendence_local.txt --db commits.sqlite3