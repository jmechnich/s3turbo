#!/usr/bin/env python

import argparse, sys, time

from MidiHandler import MidiHandler, isSysEx
from S3Turbo import MSCEIMessage, SysExParser

def main():
    parser = argparse.ArgumentParser(description='Send and receive midi messages')
    parser.add_argument('--indev', type=int, default=-1, action='store',
                        help='MIDI input device')
    parser.add_argument('--outdev', type=int, default=-1, action='store',
                        help='MIDI output device')
    parser.add_argument('--command', type=str, action='store',
                        help='send MIDI command')
    parser.add_argument('--debug', action='store_true',
                        help='enable debug output')

    args = parser.parse_args()

    try:
        filter = [
           [ 0xf8 ], # midi clock
        ]
        midi = MidiHandler(indev=args.indev, outdev=args.outdev,
                           msgfilter=filter, debug=args.debug)
        midi.start()
        parser = SysExParser(send_conn=midi.send_conn,debug=args.debug)
        if args.command:
            parser.sendSysEx(MSCEIMessage(fromName=args.command))
        else:
            #parser.sendSysEx(MSCEIMessage(0x4, 0x4, fromName="BANK_PERF_CHG"))
            #parser.sendSysEx(MSCEIMessage(0x0,0x0,0x0, 0x2a,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,fromName="DIR_REQUEST",appendChecksum=True))
            #parser.sendSysEx(MSCEIMessage(0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0, 0x0,fromName="DIR_DRQ",appendChecksum=True))
            pass
        while True:
            try:
                if midi.recv_conn.poll(1):
                    timestamp, msg = midi.recv_conn.recv()
                    if not len(msg):
                        continue
                    if isSysEx(msg):
                        parser.parse(msg, timestamp)
                    else:
                        #print timestamp, msg
                        pass
                else:
                    #print "No message received"
                    pass
            except EOFError:
                break
    except KeyboardInterrupt:
        pass
    print "Exiting normally..."
    
if __name__ == '__main__':
    main()
