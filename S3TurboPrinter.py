from Util import checksum, conv7_8, noop, convertToShort, convertToLong

def printError(msg):
    errs = [ 'No_error', 'Job_invalid', 'Job_in_use', 'Operation_invalid',
             'Drive_invalid', 'Drive_no_write',
             'Media_invalid', 'Media_corrupt', 'Media_protected', 'Media_full',
             'Media_not_inserted', 'Media_not_equal',
             'File_not_found', 'File_open', 'File_in_write', 'File_protected',
             'File_exists', 'MFH_error',
             # from DEVICE ERROR
             'ActiveBankAccess', 'IncompatibleObject',
             'BadObjOperation', 'StyleRecAccess',
    ]
    errno = msg[5]
    if errno < len(errs):
        print errs[errno]
    else:
        print "Unknown error"

def printUpdate(msg):
    family = msg[4]
    group  = msg[5]
    print "family:", family
    print "group: ", group

def printStatusAnswer(msg):
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

def printFileDumpHeader(msg):
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
        "filename"           : repr(str(bytearray(msg[5:16]))),
        "flags"              : msg[16],
        "info.Time"          : convertToShort(data[0:2]),
        "info.Date"          : convertToShort(data[2:4]),
        "info.Length"        : convertToLong(data[4:8]),
        "info.DeviceClass"   : data[8],
        "info.DeviceSubClass": data[9],
        "info.DeviceRelease" : data[10],
        "info.FileType"      : data[11],
        "info.FileFormat"    : data[12],
    }
    print "  Data:"
    for k,v in sorted(datadict.iteritems()):
        print "    %s:" % k, v
    print "  checksum:", hex(msg[offset]), \
        "(calculated 0x%x)" % checksum(msg[1:offset])
    if msg[offset+1] != 0xF7:
        print "  remaining bytes:", [hex(b) for b in msg[offset+1:]]

def printFileDumpDataBlock(msg):
    noctets = msg[5]
    offset=6
    #data = []
    for i in xrange(noctets):
        #data += conv7_8(msg[offset:offset+8])
        offset += 8
    print "  Data:"
    print "    noctets:", noctets
    #print "       data:", data
    print "  checksum:", hex(msg[offset]), \
        "(calculated 0x%x)" % checksum(msg[1:offset])
    if msg[offset+1] != 0xF7:
        print "  remaining bytes:", [hex(b) for b in msg[offset+1:]]

def printDirectoryAnswer(msg):
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
        #"data"          : [hex(d) for d in data],
        "datastr"       : repr(str(bytearray(data))),
        "info.Time"          : convertToShort(data[0:2]),
        "info.Date"          : convertToShort(data[2:4]),
        "info.Length"        : convertToLong(data[4:8]),
        "info.InstrID"       : data[8],
        "info.FileID"        : data[9],
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

MessagePrinter = {
    # FILE FUNCTIONS  FILE_F
    "F_DHDR"     : printFileDumpHeader,
    "F_DPKT"     : printFileDumpDataBlock,
    "DIR_HDR"    : printFileDumpHeader,
    "F_ERR"      : printError,
    # EDIT FUNCTIONS  EDIT_F
    "_UPDATE"    : printUpdate,
    # DEVICE COMMAND  DEVICE_CMD
    "STAT_ANSWER": printStatusAnswer,
    "DATA_HEADER": printDirectoryAnswer,
    "DATA_DUMP"  : printFileDumpDataBlock,
    "DIR_ANSWER" : printDirectoryAnswer,
    "D_ERR"      : printError,
    "D_WAIT"     : noop,
}
