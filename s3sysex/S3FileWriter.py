import cStringIO, time

from s3sysex.Util import strToDate, strToTime

class S3FileWriter(object):
    def __init__(self,filename):
        self.filename = filename
        self.initialize()

        self.offset_vname = 0x1000
        self.offset_vtime = 0x1016
        self.offset_vdate = 0x1018
        
    def initialize(self):
        self.data = cStringIO.StringIO()

        # write boot sector start
        self.data.write("\xeb\x34\x90")                     # bootcode
        self.data.write("\x20\x20\x20\x20\x20\x00\xfc\x2c") # oemname
        self.writeWordLE(1024)                              # bytes / sector
        self.writeByte(1)                                   # sectors / cluster
        self.writeWordLE(1)                                 # reserved
        self.writeByte(1)                                   # no. of FATs
        self.writeWordLE(160)                               # no. of rootentries
        self.writeWordLE(1600)                              # no. of sectors
        self.writeByte(0xf9)                                # media descriptor
        self.writeWordLE(3)                                 # sectors / FAT
        self.writeWordLE(10)                                # sectors / track
        self.writeWordLE(2)                                 # no. of heads
        self.data.write("\x00\x00\x00\x00")                 # no. of hidden sect
        self.data.write("\x2f\xf2\x02\x03")                 # no. of ext sect
        self.data.write("\x00")                             # reserved
        self.data.write("\x00\x00\x00\x00")                 # volume serial
        self.data.write("\x00\x00\x00\x00\x00\x00\x00\x00") # volume label
        self.data.write("\x00\x00\x00")
        self.data.write("\x00\x00\x00\x00\x00\x00\x00\x00") # filesystem ID

        # write author information
        self.data.seek(0x40)
        self.data.write("\x2a\x2a\x47\x45\x4e\x45\x52\x41")
        self.data.write("\x4c\x4d\x55\x53\x49\x43\x2a\x2a")
        self.data.write("\x2a\x2a\x44\x69\x73\x6b\x5f\x5f")
        self.data.write("\x44\x72\x69\x76\x65\x72\x2a\x2a")
        self.data.write("\x2a\x2a\x20\x56\x65\x72\x2e\x20")
        self.data.write("\x20\x31\x2e\x30\x30\x20\x2a\x2a")
        self.data.write("\x2a\x2a\x2a\x20\x31\x36\x2f\x31")
        self.data.write("\x30\x2f\x39\x30\x20\x2a\x2a\x2a")
        self.data.write("\x62\x79\x20\x46\x2e\x20\x42\x72")
        self.data.write("\x61\x63\x61\x6c\x65\x6e\x74\x69")
        
        # write empty FAT
        self.data.seek(0x400)
        self.data.write("\xf9\xff\xff")

        # write root directory
        self.data.seek(0x1000)
        self.data.write("\x20\x20\x20\x20\x20\x20\x20\x20")
        self.data.write("\x20\x20\x20\x08")

        # initialize rest of disk to 0xcb
        self.data.seek(0x2400)
        self.data.write("\xcb"*(0x190000-0x2400))

    def setVolumeName(self,name):
        if len(name) > 11:
            print "WARNING: trimming volume name to 11 characters"
            name = name[:11]
        self.data.seek(self.offset_vname)
        self.data.write(name)
        
    def writeByte(self,b):
        self.data.write(chr(b))
        
    def writeWordLE(self,u16):
        self.data.write(chr(u16&0xff))
        self.data.write(chr((u16>>8)&0xff))
    
    def write(self):
        if self.data is None: return

        # update volume time and date
        self.data.seek(self.offset_vtime)
        self.writeWordLE(strToTime(time.strftime("%H:%M:%S")))
        self.data.seek(self.offset_vdate)
        self.writeWordLE(strToDate(time.strftime("%d/%m/%Y")))
        
        with open(self.filename,'wb') as f:
            f.write(self.data.getvalue())
