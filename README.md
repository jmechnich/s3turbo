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

### Dumps

```
# Trigger RAM dump (not sure if bug)
./s3sysex.py --command STAT_REQUEST --exit
./s3sysex.py --command F_ACK --exit

# Dump Soundmap, Effect1, Effect2, General
./s3sysex.py --command DATA_REQUEST --checksum --exit 0x2 0x30 0x30 'str2file("*")'
./s3sysex.py --command DATA_REQUEST --checksum --exit 0x3 0x30 0x30 'str2file("*")'
./s3sysex.py --command DATA_REQUEST --checksum --exit 0x4 0x30 0x30 'str2file("*")'
./s3sysex.py --command DATA_REQUEST --checksum --exit 0x5 0x30 0x30 'str2file("*")'

# Dump Song 1 (Bank 0x30-0x39)
./s3sysex.py --command DATA_REQUEST --checksum --exit 0x6 0x30 0x30 'str2file("*")'

# Dump Performance (Bank 0x30-0x39 Perf 0x30-0x39)
./s3sysex.py --command DATA_REQUEST --checksum --exit 0x7 0x30 0x30 'str2file("*")'

# Other dump types
# 0x0 Sound dump     // not working or wrong filename
# 0x1 Sample dump    // not working or wrong filename

```

### Sample format
The S2/S3 exports 14-bit encoded mono samples. When receiving a sample dump, the program creates four files:
* sample_TIMESTAMP.sds: original stream of MIDI messages
* sample_TIMESTAMP.txt: sample information (loops, samplerate, etc)
* sample_TIMESTAMP.dmp: sample data dump (7-bit stream)
* sample_TIMESTAMP.raw: sample data dump (16-bit unsigned Big Endian)

The RAW file can be converted to PCM with `convert_sample.sh` or played back directly with:
```
# try samplerate*10
play  -b 16 -c 1 -e unsigned -B -t raw -r SAMPLERATE sample.raw
```

### Dependencies
* `python-pypm` Portmidi wrapper for Python
