import rtmidi, signal, os, time
from multiprocessing import Pipe

class RtMidiHandler(object):
    INPUT=0
    OUTPUT=1
    
    def __init__(self):
        super(RtMidiHandler,self).__init__()
        self.sysex = []
        self.midiin = rtmidi.MidiIn()
        self.midiin.ignore_types(sysex=False, timing=True, active_sense=True)
        self.midiout = rtmidi.MidiOut()
        
    def __del__(self):
        del self.midiin
        del self.midiout
        
    def initialize(self, indev=-1, outdev=-1, latency=10, msgfilter=[],
                   debug=False):
        self.indev     = indev
        self.outdev    = outdev
        self.latency   = latency
        self.msgfilter = msgfilter
        self.debug     = debug
        
        self.initInput()
        self.initOutput()

    def stop(self):
        pass
        
    def initInput(self):
        if self.indev < 0:
            self.print_dev(self.INPUT)
            self.indev = int(raw_input("Type input number: "))

        available_ports = self.midiin.get_ports()
        if available_ports:
            self.midiin.open_port(self.indev)
        else:
            self.midiin.open_virtual_port("s3turbo in")

        self.recv_conn, recv_conn = Pipe()
        self.midiin.set_callback(self.recv_handler, recv_conn)


    def initOutput(self):
        if self.outdev < 0:
            self.print_dev(self.OUTPUT)
            self.outdev = int(raw_input("Type output number: "))
        available_ports = self.midiout.get_ports()
        if available_ports:
            self.midiout.open_port(self.outdev)
        else:
            self.midiout.open_virtual_port("s3turbo out")

    def send(self, payload):
        timestamp, msg = payload
        if not msg or len(msg) < 2:
            print "Malformed message", timestamp, [ hex(b) for b in msg ]
            return

        # sysex
        if msg[0] == 0xF0 and msg[-1] == 0xF7:
            if self.debug:
                print "Sending  SysEx:", timestamp, [ hex(b) for b in msg ]
            self.midiout.send_message(msg)
        else:
            print "Trying to send non-sysex message"
    
    def poll(self, timeout):
        return self.recv_conn.poll(timeout)

    def recv(self):
        return self.recv_conn.recv()

    def recv_handler(self, payload, recv_conn):
        msg, timestamp = payload
        msg = [ m for m in msg if m != 0xf8 ]
        msgtype = msg[0]
        for f in self.msgfilter:
            for i in xrange(min(len(f),len(msg))):
                if f[i] != msg[i]:
                    break
            else:
                return
            
        if msgtype == 0xF0:
            self.sysex = msg
        elif len(self.sysex):
            self.sysex += msg
        else:
            recv_conn.send( (0, msg))

        if 0xF7 in self.sysex:
            self.sysex = \
                self.sysex[:self.sysex.index(0xF7)+1]
            if self.debug:
                print "Received SysEx:", [ hex(b) for b in self.sysex ]
            recv_conn.send( (0, self.sysex))
            self.sysex = []

    def print_dev(self,InOrOut):
        if InOrOut == RtMidiHandler.INPUT:
            midiobj = self.midiin
        else:
            midiobj = self.midiout

        for loop in range(midiobj.get_port_count()):
            print loop, midiobj.get_port_name(loop)
        print
