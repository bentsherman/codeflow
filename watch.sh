#!/bin/bash
# Watch a file and execute a command when the file changes.
#
# Usage: ./watch.sh <infile> '<cmd>'

if [ -z "$(command -v inotifywait)" ]; then
    echo "inotifywait not installed."
    echo "In most distros, it is available in the inotify-tools package."
    exit 1
fi
 
infile=$1
cmd=$2

inotifywait --monitor --quiet --event create,modify "$infile" \
    | while read -rs; do eval "$cmd" ; done
