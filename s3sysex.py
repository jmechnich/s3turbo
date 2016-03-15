#!/usr/bin/env python

import argparse, os, sys, time

from s3sysex.MidiHandler import MidiHandler, isSysEx
from s3sysex.S3Turbo import MSCEIMessage, SysExParser
from s3sysex.SysEx import SampleDumpHandler

# for command-line evaluation
from s3sysex.Util import str2file, str2hex

def main():
    # command-line parsing
    parser = argparse.ArgumentParser(description='Send and receive midi messages')
    parser.add_argument('-i', '--indev', type=int, default=-1, action='store',
                        help='MIDI input device')
    parser.add_argument('-o', '--outdev', type=int, default=-1, action='store',
                        help='MIDI output device')
    parser.add_argument('-l', '--listdev', action='store_true',
                        help='list MIDI devices and exit')
    parser.add_argument('-c', '--command', type=str, action='store',
                        help='send MIDI command')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='enable debug output')
    parser.add_argument('-x', '--exit', action='store_true',
                        help='exit after executing command')
    parser.add_argument('--checksum', action='store_true',
                        help='force appending checksum to command')
    parser.add_argument('--samples', nargs="+",
                        help='list of SDS files for sample upload')
    parser.add_argument('args', nargs='*',
                        help='command arguments')

    # set defaults from configuration file
    confargs = {}
    conffile = os.path.join( os.environ["HOME"], ".s3sysex.conf")
    if os.path.exists(conffile):
        for line in open(conffile):
            k,v = line.strip().split(':')
            confargs[k] = v
    parser.set_defaults(**confargs)
    args = parser.parse_args()

    try:
        # list MIDI devices and exit
        if args.listdev:
            print "Inputs:"
            MidiHandler.print_dev(MidiHandler.INPUT)
            print "Outputs:"
            MidiHandler.print_dev(MidiHandler.OUTPUT)
            sys.exit(0)
            
        # MidiHandler, filter clock messages
        filter = [
           [ 0xf8 ], # midi clock
        ]
        midi = MidiHandler(indev=args.indev, outdev=args.outdev,
                           msgfilter=filter, debug=args.debug)
        midi.start()

        # SysExParser
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
            parser.sendSysEx(MSCEIMessage(*cmdargs, fromName=args.command,
                                          forceChecksum=args.checksum))

        # poll for incoming messages
        currentHandler = None
        while True:
            if midi.recv_conn.poll(1):
                timestamp, msg = midi.recv_conn.recv()
                if not len(msg):
                    continue
                if not isSysEx(msg):
                    continue
                if msg[1] == 0x7E:
                    # SampleDumpHeader, SampleDumpDataPacket, SampleDumpRequest
                    if msg[3] in [ 0x1, 0x2, 0x3 ]:
                        if not currentHandler:
                            currentHandler = SampleDumpHandler(
                                debug=args.debug,samplelist=args.samples)
                        midi.send_conn.send((0,currentHandler.parse(msg)))
                    # WAIT
                    elif msg[3] == 0x7C:
                        pass
                    # CANCEL
                    elif msg[3] == 0x7D:
                        if currentHandler:
                            del currentHandler
                            currentHandler = None
                    # ACK
                    elif msg[3] == 0x7F:
                        if currentHandler:
                            midi.send_conn.send((0,currentHandler.parse(msg)))
                else:
                    if not parser.parse(msg, timestamp): break
            elif args.exit:
                break
    except EOFError, e:
        print "EOFError", e
        sys.exit(1)
    except KeyboardInterrupt:
        print
    #except Exception, e:
    #    print e
    #    sys.exit(1)
    
if __name__ == '__main__':
    main()
