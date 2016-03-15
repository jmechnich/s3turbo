import os, time

from s3sysex.Util import checksum, conv7_8, noop, cancel, hexdump, convertToLong
from s3sysex.S3TurboPrinter import MessagePrinter
from s3sysex.progress.bar import Bar

S3Functions = {
    # FILE FUNCTIONS  FILE_F
    "F_DHDR"                 : (0x0, 0x01, True),  # FILE DUMP HEADER
    "F_DPKT"                 : (0x0, 0x02, True),  # FILE DUMP DATA BLOCK
    "F_DREQ"                 : (0x0, 0x03, True),  # FILE DUMP REQUEST
    "DIR_HDR"                : (0x0, 0x00, True),  # FILE DIRECTORY HEADER
    "DIR_DRQ"                : (0x0, 0x04, True),  # FILE DIRECTORY REQUEST
    "F_ERR"                  : (0x0, 0x7B, False), # FILE ERROR
    # EDIT FUNCTIONS  EDIT_F
    "PAR_REQ"                : (0x2, 0x02, True),  # EDIT PARAMETER REQUEST
    "PAR_ASW"                : (0x2, 0x04, True),  # EDIT PARAMETER ANSWER
    "PAR_SND"                : (0x2, 0x03, True),  # EDIT PARAMETER SEND+REQUEST
    "EXECUTE"                : (0x2, 0x05, True),  # EDIT EXECUTE
    "_UPDATE"                : (0x2, 0x06, False), # EDIT UPDATE
    # DEVICE COMMAND  DEVICE_CMD
    "STAT_REQUEST"           : (0x5, 0x00, False), # STATUS REQUEST
    "STAT_ANSWER"            : (0x5, 0x01, True),  # STATUS ANSWER
    "BANK_PERF_CHG"          : (0x5, 0x02, False), # BANK PERFORMANCE CHANGE
    "PREPARE_soundAccess"    : (0x5, 0x03, False), # PREPARE SOUND ACCESS
    "UNPREPARE_soundAccess"  : (0x5, 0x04, False), # UNPREPARE SOUND ACCESS
    "PREPARE_bankAccess"     : (0x5, 0x05, False), # PREPARE BANK ACCESS
    "UNPREPARE_bankAccess"   : (0x5, 0x06, False), # UNPREPARE BANK ACCESS
    "PREPARE_effectAccess"   : (0x5, 0x07, False), # PREPARE EFFECT ACCESS
    "UNPREPARE_effectAccess" : (0x5, 0x08, False), # UNPREPARE EFFECT ACCESS
    "PREPARE_generalAccess"  : (0x5, 0x09, False), # PREPARE GENERAL ACCESS
    "UNPREPARE_generalAccess": (0x5, 0x0A, False), # UNPREPARE GENERAL ACCESS
    "PREPARE_StyleAccess"    : (0x5, 0x18, False), # PREPARE STYLE ACCESS
    "UNPREPARE_StyleAccess"  : (0x5, 0x19, False), # UNPREPARE STYLE ACCESS
    "DATA_HEADER"            : (0x5, 0x0C, True),  # DATA DUMP HEADER
    "DATA_DUMP"              : (0x5, 0x0D, True),  # DATA DUMP
    "DELETE"                 : (0x5, 0x0E, True),  # DELETE
    "DIR_REQUEST"            : (0x5, 0x0F, True),  # DIRECTORY REQUEST
    "DIR_ANSWER"             : (0x5, 0x10, True),  # DIRECTORY ANSWER
    "DATA_REQUEST"           : (0x5, 0x0B, True),  # DATA_REQUEST
    "MESSAGECAPTUREON"       : (0x5, 0x11, False), # MESSAGE CAPTURE ON
    "MESSAGECAPTUREOFF"      : (0x5, 0x12, False), # MESSAGE CAPTURE OFF
    "MESSAGESEND"            : (0x5, 0x13, True),  # MESSAGE SEND
    "MESSAGEANSWER"          : (0x5, 0x14, False), # MESSAGE ANSWER
    "ENABLEEDITUPDATE"       : (0x5, 0x15, False), # ENABLE EDIT UPDATE
    "DISABLEEDITUPDATE"      : (0x5, 0x16, False), # DISABLE EDIT UPDATE
    "D_ERR"                  : (0x5, 0x7B, False), # DEVICE ERROR
    "PUT_KEY"                : (0x5, 0x17, False), # WRITE KEY
    # EXTRA
    "F_WAIT"                 : (0x0, 0x7C, False), # WAIT
    "F_CANCEL"               : (0x0, 0x7D, False), # CANCEL
    "F_NACK"                 : (0x0, 0x7E, False), # NACK
    "F_ACK"                  : (0x0, 0x7F, False), # ACK
    "D_WAIT"                 : (0x5, 0x7C, False), # DEVICE WAIT
    "D_CANCEL"               : (0x5, 0x7D, False), # DEVICE CANCEL
    "D_NACK"                 : (0x5, 0x7E, False), # DEVICE NACK
    "D_ACK"                  : (0x5, 0x7F, False), # DEVICE ACK
    }

