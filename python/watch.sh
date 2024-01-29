#!/bin/bash

if [[ $# != 1 ]]; then
    >&2 echo "usage: ./watch.sh <infile>"
    exit 1
fi

infile="$1"
mmdfile="$(dirname "$infile")/$(basename "$infile" .py).mmd"

../watch.sh "$infile" "codeflow $infile > $mmdfile && mmdc -q -i $mmdfile -e png"
