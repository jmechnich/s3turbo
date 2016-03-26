from __future__ import print_function
import cStringIO, os, time

from s3turbo.Util import dateToStr, timeToStr, strToDate, strToTime, makeTimes
from s3turbo.Util import decodePath, encodePath
from s3turbo.S3Turbo import S3Exception

# 3 bytes
Jumpcode          = b'\xeb\x34\x90'
# 8 bytes
OemName           = b'\x20\x20\x20\x20\x20\x00\x00\xda'
# 2 bytes LE
BytesPerSector    = 1024
# 1 byte
SectorsPerCluster = 1
# 2 bytes LE
Reserved1         = 1
# 1 byte
NFATs             = 1
# 2 bytes LE
NRootEntries      = 160
# 2 bytes LE
NSectors          = 1600
# 1 byte
MediaDescByte     = 0xf9
# 2 bytes LE
SectorsPerFAT     = 3
# 2 bytes LE
SectorsPerTrack   = 10
# 2 bytes LE
NHeads            = 2
# 4 bytes LE
NHiddenSectors    = 0
# 4 bytes LE
NSectorsExt       = 50524719
# 1 byte
Reserved2         = 0
# 4 bytes
VolumeSerial      = b'\x00'*4
# 11 bytes
VolumeLabel       = b'\x00'*11
# 8 bytes
FSID              = b'\x00'*8

RootEntrySize     = 32
FATSize           = SectorsPerFAT*BytesPerSector
ClusterSize       = SectorsPerCluster*BytesPerSector
OffsetFAT         = BytesPerSector
OffsetRoot        = OffsetFAT + FATSize
OffsetCluster1    = OffsetRoot + NRootEntries*RootEntrySize
DiskSize          = BytesPerSector*NSectors
OffsetAuthor      = 0x40
OffsetVolumeName  = 0x1000
OffsetVolumeTime  = 0x1016
OffsetVolumeDate  = 0x1018

