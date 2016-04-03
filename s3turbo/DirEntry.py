from __future__ import print_function
import cStringIO, sys, collections
from s3turbo.Util import CharHandler, ByteHandler, WordHandler, LongHandler
from s3turbo.Util import decodePath

class DirEntry(object):
    def __init__(self,**kwargs):
        if 'data' in kwargs.keys():
            self.from_raw(kwargs['data'])
        else:
            self.reset()
        for k,v in kwargs.iteritems():
            if k == 'data': continue
            self.__setattr__(k,v)

    def reset(self):
        for name,handler in DirEntry.attributes.iteritems():
            self.__setattr__(name,handler.default)
        
    def from_raw(self,data):
        for name,handler in DirEntry.attributes.iteritems():
            try:
                self.__setattr__(name,handler.read(data))
            except Exception, e:
                raise Exception("DirEntry.from_raw: error while parsing '%s':\n"
                                " %s" % (name,str(e)))
        
    def to_raw(self):
        data = cStringIO.StringIO()
        for name,handler in DirEntry.attributes.iteritems():
            data.write(handler.write(self.__getattribute__(name)))
        return data.getvalue()

    def is_empty(self):
        return ord(self.shortname[0]) == DirEntry.TYPE_EMPTY

    def is_dotdir(self):
        return ord(self.shortname[0]) == DirEntry.TYPE_DOTDIR

    def is_erased(self):
        return ord(self.shortname[0]) == DirEntry.TYPE_ERASED

    def has_attr(self,attr):
        return attr & self.attr

    def is_dir(self):
        return self.has_attr(DirEntry.ATTR_DIR)

    def name(self):
        return self.shortname+self.shortext

    def set_name(self,name):
        if len(name) > 11:
            name = name[:11]
        name = name.ljust(11)
        self.shortname = name[:8]
        self.shortext  = name[8:]

    def decodedName(self):
        return decodePath(self.name())

    def dump(self,file=sys.stdout):
        for name in DirEntry.attributes.iterkeys():
            print("%-20s: %s" % (name,repr(self.__getattribute__(name))))

DirEntry.attributes = collections.OrderedDict([
    ('shortname', CharHandler(b'\x00'*8)),
    ('shortext',  CharHandler(b'\x00'*3)),
    ('attr',      ByteHandler(0)),
    ('userattr',  ByteHandler(0)),
    ('undelchar', ByteHandler(0)),
    ('ctime',     WordHandler(0)),
    ('cdate',     WordHandler(0)),
    ('adate',     WordHandler(0)),
    ('access',    WordHandler(0)),
    ('mtime',     WordHandler(0)),
    ('mdate',     WordHandler(0)),
    ('start',     WordHandler(0)),
    ('size',      LongHandler(0)),
])

DirEntry.SIZE = 32

DirEntry.TYPE_EMPTY  = 0x0
DirEntry.TYPE_DOTDIR = 0x2e
DirEntry.TYPE_ERASED = 0xe5

DirEntry.ATTR_READONLY = 0x01
DirEntry.ATTR_HIDDEN   = 0x02
DirEntry.ATTR_SYSTEM   = 0x04
DirEntry.ATTR_VOLLABEL = 0x08
DirEntry.ATTR_DIR      = 0x10
DirEntry.ATTR_ARCHIVE  = 0x20
