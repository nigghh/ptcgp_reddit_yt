#!/usr/bin/env bash
set -e

# Python
if [ -f "requirements.txt" ]; then
  python -m pip install --upgrade pip
  pip install -r requirements.txt
fi

# Node
if [ -f "package.json" ]; then
  corepack enable || true
  npm install
fi

# 便利系
git config --global pull.rebase false
echo "post_create done ✅"
