#!/bin/sh

if [ ! -x bitshift ]; then
    gcc bitshift.c -o bitshift
fi

if ! echo "$PATH" | grep -q "$PWD"; then
    export PATH="$PWD:$PATH"
fi
