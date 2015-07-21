# s3sysex
MIDI System Exclusive interface for the General Music S3 Turbo synthesizer

### About
The General Music/GEM S2/S3 Turbo Music Processor is a synthesizer workstation from the early 90s.  The Turbo version (larger ROM and updated functionality) has support for MIDI System Exclusive which is not well-documented.  The manual includes only a rudimentary description of the available commands and data structures but the C development files are not available.

This tool provides an implementation of most of the commands from the manual.  It is also possible to send and receive sample dumps using SDS to the synthesizer (not tested with other instruments).

### Functionality
* Send commands to the synthesizer (see `S3Turbo.py`)
* Monitor MIDI messages and decode S2/S3 specific data
* Send and receive sample dumps
* Convert samples to PCM (`convert_sample.sh`)

### Usage

Sending a basic status request to the synthesizer. The `--exit` flag causes the program to terminate after one second of inactivity from the synthesizer.
```
./s3sysex.py --command STAT_REQUEST --exit
1 Midi Through Port-0   (input)  (unopened)
3 FastTrack Pro MIDI 1   (input)  (unopened)

Type input number: 3
0 Midi Through Port-0   (output)  (unopened)
2 FastTrack Pro MIDI 1   (output)  (unopened)

Type output number: 2
Sending STAT_REQUEST @ 0
Received STAT_ANSWER @ 51
  Data:
    ActBankPerf: (2, 1)
    FreeMem: 678632
    FreeSampleMem: 1649774
    ReadyFor: (255, 255)
    TotalMem: 1650688
    iClass: 1
    iRelease: 2
    iSubClass: 2
  checksum: 0x57 (calculated 0x57)
Sending D_WAIT @ 0
Sending D_ACK @ 0
```

The MIDI device numbers can be given on the command line using `--indev` and `--outdev`. Defaults for command line arguments can be set using a configuration file `~/.s3sysex.conf`, e.g. containing:
```
indev:  2
outdev: 3
```

Change to Bank 1, Performance 1 and print debugging information. Additional command line arguments are appended to the message body.
```
# Bank and Performance values in ASCII (0x30-0x39)
./s3sysex.py --debug --command BANK_PERF_CHG --exit 0x30 0x30
```

Send a directory request to the synthesizer. Uses the custom python functions `str2file` and `str2hex` to convert a string to lists of integers. `str2file` creates fixed 11 character filename padded with whitespace.  `str2hex` creates a 0-terminated list.

```
./s3sysex.py --command DIR_DRQ --checksum --exit 'str2file("*")' 'str2hex("A:\\")'
```

### Dependencies
* `python-pypm` Portmidi wrapper for Python
