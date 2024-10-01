#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
"$DIR/PHASe.app/Contents/MacOS/PHASe" "$DIR/updater.py" "$1" "$2"