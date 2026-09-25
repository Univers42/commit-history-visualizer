#!/usr/bin/bash

mkdir -p ~/projects/transcendence
cd ~/projects/transcendence || exit 0



for repo in "${repositories[@]}"; do
  if [ -d "$repo" ]; then
    cd "$repo" || exit 0
    git pull --rebase origin main
    cd ..
  else
    git clone "git@github.com:Univers42/$repo"
  fi
done
