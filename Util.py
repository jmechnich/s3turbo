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

# convert pair of 8-bit values to 16-bit int, MSB first
def convertToShort(data):
    if len(data) < 2:
        return None
    return data[0] << 8 | data[1]

# convert four 8-bit values to 32-bit int, MSB first
def convertToLong(data):
    if len(data) < 4:
        return None
    return data[0] << 24 | data[1] << 16 | data[2] << 8 | data[3]

# xor checksum of list
def checksum(data):
    ret = 0
    for d in data:
        ret ^= d
    return ret

# does nothing
def noop(msg):
    pass

# string to left-justified list of bytes of length 11
def str2file(s):
    s = str(s).ljust(11)
    return [ ord(c) for c in s ]

# string to null-terminated list of bytes
def str2hex(s):
    s = str(s)
    return [ ord(c) for c in s ] + [ 0x0 ]
