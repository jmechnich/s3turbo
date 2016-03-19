from s3sysex.Util import checksum, conv7_8, noop, convertToShort, convertToLong
from s3sysex.Util import hexdump, timeToStr, dateToStr, prettyPath

class MessagePrinter(object):
    def __init__(self,debug=False):
        self.debug = debug
        
        self.handlers = {
            # FILE FUNCTIONS  FILE_F
            "F_DHDR"     : self.printFileDumpHeader,
            "F_DPKT"     : self.printFileDumpDataBlock,
            "DIR_HDR"    : self.printDirHeader,
            "F_ERR"      : self.printError,
            # EDIT FUNCTIONS  EDIT_F
            "_UPDATE"    : self.printUpdate,
            # DEVICE COMMAND  DEVICE_CMD
            "STAT_ANSWER": self.printStatusAnswer,
            "DATA_HEADER": self.printDirectoryAnswer,
            "DATA_DUMP"  : self.printFileDumpDataBlock,
            "DIR_ANSWER" : self.printDirectoryAnswer,
            "D_ERR"      : self.printError,
            "D_WAIT"     : noop,
        }

    def handle(self,fname,msg):
        for name, handler in self.handlers.iteritems():
            if name == fname:
                handler(msg)
                return
            
    def printError(self,msg):
        errs = [ 'No_error', 'Job_invalid', 'Job_in_use', 'Operation_invalid',
                 'Drive_invalid', 'Drive_no_write',
                 'Media_invalid', 'Media_corrupt', 'Media_protected',
                 'Media_full', 'Media_not_inserted', 'Media_not_equal',
                 'File_not_found', 'File_open', 'File_in_write',
                 'File_protected', 'File_exists', 'MFH_error',
                 # from DEVICE ERROR
                 'ActiveBankAccess', 'IncompatibleObject',
                 'BadObjOperation', 'StyleRecAccess',
        ]
        errno = msg[5]
        if errno < len(errs):
            print errs[errno]
        else:
            print "Unknown error"

    def printUpdate(self,msg):
        family = msg[4]
        group  = msg[5]
        print "family:", family
        print "group: ", group
        
    def printStatusAnswer(self,msg):
        offset=5
        data = []
        for i in xrange(3):
            data += conv7_8(msg[offset:offset+8])
            offset += 8
        datadict = {
            "iClass"       : data[0],
            "iSubClass"    : data[1],
            "iRelease"     : data[2],
            "TotalMem"     : convertToLong(data[4:8]),
            "FreeMem"      : convertToLong(data[8:12]),
            "FreeSampleMem": convertToLong(data[12:16]),
            "ReadyFor"     : tuple(data[16:18]),
            "ActBankPerf"  : tuple(data[18:20]),
        }
        print "  Data:"
        for k,v in sorted(datadict.iteritems()):
            print "    %s:" % k, v
        print "  checksum:", hex(msg[offset]), \
            "(calculated 0x%x)" % checksum(msg[1:offset])
        if msg[offset+1] != 0xF7:
            print "  remaining bytes:", [hex(b) for b in msg[offset+1:]]

    def printFileDumpHeader(self,msg,swapDateTime=False,prettyPrint=True):
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
        datadict = {
            "filename"           : str(bytearray(msg[5:16])),
            "flags"              : msg[16],
            "info.Time"          : timeToStr(convertToShort(data[2:4])
                                             if swapDateTime
                                             else convertToShort(data[0:2])),
            "info.Date"          : dateToStr(convertToShort(data[0:2])
                                             if swapDateTime
                                             else convertToShort(data[2:4])),
            "info.Length"        : convertToLong(data[4:8]),
            "info.DeviceClass"   : data[8],
            "info.DeviceSubClass": data[9],
            "info.DeviceRelease" : data[10],
            "info.FileType"      : data[11],
            "info.FileFormat"    : data[12],
            "location"           : location,
        }
        if prettyPrint and not self.debug:
            if datadict["filename"] == "="*11:
                print "%13s %8s %10s %8s %2s %2s %2s %2s %2s %2s %s" % \
                    ("Filename".center(13),
                     "Size".center(8),
                     "Date".center(8),
                     "Time".center(8),
                     "Fl", "Ty", "Fo", "Cl", "SC", "Re", "Path")
                print "-"*80
            else:
                print "%13s %8d %10s %8s %2s %2s %2s %2s %2s %2s %s" % \
                    (datadict["filename"].ljust(13),
                     datadict["info.Length"],
                     datadict["info.Date"],
                     datadict["info.Time"],
                     datadict["flags"],
                     datadict["info.FileType"],
                     datadict["info.FileFormat"],
                     datadict["info.DeviceClass"],
                     datadict["info.DeviceSubClass"],
                     datadict["info.DeviceRelease"],
                     repr(prettyPath(datadict["location"])))
        else:
            print "  Data:"
            for k,v in sorted(datadict.iteritems()):
                print "    %s:" % k, v
            print "  checksum:", hex(msg[offset]), \
                "(calculated 0x%x)" % checksum(msg[1:offset])
            if msg[offset+1] != 0xF7:
                print "  remaining bytes:", [hex(b) for b in msg[offset+1:]]

    def printDirHeader(self,msg):
        self.printFileDumpHeader(msg,swapDateTime=True)
    
    def printFileDumpDataBlock(self,msg,prettyPrint=True):
        noctets = msg[5]
        offset=6
        #data = []
        for i in xrange(noctets):
            #data += conv7_8(msg[offset:offset+8])
            offset += 8
        if prettyPrint and not self.debug:
            pass
        else:
            print "  Data:"
            print "    noctets:", noctets
            #print "       data:", data
            print "  checksum:", hex(msg[offset]), \
                "(calculated 0x%x)" % checksum(msg[1:offset])
        if msg[offset+1] != 0xF7:
            print "  remaining bytes:", [hex(b) for b in msg[offset+1:]]

    def printDirectoryAnswer(self,msg):
        offset=20
        data = []
        for i in xrange(2):
            data += conv7_8(msg[offset:offset+8])
            offset += 8
        datadict = {
            "type"          : msg[5],
            "bank"          : msg[6],
            "perf"          : msg[7],
            "filename1"     : repr(str(bytearray(msg[8:19]))),
            "fileflags"     : msg[19],
            "datastr"       : hexdump(data),
            "info.Time"     : convertToShort(data[0:2]),
            "info.Date"     : convertToShort(data[2:4]),
            "info.Length"   : convertToLong(data[4:8]),
            "info.InstrID"  : data[8],
            "info.FileID"   : data[9],
            "filename2"     : repr(str(bytearray(msg[offset:offset+11]))),
        }
        offset += 11
        print "  Data:"
        for k,v in sorted(datadict.iteritems()):
            print "    %s:" % k, v
        print "  checksum:", hex(msg[offset]), \
            "(calculated 0x%x)" % checksum(msg[1:offset])
        if msg[offset+1] != 0xF7:
            print "  remaining bytes:", [hex(b) for b in msg[offset+1:]]
