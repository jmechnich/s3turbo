import os, time

from Util import checksum, conv7_8, noop
from S3TurboPrinter import MessagePrinter

S3Functions = {
    # FILE FUNCTIONS  FILE_F
    "F_DHDR"                 : (0x0, 0x01), # FILE DUMP HEADER
    "F_DPKT"                 : (0x0, 0x02), # FILE DUMP DATA BLOCK
    "F_DREQ"                 : (0x0, 0x03), # FILE DUMP REQUEST
    "DIR_HDR"                : (0x0, 0x00), # FILE DIRECTORY HEADER
    "DIR_DRQ"                : (0x0, 0x04), # FILE DIRECTORY REQUEST
    "F_ERR"                  : (0x0, 0x7B), # FILE ERROR
    # EDIT FUNCTIONS  EDIT_F
    "PAR_REQ"                : (0x2, 0x02), # EDIT PARAMETER REQUEST
    "PAR_ASW"                : (0x2, 0x04), # EDIT PARAMETER ANSWER
    "PAR_SND"                : (0x2, 0x03), # EDIT PARAMETER SEND+REQUEST
    "EXECUTE"                : (0x2, 0x05), # EDIT EXECUTE
    "_UPDATE"                : (0x2, 0x06), # EDIT UPDATE
    # DEVICE COMMAND  DEVICE_CMD
    "STAT_REQUEST"           : (0x5, 0x00), # STATUS REQUEST
    "STAT_ANSWER"            : (0x5, 0x01), # STATUS ANSWER
    "BANK_PERF_CHG"          : (0x5, 0x02), # BANK PERFORMANCE CHANGE
    "PREPARE_soundAccess"    : (0x5, 0x03), # PREPARE SOUND ACCESS
    "UNPREPARE_soundAccess"  : (0x5, 0x04), # UNPREPARE SOUND ACCESS
    "PREPARE_bankAccess"     : (0x5, 0x05), # PREPARE BANK ACCESS
    "UNPREPARE_bankAccess"   : (0x5, 0x06), # UNPREPARE BANK ACCESS
    "PREPARE_effectAccess"   : (0x5, 0x07), # PREPARE EFFECT ACCESS
    "UNPREPARE_effectAccess" : (0x5, 0x08), # UNPREPARE EFFECT ACCESS
    "PREPARE_generalAccess"  : (0x5, 0x09), # PREPARE GENERAL ACCESS
    "UNPREPARE_generalAccess": (0x5, 0x0A), # UNPREPARE GENERAL ACCESS
    "PREPARE_StyleAccess"    : (0x5, 0x18), # PREPARE STYLE ACCESS
    "UNPREPARE_StyleAccess"  : (0x5, 0x19), # UNPREPARE STYLE ACCESS
    "DATA_HEADER"            : (0x5, 0x0C), # DATA DUMP HEADER
    "DATA_DUMP"              : (0x5, 0x0D), # DATA DUMP
    "DELETE"                 : (0x5, 0x0E), # DELETE
    "DIR_REQUEST"            : (0x5, 0x0F), # DIRECTORY REQUEST
    "DIR_ANSWER"             : (0x5, 0x10), # DIRECTORY ANSWER
    "DATA_REQUEST"           : (0x5, 0x0B), # DATA_REQUEST
    "MESSAGECAPTUREON"       : (0x5, 0x11), # MESSAGE CAPTURE ON
    "MESSAGECAPTUREOFF"      : (0x5, 0x12), # MESSAGE CAPTURE OFF
    "MESSAGESEND"            : (0x5, 0x13), # MESSAGE SEND
    "MESSAGEANSWER"          : (0x5, 0x14), # MESSAGE ANSWER
    "ENABLEEDITUPDATE"       : (0x5, 0x15), # ENABLE EDIT UPDATE
    "DISABLEEDITUPDATE"      : (0x5, 0x16), # DISABLE EDIT UPDATE
    "D_ERR"                  : (0x5, 0x7B), # DEVICE ERROR
    "PUT_KEY"                : (0x5, 0x17), # WRITE KEY
    # EXTRA
    "F_WAIT"                 : (0x0, 0x7C), # WAIT
    "F_CANCEL"               : (0x0, 0x7D), # CANCEL
    "F_NACK"                 : (0x0, 0x7E), # NACK
    "F_ACK"                  : (0x0, 0x7F), # ACK
    "D_WAIT"                 : (0x5, 0x7C), # DEVICE WAIT
    "D_CANCEL"               : (0x5, 0x7D), # DEVICE CANCEL
    "D_NACK"                 : (0x5, 0x7E), # DEVICE NACK
    "D_ACK"                  : (0x5, 0x7F), # DEVICE ACK
    }