# Tries to match message to S3 function
def S3FunctionName(msg):
    func    = (msg[2] >> 4)
    subfunc = msg[3]
    for k,v in S3Functions.iteritems():
        if v[:2] == (func,subfunc):
            return k
    return None

# not used but defined in manual
class S3HandshakeMessage(object):
    @staticmethod
    def WAIT(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7c)

    @staticmethod
    def CANCEL(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7d)

    @staticmethod
    def NACK(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7e)

    @staticmethod
    def ACK(function,chan=0,ownchan=0):
        return S3HandshakeMessage.Generate(function,chan,ownchan,0x7f)

    @staticmethod
    def Generate(function,chan,ownchan,command):
        fun, subfun = S3Functions[function]
        return [ 0xF0, 0x2F, fun << 4 | chan, subfun, command, ownchan, 0xF7 ]

# S3 message skeleton
class MSCEIMessage(object):
    def __init__(self, *args, **kwargs):
        super(MSCEIMessage,self).__init__()
        data = []
        if len(args):
            data += args

        func = 0
        subfunc = 0
        self.name = kwargs.get("fromName", None)
        if self.name:
            func, subfunc, appendChecksum = S3Functions.get(self.name, (None, None))
            if func is None: raise Exception("Unknown Command")
        
        self.magic    = kwargs.get("magic", 0xF0)
        self.vendor   = kwargs.get("vendor", 0x2F)
        self.func     = kwargs.get("func", func)
        self.subfunc  = kwargs.get("subfunc", subfunc)
        self.chan     = kwargs.get("chan", 0x0)
        self.reqchan  = kwargs.get("reqchan", 0x0)
        self.data     = kwargs.get("data", data)
        self.term     = kwargs.get("term", 0xF7)
        self.appendChecksum = True if kwargs.get("forceChecksum", False) else appendChecksum
        
    def msg(self, time=0):
        return (time, self.raw())

    def raw(self):
        ret = []
        ret.append(self.magic)
        ret.append(self.vendor)
        ret.append((self.func << 4) | self.chan)
        ret.append(self.subfunc)
        ret.append(self.reqchan)
        if len(self.data):
            ret += self.data
            if self.appendChecksum:
                checksum = 0
                for b in ret[1:]: checksum ^= b
                ret.append(checksum)
        ret.append(self.term)
        return ret

