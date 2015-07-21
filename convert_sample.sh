#!/bin/sh

while [ x"$1" != x ]; do
    INFILE="$1"
    shift
    if [ ! -e "$INFILE" ]; then
        echo "$INFILE does not exist"
    fi
    
    FNAME=`echo "$INFILE" | rev | cut -d. -f2- | rev`
    if [ ! -e "$FNAME".txt ]; then
        echo "$FNAME.txt does not exist, can't determine sample rate"
        exit 1
    fi
    SAMPLERATE=`grep sample_rate "$FNAME".txt | cut -d' ' -f2`

    echo "Converting $INFILE, sample rate $SAMPLERATE"
    sox -b 16 -c 1 -e unsigned -B -t raw -r $SAMPLERATE "$INFILE" "$FNAME".wav
done
