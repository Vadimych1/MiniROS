#!/bin/sh
# echo "Adding MiniROS to PATH"
# ppath="$PATH:$(pwd)"
# python3 util/pathadd.py "PATH" "$ppath"
echo "Building and installing pip package"
cd "$(dirname "$0")" || exit 1
cd ..
python3 util/src/build.py "$@"

echo '#!/bin/sh
python3 -m miniros "$@"' | sudo tee /usr/local/bin/miniros > /dev/null
sudo chmod +x /usr/local/bin/miniros

echo "Done"