# Tries to match message to S3 function
def S3FunctionName(msg):
    func    = (msg[2] >> 4)
    subfunc = msg[3]
    for k,v in S3Functions.iteritems():
        if v == (func,subfunc):
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
        appendChecksum = True
        if len(args):
            data += args
            appendChecksum = False
            
        func = 0
        subfunc = 0
        self.name = kwargs.get("fromName", None)
        if self.name:
            func, subfunc = S3Functions.get(self.name, (None, None))
            if not func: raise Exception("Unknown Command")
            
        self.magic    = kwargs.get("magic", 0xF0)
        self.vendor   = kwargs.get("vendor", 0x2F)
        self.func     = kwargs.get("func", func)
        self.subfunc  = kwargs.get("subfunc", subfunc)
        self.chan     = kwargs.get("chan", 0x0)
        self.reqchan  = kwargs.get("reqchan", 0x0)
        self.data     = kwargs.get("data", data)
        self.term     = kwargs.get("term", 0xF7)
        self.appendChecksum = kwargs.get("appendChecksum", appendChecksum)

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

        self.handlers = {
            # FILE FUNCTIONS  FILE_F
            "F_DHDR":      self.handleFileDumpHeader,
            "F_DPKT":      self.handleFileDumpDataBlock,
            "DIR_HDR":     self.handleFileDumpHeader,
            "F_WAIT"     : noop,
            # DEVICE COMMAND  DEVICE_CMD
            "STAT_ANSWER": self.handleStatusAnswer,
            "DATA_HEADER": self.handleDirectoryAnswer,
            "DATA_DUMP"  : self.handleDataDump,
            "DIR_ANSWER" : self.handleDirectoryAnswer,
            "D_WAIT"     : noop,
        }

    def __del__(self):
        if self.dump_file:
            self.dump_file.close()
            print "Closed dump file"

    def createDumpFile(self):
        timestamp = time.strftime("%Y%m%d%H%M%S")
        fname="dump_%s.bin" % timestamp
        self.dump_file = open(fname,"wb")
        print "Opened dump file '%s'" % fname
        
    def dump(self,data):
        if not self.dump_file:
            self.createDumpFile()
        self.dump_file.write(bytearray(data))
        
    # FILE FUNCTIONS  FILE_F
    def handleFileDumpHeader(self,msg):
        self.sendSysEx( MSCEIMessage(fromName="F_WAIT"))
        offset=17 + 2*8
        location = ''
        while msg[offset] != 0:
            location += chr(msg[offset])
            offset += 1
        offset+=1
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            self.sendSysEx( MSCEIMessage(fromName="F_ACK"))
        else:
            self.sendSysEx( MSCEIMessage(fromName="F_NACK"))
        
    def handleFileDumpDataBlock(self,msg):
        self.sendSysEx( MSCEIMessage(fromName="F_WAIT"))
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
            self.sendSysEx( MSCEIMessage(fromName="F_ACK"))
        else:
            self.sendSysEx( MSCEIMessage(fromName="F_NACK"))

    # DEVICE COMMAND  DEVICE_CMD
    def handleStatusAnswer(self,msg):
        self.sendSysEx( MSCEIMessage(fromName="D_WAIT"))
        offset= 5 + 3*8
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            self.sendSysEx( MSCEIMessage(fromName="D_ACK"))
        else:
            self.sendSysEx( MSCEIMessage(fromName="D_NACK"))

    def handleDataDump(self,msg):
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
            self.sendSysEx( MSCEIMessage(fromName="D_ACK"))
        else:
            self.sendSysEx( MSCEIMessage(fromName="D_NACK"))

    def handleDirectoryAnswer(self,msg):
        self.sendSysEx( MSCEIMessage(fromName="D_WAIT"))
        offset = 8 + 11 + 1 + 16 + 11
        cc = msg[offset]
        cc_calc = checksum(msg[1:offset])
        if cc == cc_calc:
            self.sendSysEx( MSCEIMessage(fromName="D_ACK"))
        else:
            self.sendSysEx( MSCEIMessage(fromName="D_NACK"))
        
    def parse(self, msg, timestamp=-1):
        if msg[0] != 0xF0:
            print 'Non-sysex message'
            print [ hex(b) for b in msg ]
            print
            return

        fname = S3FunctionName(msg)
        if not fname:
            return
        
        print "Received", fname, "@", timestamp
        printer = MessagePrinter.get(fname,None)
        if printer: printer(msg)
        handler = self.handlers.get(fname, None)
        if handler: handler(msg)
        else: print [ hex(b) for b in msg ]
        print

    def sendSysEx(self,msg,timestamp=0):
        fname = S3FunctionName(msg.raw())
        if fname:
            print "Sending", fname, "@", timestamp
            p = MessagePrinter.get(fname,None)
            if p: p(msg)
        self.send_conn.send( (timestamp,msg.raw()))
