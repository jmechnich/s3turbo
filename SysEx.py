import time, os

from Util import checksum

class HandshakeMessage(object):
    @staticmethod
    def EOF(target=0x0, packetnumber=0x0):
        return HandshakeMessage.Generate(
            subid=0x7B,target=target,packetnumber=packetnumber)
                 
    @staticmethod
    def Wait(target=0x0, packetnumber=0x0):
        return HandshakeMessage.Generate(
            subid=0x7C,target=target,packetnumber=packetnumber)
                 
    @staticmethod
    def Cancel(target=0x0, packetnumber=0x0):
        return HandshakeMessage.Generate(
            subid=0x7D,target=target,packetnumber=packetnumber)
                 
    @staticmethod
    def NAK(target=0x0, packetnumber=0x0):
        return HandshakeMessage.Generate(
            subid=0x7E,target=target,packetnumber=packetnumber)
                 
    @staticmethod
    def ACK(target=0x0, packetnumber=0x0):
        return HandshakeMessage.Generate(
            subid=0x7F,target=target,packetnumber=packetnumber)

    @staticmethod
    def Generate(subid, target, packetnumber):
        return [ 0xF0, 0x7E, target, subid, packetnumber, 0xF7 ]

class SampleDumpHandler(object):
    def __init__(self,debug=False,samplelist=None):
        super(SampleDumpHandler,self).__init__()
        self.debug=debug
        self.samplelist = samplelist
        self.reset()
        
    def __del__(self):
        if len(self.data):
            self.saveFile()

    def reset(self):
        self.header  = {}
        self.data = []
        self.lastpacket = 0
        self.raw = []
        self.packetcounter = 0
        self.dump_start = 0
        self.exppacket = 0
        self.starttime = 0
        
    def parse(self,msg):
        status = None
        if msg[3] == 0x1:
            status = self.parseHeader(msg)
        elif msg[3] == 0x2:
            status = self.parsePacket(msg)
        elif msg[3] == 0x3:
            status = self.parseRequest(msg)
        elif msg[3] == 0x7F and self.dump_start > 0:
            status = self.continueDump()
        return status
    
    def parseHeader(self, msg):
        self.reset()
        if len(msg) != 21:
            print "Size mismatch, is", len(msg)
            return HandshakeMessage.NAK(packetnumber=self.lastpacket)

        speriod = int(msg[9]  << 14 | msg[8]  << 7 | msg[7])
        srate   = 1./(speriod *1e-9)
        self.header = {
            "target_id"        : msg[2],
            "sample_number"    : msg[5] << 7 | msg[4],
            "sample_format"    : msg[6],
            "sample_period"    : speriod,
            "sample_rate"      : "%d Hz" % srate,
            "sample_length"    : msg[12] << 14 | msg[11] << 7 | msg[10],
            "sample_loop_start": msg[15] << 14 | msg[14] << 7 | msg[13],
            "sample_loop_end"  : msg[18] << 14 | msg[17] << 7 | msg[16],
            "loop_type"        : msg[19],
            }

        if self.debug:
            print "Sample Dump Header"
            print "  Data:"
            for k,v in self.header.iteritems():
                print "    %s:" % k, v

        self.raw += msg
        format = int(self.header["sample_format"])
        length = int(self.header["sample_length"])
        self.exppacket = (format+6)/7*length/120+1
        print "Receiving sample, expecting", self.exppacket, "packets"
        self.starttime = time.time()
        return HandshakeMessage.ACK(packetnumber=self.lastpacket)
    
    def parsePacket(self, msg):
        if not 0xF7 in msg:
            print "printSampleDumpDataPacket: could not find EOX"
            return HandshakeMessage.NAK(packetnumber=self.lastpacket)
        
        cs = msg.index(0xF7)-1
        calced_cs = checksum(msg[1:cs])
        if self.debug:
            print "Sample Dump Data Packet"
            print "  Data:"
            print "    Packet count", msg[4]
            print "  checksum:", hex(msg[cs]), \
                "(calculated 0x%x)" % calced_cs
        if msg[cs] != calced_cs:
            print "Checksum mismatch:", hex(msg[cs]), "should be", hex(calced_cs)
            return HandshakeMessage.NAK(packetnumber=self.lastpacket)
        offset = 5
        format = int(self.header['sample_format'])

        if format == 14:
            self.data += msg[offset:offset+120]
        else:
            print format, "bit samples are not supported"
        self.lastpacket = msg[4]
        self.raw += msg
        self.packetcounter += 1
        if self.packetcounter % 100 == 0:
            elapsed = (time.time()-self.starttime)
            rate = self.packetcounter/elapsed
            print "Received %d packets in %.1f seconds (%.1f pkts/sec)" % (
                self.packetcounter, elapsed, rate
                )
        return HandshakeMessage.ACK(packetnumber=self.lastpacket)

    def parseRequest(self,msg):
        self.reset()
        if not 0xF7 in msg:
            print "printSampleDumpDataPacket: could not find EOX"
            return HandshakeMessage.NAK(packetnumber=self.lastpacket)

        samplenumber = int(msg[5] << 7 | msg[4])

        print "Received Sample Dump Request for sample", samplenumber
        if self.debug:
            print "  Data:"
            print "        targetid:",  msg[2]
            print "    samplenumber:", samplenumber

        samplefile = None
        if self.samplelist and samplenumber < len(self.samplelist):
            samplefile = self.samplelist[samplenumber]
            print "Selected list index", samplenumber, repr(samplefile)
        if not samplefile or not os.path.exists(samplefile):
            samplefile = "sample.sds"
            print "Selected fallback", repr(samplefile)
        if not os.path.exists(samplefile):
            print "No sample to send"
            return HandshakeMessage.Cancel(packetnumber=self.lastpacket)
            
        f = open(samplefile, "rb")
        self.raw = [ ord(i) for i in f.read() ]
        f.close()
        n = self.raw.count(0xF7)
        if n > 0:
            print "Sending", n, "Sample Dump Packets (+ header)"
            self.starttime = time.time()
            self.dump_start = self.raw.index(0xF7)+1
            self.packetcounter += 1
            return self.raw[:self.dump_start]
        
        return HandshakeMessage.Cancel(packetnumber=self.lastpacket)

    def continueDump(self):
        n = self.raw[self.dump_start:].count(0xF7)
        if n == 0:
            elapsed = time.time()-self.starttime
            print "Sent %d packets in %.1f seconds (%.1f bytes/sec)" % (
                self.packetcounter, elapsed, len(self.raw)/elapsed)
            self.reset()
            return HandshakeMessage.EOF(packetnumber=self.lastpacket)
        
        ds = self.dump_start
        self.dump_start = self.raw.index(0xF7,self.dump_start)+1
        if self.packetcounter % 100 == 0:
            print "Sent %d packets" % self.packetcounter
        self.packetcounter += 1
        return self.raw[ds:self.dump_start]
        
    def saveFile(self, filename=None):
        if not filename:
            timestamp = time.strftime("%Y%m%d%H%M%S")
            filename = "sample_%s" % timestamp

        rate = self.packetcounter*120/(time.time()-self.starttime)
        print "Packets received:", self.packetcounter
        print "Packets expected:", self.exppacket
        print "Average rate:     %.1f bytes/sec" % rate
        print
        print "Saving to", filename

        # concatenation of sysex messages
        f = open(filename+".sds", "wb")
        f.write(bytearray(self.raw))
        f.close()

        # sample data only (7-bit encoded)
        f = open(filename+".dmp", "wb")
        f.write(bytearray(self.data))
        f.close()

        # decoded sample data
        format = int(self.header['sample_format'])
        f = open(filename+".raw", "wb")
        if format == 14:
            out  = []
            pos  = 0
            # stretch to 16-bit
            norm = 2
            while pos < len(self.data):
                # assume MSB first
                tmp = self.data[pos] << (7+norm) | self.data[pos+1] << norm
                # hard 16-bit conversion, store MSB first
                out.append(tmp >> 8)
                out.append(tmp & 0xFF)
                pos += 2
            f.write(bytearray(out))
        else:
            print format, "bit samples are not supported"
            print>>f, format, "bit samples are not supported"
        f.close()

        # sample properties
        f = open(filename+".txt", "w")
        f.writelines( [ "%s: %s\n" % i for i in self.header.iteritems() ] )
        f.close()
        self.reset()