# main parser class
class SysExParser(object):
    def __init__(self,send_conn,debug=False):
        super(SysExParser,self).__init__()
        self.send_conn = send_conn
        self.debug     = debug
        self.dump_file = None
        self.dump_on = False

        self.handlers = {
            # FILE FUNCTIONS  FILE_F
            "F_DHDR":      self.handleFileDumpHeader,
            "F_DPKT":      self.handleFileDumpDataBlock,
            "DIR_HDR":     self.handleFileDumpHeader,
            "F_WAIT"     : noop,
            "F_CANCEL"   : cancel,
            "F_ERR"      : cancel,
            # DEVICE COMMAND  DEVICE_CMD
            "STAT_ANSWER": self.handleStatusAnswer,
            "DATA_HEADER": self.handleDirectoryAnswer,
            "DATA_DUMP"  : self.handleDataDump,
            "DIR_ANSWER" : self.handleDirectoryAnswer,
            "D_WAIT"     : noop,
            "D_ACK"      : noop,
            "D_CANCEL"   : cancel,
            "D_ERR"      : cancel,
        }

        self.dump_start = [ "F_DREQ", "DATA_REQUEST" ]
        self.dump_stop  = [ "F_CANCEL", "D_CANCEL"]

    def __del__(self):
        self.closeDumpFile()

    def createDumpFile(self,filename=None):
        if not filename:
            timestamp = time.strftime("%Y%m%d%H%M%S")
            filename="dump_%s.bin" % timestamp
        self.dump_file = open(filename,"wb")
        print "Dump started"
        
    def closeDumpFile(self):
        if not self.dump_file: return
        self.dump_file.close()
        self.dump_file = None
        print "Dump finished"

    def startDump(self,filename,size):
        if not self.dump_on: return
        self.dump_written = 0
        self.dump_size = size
        self.closeDumpFile()
        self.createDumpFile(filename)
        print
        self.bar = Bar(filename,max=size,suffix = '%(percent).1f%% - %(eta)ds')

    def stopDump(self):
        if not self.dump_on: return
        self.bar.finish()
        self.closeDumpFile()
        self.dump_on = False
        
    def dump(self,data,filename=None):
        if not self.dump_on: return
        if not self.dump_file:
            self.createDumpFile()
        if self.dump_written == self.dump_size:
            print "Discarding", len(data), "bytes, dump has ended"
        elif len(data) + self.dump_written > self.dump_size:
            discard = len(data) + self.dump_written - self.dump_size
            self.dump_file.write(bytearray(data[:-discard]))
            self.bar.next(self.dump_size-self.dump_written)
            self.dump_written = self.dump_size
            self.bar.finish()
            leftover = data[-discard:]
            for i in leftover:
                if i != 0:
                    print "Discarding non-NUL data:", hexdump(leftover)
                    break
        else:
            self.dump_file.write(bytearray(data))
            self.dump_written += len(data)
            self.bar.next(len(data))
        
    # FILE FUNCTIONS  FILE_F
    def handleFileDumpHeader(self,msg,timestamp):
        self.sendSysEx( MSCEIMessage(fromName="F_WAIT"),timestamp=timestamp+1)
        offset=17
        data = []
        for i in xrange(2):
            data += conv7_8(msg[offset:offset+8])
            offset += 8
        location = ''
        while msg[offset] != 0:
            location += chr(msg[offset])
            offset += 1
        offset+=1
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            filename = str(bytearray(msg[5:16]))
            length = convertToLong(data[4:8])
            self.startDump(filename,length)
            self.dump(data[8:])
            self.sendSysEx( MSCEIMessage(fromName="F_ACK"),
                            timestamp=timestamp+2)
        else:
            self.sendSysEx( MSCEIMessage(fromName="F_NACK"),
                            timestamp=timestamp+2)
        return True
        
    def handleFileDumpDataBlock(self,msg,timestamp):
        self.sendSysEx( MSCEIMessage(fromName="F_WAIT"),timestamp=timestamp+1)
        noctets = msg[5]
        offset=6
        data = []
        for i in xrange(noctets):
            data += conv7_8(msg[offset:offset+8])
            offset += 8
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            self.dump(data)
            self.sendSysEx( MSCEIMessage(fromName="F_ACK"),
                            timestamp=timestamp+2)
        else:
            self.sendSysEx( MSCEIMessage(fromName="F_NACK"),
                            timestamp=timestamp+2)
        return True

    # DEVICE COMMAND  DEVICE_CMD
    def handleStatusAnswer(self,msg,timestamp):
        self.sendSysEx( MSCEIMessage(fromName="D_WAIT"),timestamp=timestamp+1)
        offset= 5 + 3*8
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            self.sendSysEx( MSCEIMessage(fromName="D_ACK"),
                            timestamp=timestamp+2)
        else:
            self.sendSysEx( MSCEIMessage(fromName="D_NACK"),
                            timestamp=timestamp+2)
        return True

    def handleDataDump(self,msg,timestamp):
        self.sendSysEx( MSCEIMessage(fromName="D_WAIT"))
        noctets = msg[5]
        offset=6
        data = []
        for i in xrange(noctets):
            data += conv7_8(msg[offset:offset+8])
            offset += 8
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            self.dump(data)
            self.sendSysEx( MSCEIMessage(fromName="D_ACK"),
                            timestamp=timestamp+2)
        else:
            self.sendSysEx( MSCEIMessage(fromName="D_NACK"),
                            timestamp=timestamp+2)
        return True

    def handleDirectoryAnswer(self,msg,timestamp):
        #time.sleep(0.1)
        self.sendSysEx( MSCEIMessage(fromName="D_WAIT"),timestamp=timestamp+1)
        offset = 8 + 11 + 1
        data = []
        for i in xrange(2):
            data += conv7_8(msg[offset:offset+8])
            offset += 8
        offset += 11
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            filename = str(bytearray(msg[8:19]))
            length = convertToLong(data[4:8])
            self.startDump(filename,length)
            #time.sleep(0.1)
            self.sendSysEx( MSCEIMessage(fromName="D_ACK"),
                            timestamp=timestamp+2)
        else:
            self.sendSysEx( MSCEIMessage(fromName="D_NACK"),
                            timestamp=timestamp+2)
        return True
        
    def parse(self, msg, timestamp, acceptUnhandled=True):
        if msg[0] != 0xF0:
            print 'Non-sysex message'
            print [ hex(b) for b in msg ]
            print
            return acceptUnhandled

        fname = S3FunctionName(msg)
        if not fname:
            print "Unhandled message"
            return acceptUnhandled
        
        if self.debug: print "Received", fname, "@", timestamp
        printer = MessagePrinter.get(fname,None)
        if printer: printer(msg)
        if fname in self.dump_stop: self.stopDump()
        handler = self.handlers.get(fname, None)
        if handler: return handler(msg,timestamp=timestamp)
        else:       print fname, [ hex(b) for b in msg ]

    def sendSysEx(self,msg,timestamp=0):
        fname = S3FunctionName(msg.raw())
        if fname:
            if self.debug: print "Sending ", fname, "@", timestamp
            p = MessagePrinter.get(fname,None)
            if p: p(msg)
            if fname in self.dump_start: self.dump_on = True
        self.send_conn.send( (timestamp,msg.raw()))