class S3Image(object):
    def __init__(self,compatibilityMode=False,debug=False):
        self.compatibilityMode = compatibilityMode
        self.debug             = debug
        
        self.reset()

    def reset(self):
        self.data    = None
        self.fat     = [ 0xf9, 0xff, 0xff ]
        self.oemname = OemName
        self.volname = None
        self.voltime = None
        self.voldate = None

    def createEmpty(self):
        self.reset()
        self.data = cStringIO.StringIO()
        self.writeBootSector()
        self.writeAuthorInfo()
        self.writeFAT()
        self.initRootDirectory()
        self.initDataClusters()

    def initRootDirectory(self):
        self.seek(OffsetRoot)
        self.write("\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x08")

    def initDataClusters(self):
        self.seek(OffsetCluster1)
        self.write('\xcb'*(DiskSize-OffsetCluster1))
        
    def readFromFile(self,filename):
        if not os.path.exists(filename):
            raise S3Exception("File '%s' not found" % filename)
        with open(filename,'rb') as f: diskdata = f.read()
        if len(diskdata) != DiskSize:
            raise S3Exception("File size mismatch, is %d, should be %d" %
                              (len(diskdata),DiskSize))
        if self.debug:
            print( "Read %d bytes from file '%s'" %(len(diskdata),filename))
        self.data = cStringIO.StringIO(diskdata)
        self.checkBootSector()
        self.readFAT()
        self.readVolumeInformation()

    def writeToFile(self,filename):
        if not self.data:
            raise S3Exception("writeToFile: empty data")
        with open(filename,'wb') as f: f.write(self.data.getvalue())
        
    def checkBootSector(self):
        self.seek(0)
        buf = self.read(3)
        if buf != Jumpcode:
            raise S3Exception("Boot sector: wrong jump code")
        self.oemname = self.read(8)
        buf = self.readWordLE()
        if buf != BytesPerSector:
            s = "Boot sector: bytes per sector should be %d but is %d" % \
                (BytesPerSector,buf)
            if self.compatibilityMode: print("WARNING: "+s)
            else:                      raise S3Exception(s)
        buf = self.readByte()
        if buf != SectorsPerCluster:
            raise S3Exception(
                "Boot sector: sectors per cluster should be %d but is %d" %
                (SectorsPerCluster,buf))
        self.readWordLE()
        buf = self.readByte()
        if buf != NFATs:
            raise S3Exception(
                "Boot sector: number of FATs should be %d but is %d" % \
                (NFATs,buf))
        buf  = self.readWordLE()
        if buf != NRootEntries:
            raise S3Exception(
                "Boot sector: number of root entries should be %d but is %d" %
                (NRootEntries,buf))
        buf = self.readWordLE()
        if buf != NSectors:
            raise S3Exception(
                "Boot sector: number of sectors should be %d but is %d" %
                (NSectors,buf))
        buf = self.readByte()
        if buf != MediaDescByte:
            raise S3Exception(
                "Boot sector: media desciptor byte is not 0x%02x but is 0x%02x"%
                (MediaDescByte,buf))
        buf = self.readWordLE()
        if buf != SectorsPerFAT:
            raise S3Exception(
                "Boot sector: number of sectors per FAT should be %d but is %d"%
                (SectorsPerFAT,buf))
        buf = self.readWordLE()
        if buf != SectorsPerTrack:
            raise S3Exception(
                "Boot sector: number of sectors per track should be %d but is %d" %
                (SectorsPerTrack,buf))
        buf = self.readWordLE()
        if buf != NHeads:
            raise S3Exception(
                "Boot sector: number of heads should be %d but is %d" %
                (NHeads,buf))
        buf = self.readLongWordLE()
        if buf != NHiddenSectors:
            raise S3Exception(
                "Boot sector: number of hidden sectors should be %d but is %d" %
                (NHiddenSectors,buf))

    def writeBootSector(self):
        self.seek(0)
        self.write(Jumpcode)
        self.write(self.oemname)
        self.writeWordLE(BytesPerSector)
        self.writeByte(SectorsPerCluster)
        self.writeWordLE(Reserved1)
        self.writeByte(NFATs)
        self.writeWordLE(NRootEntries)
        self.writeWordLE(NSectors)
        self.writeByte(MediaDescByte)
        self.writeWordLE(SectorsPerFAT)
        self.writeWordLE(SectorsPerTrack)
        self.writeWordLE(NHeads)
        self.writeLongWordLE(NHiddenSectors)
        self.writeLongWordLE(NSectorsExt)
        self.writeByte(Reserved2)
        self.write(VolumeSerial)
        self.write(VolumeLabel)
        self.write(FSID)

    def writeAuthorInfo(self):
        self.seek(OffsetAuthor)
        self.write("\x2a\x2a\x47\x45\x4e\x45\x52\x41")
        self.write("\x4c\x4d\x55\x53\x49\x43\x2a\x2a")
        self.write("\x2a\x2a\x44\x69\x73\x6b\x5f\x5f")
        self.write("\x44\x72\x69\x76\x65\x72\x2a\x2a")
        self.write("\x2a\x2a\x20\x56\x65\x72\x2e\x20")
        self.write("\x20\x31\x2e\x30\x30\x20\x2a\x2a")
        self.write("\x2a\x2a\x2a\x20\x31\x36\x2f\x31")
        self.write("\x30\x2f\x39\x30\x20\x2a\x2a\x2a")
        self.write("\x62\x79\x20\x46\x2e\x20\x42\x72")
        self.write("\x61\x63\x61\x6c\x65\x6e\x74\x69")

    def setVolumeName(self,name):
        if len(name) > 11:
            print("WARNING: trimming volume name to 11 characters")
            name = name[:11]
        self.seek(OffsetVolumeName)
        self.write(name)
        
    def setVolumeDate(self,date=None):
        if date is None: date = strToDate(time.strftime("%d/%m/%Y"))
        self.seek(OffsetVolumeDate)
        self.writeWordLE(date)
        
    def setVolumeTime(self,t=None):
        if t is None: t = strToTime(time.strftime("%H:%M:%S"))
        self.seek(OffsetVolumeTime)
        self.writeWordLE(t)
        
    def seek(self,off):
        if off < DiskSize: self.data.seek(off)
        else: raise S3Exception("Trying to seek to offset 0x%x beyond EOF"%off)

    def read(self,size):
        if self.data.tell()+size > DiskSize:
            overflow = self.data.tell()+size-DiskSize
            raise S3Exception("Trying to read %d bytes beyond EOF" % overflow)
        return self.data.read(size)
        
    def readByte(self):
        return ord(self.read(1))
    
    def readWordLE(self):
        tmp = self.read(2)
        return ord(tmp[1])<<8 | ord(tmp[0])
    
    def readLongWordLE(self):
        return self.readWordLE() | (self.readWordLE() << 16)

    def read(self,size):
        if self.data.tell()+size > DiskSize:
            overflow = self.data.tell()+size-DiskSize
            raise S3Exception("Trying to read %d bytes beyond EOF" % overflow)
        return self.data.read(size)
        
    def write(self,s):
        self.data.write(s)

    def writeByte(self,b):
        self.write(chr(b))
    
    def writeWordLE(self,w):
        self.write(chr(w &0xff))
        self.write(chr((w>>8) & 0xff))
    
    def writeLongWordLE(self,dw):
        self.writeWordLE(dw & 0xffff)
        self.writeWordLE((dw>>16) & 0xffff)

    def readFAT(self):
        self.seek(OffsetFAT)
        self.fat = [ ord(i) for i in self.read(FATSize) ]

    def writeFAT(self):
        self.seek(OffsetFAT)
        for i in self.fat: self.writeByte(i)

    def readVolumeInformation(self):
        self.seek(OffsetRoot)
        de = self.readDirEntry()
        if de.attr & 0x8:
            self.volname = (de.shortname+de.shortext).strip()
            self.voltime = de.mtime
            self.voldate = de.mdate
        else:
            raise S3Exception(
                "volume information is not first entry in root directory")

    def readDirectory(self,dirlist=[],filelist=[],cluster=None):
        if cluster is None: self.seek(OffsetRoot)
        else:               self.seek(self.clusterToOffset(cluster))
        de = self.readDirEntry()
        counter = 0
        while de.shortname[0] != '\0':
            if de.shortname[0] != '\xe5':
                if de.attr & 0x8:     pass
                elif de.attr & 0x10:  dirlist.append(de)
                else:                 filelist.append(de)
            counter += 1
            if cluster is None:
                if counter == NRootEntries: break
            elif counter*32 == ClusterSize:
                cluster = self.lookupCluster(cluster)
                if   cluster == 0xfff: break
                elif cluster == 0x0:
                    s = "readDir: cluster %d links to 0" % cluster
                    if self.compatibilityMode:
                        print("WARNING "+s)
                        break
                    else: raise S3Exception(s)
                else:
                    counter = 0
                    self.seek(self.clusterToOffset(cluster))
            de = self.readDirEntry()
    
    def readDirEntry(self,offset=None):
        if not offset is None: self.seek(offset)
        return type('DirEntry',(),{
            'addr'      : self.data.tell(),
            'shortname' : self.read(8),
            'shortext'  : self.read(3),
            'attr'      : self.readByte(),
            'userattr'  : self.readByte(),
            'undelchar' : self.readByte(),
            'ctime'     : self.readWordLE(),
            'cdate'     : self.readWordLE(),
            'adate'     : self.readWordLE(),
            'access'    : self.readWordLE(),
            'mtime'     : self.readWordLE(),
            'mdate'     : self.readWordLE(),
            'start'     : self.readWordLE(),
            'size'      : self.readLongWordLE(),
        })

    def clusterToOffset(self,cluster):
        return OffsetCluster1+ClusterSize*(cluster-2)

    def printDirEntry(self,de,indent=0):
        name = decodePath(de.shortname+de.shortext)
        print('%s%-14s %8d %s %s  %2x %7d (0x%x)' % (
            indent*' ', name, de.size, timeToStr(de.mtime), dateToStr(de.mdate),
            de.attr,de.start,self.clusterToOffset(de.start)))

    def printContents(self,start=None,path='A:'):
        if start is None:
            print("-"*80)
            volname = self.volname if len(self.volname.strip()) else "<empty>"
            print("Volume: %-17s %s %s" % (
                volname, timeToStr(self.voltime), dateToStr(self.voldate)))
            print("-"*80)
            print("%s %s %s %s %s %s %s" % \
                ("Name".center(16), "Size".center(8), "Time".center(8),
                 "Date".center(10), "Att", "Cluster", "(hex)"))
            print("-"*80)

        dirs, files = [], []
        self.readDirectory(dirlist=dirs,filelist=files,cluster=start)
        print(path)
        for d in dirs:
            dirname = (d.shortname+d.shortext).strip()
            if dirname in ['.','..']: continue
            self.printDirEntry(d,2)
        for f in files: self.printDirEntry(f,2)
        print()
        for d in dirs:
            dirname = (d.shortname+d.shortext).strip()
            if dirname in ['.','..']: continue
            self.printContents(d.start,path+"\\"+dirname)
        
    def dumpProps(self):
        for k,v in sorted(self.__dict__.iteritems()):
            if k in [ 'root', 'fat', 'file', 'filename' ]: continue
            if type(v) == type(int()):
                print("%-20s: %-10d 0x%04x" % (k,v,v))
            elif type(v) == type(str()):
                print("%-20s: %s" % (k,repr(str(bytearray(v)))))

    def findFile(self,path):
        path = encodePath(path)
        segments = path.split('\\')
        if len(segments) and segments[0] == 'A:': segments = segments[1:]
        if not len(segments):
            raise S3Exception("findFile: malformed file path '%s'" % path)
        dircluster = None
        while True:
            dirs, files = [], []
            self.readDirectory(dirlist=dirs,filelist=files,cluster=dircluster)
            if len(segments) > 1:
                for d in dirs:
                    dirname = (d.shortname+d.shortext).strip()
                    if dirname == segments[0]:
                        segments = segments[1:]
                        dircluster = d.start
                        break
                else: return None
            else:
                for f in files:
                    filename = (f.shortname+f.shortext).strip()
                    if filename == segments[0]:
                        return f
                else: return None
        
    def extractFile(self,f):
        buf = ''
        if self.debug: print("extractFile: cluster %d" % f.start)
        self.seek(self.clusterToOffset(f.start))
        buf += self.read(ClusterSize)
        cluster = self.lookupCluster(f.start)
        while not cluster in [0x0, 0xfff]:
            if self.debug: print("extractFile: cluster %d" % cluster)
            self.seek(self.clusterToOffset(cluster))
            buf += self.read(ClusterSize)
            cluster = self.lookupCluster(cluster)
        if cluster == 0:
            print("WARNING: cluster 0, file %s might be corrupt" % \
                repr(f.shortname+f.shortext))
        if f.size > len(buf):
            s = "extractFile: unexpected end of file, %d/%d written" % \
                (len(buf),f.size)
            if self.compatibilityMode: print("WARNING: "+s)
            else:                      raise S3Exception(s)
        return buf[:f.size]

    def dumpFAT(self):
        nentries = len(self.fat)/3*2
        for i in xrange(nentries):
            if i%16==0: print('\n0x%03x:' % i,end=" ")
            print('0x%03x' % self.lookupCluster(i),end=" ")
        print()
        
    def lookupCluster(self,idx):
        if not self.fat: raise S3Exception("lookupCluster: empty FAT")
        start = idx/2*3
        triplet = self.fat[start:start+3]
        if idx%2 == 0: return triplet[0] | ((triplet[1]&0xf)<<8)
        else:          return (triplet[1] >> 4) | (triplet[2] << 4)

    def extractAll(self,targetdir,cluster=None):
        if not os.path.exists(targetdir): os.makedirs(targetdir)
        if cluster is None:
            os.utime(targetdir, makeTimes(self.voldate,self.voltime))
        dirs, files = [], []
        self.readDirectory(dirlist=dirs,filelist=files,cluster=cluster)
        for f in files:
            fname = decodePath(f.shortname+f.shortext).strip()
            outname = os.path.join(targetdir,fname)
            try:
                with open(outname,'wb') as outfile:
                    if self.debug: print("Writing '%s'" % outname)
                    outfile.write(self.extractFile(f))
                os.utime(outname, makeTimes(f.mdate,f.mtime))
            except S3Exception, e: raise
            except Exception, e:
                if self.debug: raise
                s = "extractAll: error writing to file %s" % repr(outname)
                if self.compatibilityMode: print("WARNING: "+s)
                else:                      raise S3Exception(s)
        for d in dirs:
            dirname = decodePath(d.shortname+d.shortext).strip()
            if dirname == '.':
                os.utime(targetdir, makeTimes(d.mdate,d.mtime))
                continue
            elif dirname == '..': continue
            self.extractAll(os.path.join(targetdir,dirname),cluster=d.start)
