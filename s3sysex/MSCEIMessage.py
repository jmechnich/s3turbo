from s3sysex.S3Turbo import S3Functions, S3Exception

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
            func, subfunc, appendChecksum = S3Functions.get(
                self.name, (None, None,None))
            if func is None:
                raise S3Exception("Unknown Command '%s'" % self.name)
        
        self.magic    = kwargs.get("magic", 0xF0)
        self.vendor   = kwargs.get("vendor", 0x2F)
        self.func     = kwargs.get("func", func)
        self.subfunc  = kwargs.get("subfunc", subfunc)
        self.chan     = kwargs.get("chan", 0x0)
        self.reqchan  = kwargs.get("reqchan", 0x0)
        self.data     = kwargs.get("data", data)
        self.term     = kwargs.get("term", 0xF7)
        self.appendChecksum = True \
                              if kwargs.get("forceChecksum", False) \
                              else appendChecksum
        
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
