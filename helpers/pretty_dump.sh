#!/bin/sh

if [ $# -ne 1 ]; then
    echo "usage: $(basename $0) file"
    exit 1
fi

HDR=$(hexdump -n6 -e '2/1 "%02x"' "$1")

dump ()
{
    LENGTH=18
    WIDTH=6
    FN=$1; shift
    if [ ! -z "$1" ]; then LENGTH="$1"; shift; fi
    if [ ! -z "$1" ]; then WIDTH="$1"; shift; fi
    echo $LENGTH $WIDTH
    hexdump -s$WIDTH -e '"%08_ad  " '$LENGTH'/1 "%02x "' -e '"  |" '$LENGTH'/1 "%_p" "|\n"' "$FN"

}
case $HDR in
    010202090202)
        echo "Found Soundmap"
        dump "$1"
        break
        ;;
    010202060201)
        echo "Found Effectmap 1"
        dump "$1" 34
        break
        ;;
    010202070201)
        echo "Found Effectmap 2"
        dump "$1" 34
        break
        ;;
    *)
        echo "Unknown format"
        hexdump -C "$1"
        ;;
esac
