#!/usr/bin/env python

import argparse, sys, time

from MidiHandler import MidiHandler, isSysEx
from S3Turbo import MSCEIMessage, SysExParser

# for command-line evaluation
from Util import str2file, str2hex

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
    parser.add_argument('--exit', action='store_true',
                        help='exit after executing command')
    parser.add_argument('--checksum', action='store_true',
                        help='append checksum to command')
    parser.add_argument('args', nargs='*',
                        help='command arguments')
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
            cmdargs = []
            if len(args.args):
                for a in args.args:
                    a = eval(a)
                    if type(a) == type(list()):
                        cmdargs += a
                    else:
                        cmdargs.append(a)
            parser.sendSysEx(MSCEIMessage(*cmdargs, fromName=args.command, appendChecksum=args.checksum))
        while True:
            if midi.recv_conn.poll(1):
                timestamp, msg = midi.recv_conn.recv()
                if not len(msg):
                    continue
                if isSysEx(msg):
                    parser.parse(msg, timestamp)
            elif args.exit:
                break
    except EOFError, e:
        print "EOFError", e
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except Exception, e:
        print e
    
    print "Exiting normally..."
    
if __name__ == '__main__':
    main()
