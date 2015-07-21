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
