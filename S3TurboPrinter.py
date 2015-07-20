from SysEx import checksum

# 7 to 8 bit conversion
def conv8_7(src):
    ret = []
    accum = 0
    for i in xrange(7):
        accum = accum | ((src[i] & 0x1) << i)
        ret.append(src[i] >> 1)
    ret.append(accum)
    return ret

# 8 to 7 bit conversion
def conv7_8(src):
    ret = []
    bit8 = src[7]
    for i in xrange(7):
        ret.append( (src[i] << 1) + (bit8 & 1))
        bit8 = bit8 >> 1
    return ret

def convertToShort(data):
    if len(data) < 2:
        return None
    return data[0] << 8 | data[1]

def convertToLong(data):
    if len(data) < 4:
        return None
    return data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3]

def printFileError(msg):
    errs = [ 'No_error', 'Job_invalid', 'Job_in_use', 'Operation_invalid',
             'Drive_invalid', 'Drive_no_write',
             'Media_invalid', 'Media_corrupt', 'Media_protected', 'Media_full',
             'Media_not_inserted', 'Media_not_equal',
             'File_not_found', 'File_open', 'File_in_write', 'File_protected',
             'File_exists', 'MFH_error' ]
    errno = msg[5]
    if errno < len(errs):
        print errs[errno]
    else:
        print "Unknown file error"

def printStatusAnswer(msg):
    offset=5
    data = []
    for i in xrange(3):
        data += conv7_8(msg[offset:offset+8])
        offset += 8
    STAT = {
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
    for k,v in STAT.iteritems():
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
    DUMP_HEADER = {
        "filename"           : msg[5:16],
        "flags"              : msg[16],
        "info.Time"          : convertToShort(data[0:2]),
        "info.Date"          : convertToShort(data[2:4]),
        "info.Length"        : convertToShort(data[4:8]),
        "info.DeviceClass"   : data[8],
        "info.DeviceSubClass": data[9],
        "info.DeviceRelease" : data[10],
        "info.FileType"      : data[11],
        "info.FileFormat"    : data[12],
    }
    print "  Data:"
    for k,v in DUMP_HEADER.iteritems():
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

MessagePrinter = {
    "F_DHDR"     : printFileDumpHeader,
    "F_DPKT"     : printFileDumpDataBlock,
    "F_ERR"      : printFileError,
    "STAT_ANSWER": printStatusAnswer,
}
