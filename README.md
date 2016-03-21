# s3turbo
Tools for the General Music S2/S3 Turbo synthesizer, including
* `s3midi`, a MIDI System Exclusive interface program
* `s3img`, a program for handling floppy disk images
* `s3floppy`, a program for formatting, reading and writing S2/S3 floppy disks

## About s3midi
The General Music/GEM S2/S3 Turbo Music Processor is a synthesizer workstation from the early 90s.  The Turbo version (larger ROM and updated functionality) has support for MIDI System Exclusive which is not well-documented.  The manual includes only a rudimentary description of the available commands and data structures but the C development files are not available.

This tool provides an implementation of most of the commands from the manual.  It is also possible to send and receive sample dumps using SDS to the synthesizer (not tested with other instruments).

## Functionality of s3midi
* Send commands to the synthesizer, see [s3turbo/S3Turbo.py](https://github.com/jmechnich/s3turbo/blob/master/s3turbo/S3Turbo.py)
* Monitor MIDI messages and decode S2/S3 specific data
* Send and receive sample dumps

## Usage of s3midi

The MIDI device numbers can be given on the command line using `--indev` and `--outdev`. `--listdev` lists all available MIDI devices. Defaults for command line arguments can be set using a configuration file `~/.s3turbo.conf`, e.g. containing:
```
indev:  2
outdev: 3
```
Sending a basic status request to the synthesizer. The `--exit` flag causes the program to terminate after one second of inactivity from the synthesizer.
```
./s3midi --command STAT_REQUEST
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
```

Change to Bank 1, Performance 1 and print debugging information. Additional command line arguments are appended to the message body.
```
# Bank and Performance values in ASCII (0x30-0x39)
./s3midi --verbose --command BANK_PERF_CHG -x 0x30 0x30 --exit
```

Send a directory request to the synthesizer. The order of commandline arguments has to match the signature of the command.
```
# List everything
./s3midi --command DIR_DRQ -f"*" -p"A:"
```

The first argument is the filename, second is the path.
A: corresponds to RAM.
B: corresponds to the current disk if loaded, to the RAM disk otherwise.
C: is either empty if no disk is loaded or corresponds to the RAM disk.

The general directory layout is
```
A:-|
   |-BANKS                 (type 32, format 32)
   | |-'BANKNAME  0'       (type 32, format 32)
   | |-'BANKNAME  1'       (type 32, format 32)
   | :
   | |-'BANKNAME  9'       (type 32, format 32)
   |   |-PERF              (type 32, format 32)
   |   | |-'PERFNAME  0'   (type  2, format  2)
   |   | |-'PERFNAME  1'   (type  2, format  2)
   |   | :
   |   | |-'PERFNAME  9'   (type  2, format  2)
   |   |
   |   |-Song              (type  3, format  2)
   |
   |-DATA                  (type 32, format 32)
   | :_(e.g. screenshot from hardcopy program in HARDCPY/FIG_001 IMG)
   | :_(e.g. text file from disk directory program in DISKNAMEALL/LIB/DIR etc.)
   |
   |-PROGRAM               (type 32, format 32)
   | :_(e.g. temporary files from disk copy program)
   |
   |-SETUP                 (type 32, format 32)
     |-GENERAL             (type  5, format  2)
     |-EFFECT1             (type  6, format  2)
     |-EFFECT2             (type  7, format  2)
     |-SOUNDMAP            (type  9, format  2)
     |-SAMPLES             (type 32, format 32)
     | |-'SAMPNAMETXL'     (type  8, format  2)
     |
     |-SOUNDS              (type 32, format 32)
       |-'SOUNDNAME F'     (type  1, format  2)
       |-'SOUNDNAME E'     (type  1, format  2)

Sound suffixes:
  E - RAM sound using RAM sample
  F - RAM sound using ROM sample

File types:
  1 - Sound
  2 - Performance
  3 - Song
  4 - ?
  5 - General Setup
  6 - Effect1 Setup
  7 - Effect2 Setup
  8 - Sample
  9 - Soundmap Setup
 32 - Directory
```

### Dumps
```
TYPE = [ 0x0, # Sound
         0x1, # Sample
         0x2, # Soundmap
         0x3, # Effect1
         0x4, # Effect2
         0x5, # General
         0x6, # Song
         0x7, # Performance
         0x8, # Global       (untested)
         0x9, # StylePerf    (untested)
         0xa, # RealtimePerf (untested)
         0xb, # Riff         (untested)
]

BANK = ASCII Bank number (0x30-0x39), only used for TYPE 0x6, 0x7
PERF = ASCII Performance number (0x30-0x39), only used for TYPE 0x7

# List directory contents
./s3midi --command DIR_REQUEST -x $TYPE $BANK $PERF -f"*"

# Dump 'file'
./s3midi --command DATA_REQUEST -x $TYPE $BANK $PERF -f"*")'

# Dump Sound ("SOUND     E" from DIR_REQUEST)
# F_DREQ does not seem to work at all
./s3midi --command DATA_REQUEST -x 0 0 0 -f"SOUND     E"

# Dump Sample ("SAMPLE  TXL" from DIR_REQUEST)
# F_DREQ only dumps a few bytes if dumping from RAM but seems to work for RAM disk (e.g. C:)
./s3midi --command DATA_REQUEST -x 1 0 0 -f"SAMPLE  TXL"
or
./s3midi --command F_DREQ -f"SAMPLE  TXL" -p"A:\\SETUP\\SAMPLES\\"

# Dump SOUNDMAP (filename argument ignored)
./s3midi --command DATA_REQUEST -x 2 0 0 -f"*"
or
./s3midi --command F_DREQ -f"SOUNDMAP" -p"A:\\SETUP\\"

# Dump EFFECT1 (filename argument ignored)
./s3midi --command DATA_REQUEST -x 3 0 0 -f"*"
or
./s3midi --command F_DREQ -f"EFFECT1" -p"A:\\SETUP\\"

# Dump EFFECT2 (filename argument ignored)
./s3midi --command DATA_REQUEST -x 4 0 0 -f"*"
or
./s3midi --command F_DREQ -f"EFFECT2" -p"A:\\SETUP\\"

# Dump GENERAL (filename argument ignored)
./s3midi --command DATA_REQUEST -x 5 0 0 -f"*"
or
./s3midi --command F_DREQ -f"GENERAL" -p"A:\\SETUP\\"

# Dump Song 1 (Bank 0x30-0x39)
./s3midi --command DATA_REQUEST -x 6 0x30 0x30 -f"*"
or e.g.
./s3midi --command F_DREQ -f"Song" -p"A:\\BANKS\\Bank 1    0\\"

# Dump Performance (Bank 0x30-0x39 Perf 0x30-0x39)
./s3midi --command DATA_REQUEST -x 7 0x30 0x30 '-f"*"
or e.g.
./s3midi --command F_DREQ -f"Perf      0" -p"A:\\BANKS\\Bank 1    0\\PERF\\"

# Dump hardcopy created with 'HARDCPY PRG'
./s3midi --command F_DREQ -f"FIG_001 IMG" -p"A:\\DATA\\HARDCPY\\"
```

### File formats

```
# Sound map format, variable length
 6 bytes header     01 02 02 09 02 02
18 bytes map entry
   bytes  1-10      Sound Name
   byte  11         unknown, c0 - ROM layer, c5 - RAM sound, c6 - RAM sample sound, else c2 or 00
   byte  12         unknown (00)
   byte  13         Bank
   byte  14         Program
   bytes 15-16      Date (1b 23 for factory presets)
   bytes 17-18      Time (70 00 for factory presets)

# Effect1 map format, variable length
 6 bytes header     01 02 02 06 02 01
34 bytes map entry
   bytes  1-10      Effect name
   bytes 11-12      unknown (00 00)
   byte  13         Effect number
   byte  14         unknown (7f)
   bytes 15-16      Date (18 c8 for factory presets)
   bytes 17-18      Time (70 00 for factory presets)
   bytes 19-21      unknown (00 00 00)
   byte  22         Effect type
   bytes 23-24      Level
   bytes 25-26      Effect param 1
   bytes 27-28      Effect param 2
   bytes 29-30      Effect param 3
   bytes 31-32      Effect param 4
   byte  33-34      Effect param 5

# Effect2 map format, variable length
 6 bytes header     01 02 02 07 02 01
34 bytes map entry, see Effect 1 map

# General format, possibly constant length 1127
 6 bytes header     01 02 02 05 02 01
 remaining unknown

# Performance format, possibly constant length 252
 6 bytes header     01 02 02 03 02 01
 remaining unknown
 
# Clipboard format, variable length
 6 bytes header     01 02 02 0a 02 01
```

### Sample format
The S2/S3 exports 14-bit encoded mono samples. When receiving a sample dump, the program creates the following files:
* sample_TIMESTAMP.sds: original stream of MIDI messages
* sample_TIMESTAMP.txt: sample information (loops, samplerate, etc)
* sample_TIMESTAMP.dmp: sample data dump (7-in-8-bit chunks, big-endian: .dcba987 .6543210)
* sample_TIMESTAMP.wav: PCM sample data (s16le mono)

## Dependencies
* `python-pypm` Portmidi wrapper for Python
* `python-progress` Progress bar for Python
