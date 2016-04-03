from __future__ import print_function
import cStringIO, collections, sys
from s3turbo.Util import CharHandler, ByteHandler, WordHandler, LongHandler

class S3BootSector(object):
    def __init__(self):
        self.reset()

    def reset(self):
        for name,handler in S3BootSector.attributes.iteritems():
            self.__setattr__(name,handler.default)
        
    def to_raw(self):
        data = cStringIO.StringIO()
        for name,handler in S3BootSector.attributes.iteritems():
            data.write(handler.write(self.__getattribute__(name)))
        data.seek(S3BootSector.author_offset)
        data.write(S3BootSector.author)
        return data.getvalue()
    
    def from_raw(self,rawdata,ignore_defaults=['oemname'],warn_defaults=[]):
        for name,handler in S3BootSector.attributes.iteritems():
            data = handler.read(rawdata)
            if self.__getattribute__(name) != data and \
               not name in ignore_defaults:
                s = "%s should be %s, is %s" % \
                    (name,repr(self.__getattribute__(name)), repr(data))
                if name in warn_defaults:
                    print("WARNING: %s, reverting to default" % s)
                    data = handler.default
                else:
                    raise Exception(s)
            self.__setattr__(name,data)

    def dump(self,file=sys.stdout):
        for name in S3BootSector.attributes.iterkeys():
            print("%-20s: %s" % (name,repr(self.__getattribute__(name))),
                  file=file)
        print(file=file)
        print('fat_offset   : %10s' % hex(self.fat_offset()),  file=file)
        print('fat_size     : %10s' % str(self.fat_size()),    file=file)
        print('root_offset  : %10s' % hex(self.root_offset()), file=file)
        print('root_size    : %10s' % str(self.root_size()),   file=file)
        print('cluster_size : %10s' % str(self.cluster_size()),file=file)
        print('disk_size    : %10s' % str(self.disk_size()),   file=file)
            
    def fat_offset(self):
        return self.bytespersector
    
    def fat_size(self):
        return self.sectorsperfat*self.bytespersector

    def root_offset(self):
        return self.fat_offset() + self.nfats*self.fat_size()

    def root_size(self):
        return self.nrootentries*32
    
    def cluster_size(self):
        return self.sectorspercluster*self.bytespersector

    def disk_size(self):
        return self.bytespersector*self.nsectors

S3BootSector.attributes = collections.OrderedDict([
    ('jumpcode',          CharHandler(b'\xeb\x34\x90')),
    ('oemname',           CharHandler(b'\x20\x20\x20\x20\x20\x00\x00\xda')),
    ('bytespersector',    WordHandler(1024)),
    ('sectorspercluster', ByteHandler(1)),
    ('reserved1',         WordHandler(1)),
    ('nfats',             ByteHandler(1)),
    ('nrootentries',      WordHandler(160)),
    ('nsectors',          WordHandler(1600)),
    ('mediadescbyte',     ByteHandler(0xf9)),
    ('sectorsperfat',     WordHandler(3)),
    ('sectorspertrack',   WordHandler(10)),
    ('nheads',            WordHandler(2)),
    ('nhiddensectors',    LongHandler(0)),
    ('nsectorsext',       LongHandler(50524719)),
    ('reserved2',         ByteHandler(0)),
    ('volumeserial',      CharHandler(b'\x00'*4)),
    ('volumelabel',       CharHandler(b'\x00'*11)),
    ('fsid',              CharHandler(b'\x00'*8)),
])

S3BootSector.author_offset = 0x40
S3BootSector.author = "\x2a\x2a\x47\x45\x4e\x45\x52\x41" \
                      "\x4c\x4d\x55\x53\x49\x43\x2a\x2a" \
                      "\x2a\x2a\x44\x69\x73\x6b\x5f\x5f" \
                      "\x44\x72\x69\x76\x65\x72\x2a\x2a" \
                      "\x2a\x2a\x20\x56\x65\x72\x2e\x20" \
                      "\x20\x31\x2e\x30\x30\x20\x2a\x2a" \
                      "\x2a\x2a\x2a\x20\x31\x36\x2f\x31" \
                      "\x30\x2f\x39\x30\x20\x2a\x2a\x2a" \
                      "\x62\x79\x20\x46\x2e\x20\x42\x72" \
                      "\x61\x63\x61\x6c\x65\x6e\x74\x69"
