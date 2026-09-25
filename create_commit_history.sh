#!/usr/bin/bash

cd ./transcendence || exit 0

rm -rf commits.sqlite3

cd ..
python3 store_github_commit_history.py --repos-file transcendence_local.txt --db commits.sqlite3