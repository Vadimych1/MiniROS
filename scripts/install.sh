#!/bin/sh
# echo "Adding MiniROS to PATH"
# ppath="$PATH:$(pwd)"
# python3 util/pathadd.py "PATH" "$ppath"
echo "Building and installing pip package"
cd "$(dirname "$0")" || exit 1
python3 util/build.py
echo "Done"