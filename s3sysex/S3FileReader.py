import os

from s3sysex.Util import dateToStr, timeToStr
from s3sysex.S3Turbo import S3Exception

class S3FileReader(object):
    def __init__(self,filename,compatible=False,debug=False):
        self.filename   = filename
        self.compatible = compatible
        self.debug      = debug
        
        self.subst = [
            ('\xc4','D'), # sound patch RAM
            ('\xc5','E'), # RAM samples used
            ('\xc6','F'), # normal RAM
            ('\xc8','!'), # copy protection (?)
            ('\xc9','@'), # copy protection (?)
            ('/','\\'),
        ]

        self.file     = None
        if os.path.exists(filename):
            self.file     = open(filename,'rb')
            self.filesize = os.path.getsize(filename)
        else:
            raise S3Exception("File '%s' not found" % filename)
        
        self.readBootSector()
        self.readFAT()
        self.readVolumeInformation()

    def __del__(self):
        if self.file:  self.file.close()

    def seek(self,offset):
        if offset < self.filesize:
            self.file.seek(offset)
        else:
            raise S3Exception("Trying to seek to offset 0x%x beyond EOF" %
                              offset)
        
    def read(self,size):
        if self.file.tell()+size > self.filesize:
            overflow = self.file.tell()+size-self.filesize
            raise S3Exception("Trying to read %d bytes beyond EOF" % overflow)
        return self.file.read(size)
        
    def readStr(self,size):
        return self.read(size)

    def readByte(self):
        return ord(self.read(1))
    
    def readWordLE(self):
        tmp = self.read(2)
        return ord(tmp[1])<<8 | ord(tmp[0])
    
    def readDoubleWordLE(self):
        tmp = self.read(4)
        return ord(tmp[1])<<8 | ord(tmp[0]) | ord(tmp[3])<<24 | ord(tmp[2])<<16
    
    def readBootSector(self):
        self.seek(0)
        jumpcode          = self.readStr(3)
        if jumpcode != "\xeb\x34\x90":
            raise S3Exception("Boot sector: wrong jump code")
        self.oemname      = self.readStr(8)
        bytespersector    = self.readWordLE()
        if bytespersector != 1024:
            s = "Boot sector: bytes per sector should be 1024 but is %d" % \
                bytespersector
            if self.compatible: print "WARNING:", s
            else:               raise S3Exception(s)
        sectorspercluster = self.readByte()
        if sectorspercluster != 1:
            raise S3Exception(
                "Boot sector: sectors per cluster should be 1 but is %d" %
                sectorspercluster)
        reserved          = self.readWordLE()
        nfats             = self.readByte()
        if nfats != 1:
            raise S3Exception(
                "Boot sector: number of FATs should be 1 but is %d" % nfats)
        self.rootentries  = self.readWordLE()
        if self.rootentries != 160:
            raise S3Exception(
                "Boot sector: number of root entries should be 160 but is %d" %
                self.rootentries)
        totalsectors      = self.readWordLE()
        if totalsectors != 1600:
            raise S3Exception(
                "Boot sector: number of sectors should be 1600 but is %d" %
                totalsectors)
        mediadescbyte     = self.readByte()
        if mediadescbyte != 0xf9:
            raise S3Exception(
                "Boot sector: media desciptor byte is not 0xF9 but is 0x%02x" %
                mediadescbyte)
        sectorsperfat     = self.readWordLE()
        if sectorsperfat != 3:
            raise S3Exception(
                "Boot sector: number of sectors per FAT should be 3 but is %d" %
                sectorsperfat)
        sectorspertrack   = self.readWordLE()
        if sectorspertrack != 10:
            raise S3Exception(
                "Boot sector: number of sectors per track should be 10 but is %d" %
                sectorspertrack)
        nheads            = self.readWordLE()
        if nheads != 2:
            raise S3Exception(
                "Boot sector: number of heads should be 2 but is %d" % nheads)
        nhiddensectors    = self.readDoubleWordLE()
        if nhiddensectors != 0:
            raise S3Exception(
                "Boot sector: number of hidden sectors should be 0 but is %d" %
                nhiddensectors)
        nsectors          = self.readDoubleWordLE()
        reserved          = self.readByte()
        volserial         = self.readStr(4)
        vollabel          = self.readStr(11)
        fsid              = self.readStr(8)

        self.fatsize       = sectorsperfat*bytespersector
        self.clustersize   = sectorspercluster*bytespersector
        self.start_fat     = bytespersector
        self.start_root    = self.start_fat+self.fatsize
        self.start_cluster = self.start_root+self.rootentries*32
        
    def readFAT(self):
        self.seek(self.start_fat)
        self.fat = self.read(self.fatsize)

    def readVolumeInformation(self):
        self.seek(self.start_root)
        de = self.readDirEntry()
        if de.attr & 0x8:
            self.volname = (de.shortname+de.shortext).strip()
            self.voltime = de.mtime
            self.voldate = de.mdate
        else:
            raise S3Exception(
                "volume information is not first entry in root directory")
        
    def readDirectory(self,dirlist=[],filelist=[],cluster=None):
        if cluster is None:
            self.seek(self.start_root)
        else:
            self.seek(self.clusterToOffset(cluster))
        de = self.readDirEntry()
        counter = 0
        while de.shortname[0] != '\0':
            if de.shortname[0] != '\xe5':
                if de.attr & 0x8:
                    pass
                elif de.attr & 0x10:
                    dirlist.append(de)
                else:
                    filelist.append(de)
            counter += 1
            if cluster is None:
                if counter == self.rootentries: break
            elif counter*32 == self.clustersize:
                cluster = self.lookupCluster(cluster)
                if   cluster == 0xfff: break
                elif cluster == 0x0:
                    s = "readDir: cluster %d links to 0" % cluster
                    if self.compatible:
                        print "WARNING", s
                        break
                    else:
                        raise S3Exception(s)
                else:
                    counter = 0
                    self.seek(self.clusterToOffset(cluster))
            de = self.readDirEntry()
    
    def readDirEntry(self,offset=None):
        if not offset is None:
            self.seek(offset)
        return type('DirEntry',(),{
            'addr'      : self.file.tell(),
            'shortname' : self.readStr(8),
            'shortext'  : self.readStr(3),
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
            'size'      : self.readDoubleWordLE(),
        })

    def clusterToOffset(self,cluster):
        return self.start_cluster+self.clustersize*(cluster-2)
    
    def printDirEntry(self,de,indent=0):
        print '%s%-14s %8d %s %s  %2x %7d (0x%x)' % (
            indent*' ', de.shortname+de.shortext, de.size, timeToStr(de.mtime),
            dateToStr(de.mdate),de.attr,de.start,self.clusterToOffset(de.start))

    def printContents(self,start=None,path='A:'):
        if start is None:
            print "-"*80
            volname = self.volname if len(self.volname.strip()) else "<empty>"
            print "Volume: %-17s %s %s Filename: %s" % (
                volname, timeToStr(self.voltime), dateToStr(self.voldate),
                os.path.basename(self.filename))
            print "-"*80
            print "%s %s %s %s %s %s %s" % \
                ("Name".center(16), "Size".center(8), "Time".center(8),
                 "Date".center(10), "Att", "Cluster", "(hex)")
            print "-"*80

        dirs, files = [], []
        self.readDirectory(dirlist=dirs,filelist=files,cluster=start)
        print path
        for d in dirs:
            dirname = (d.shortname+d.shortext).strip()
            if dirname in ['.','..']: continue
            self.printDirEntry(d,2)
        for f in files:
            self.printDirEntry(f,2)
        print
        for d in dirs:
            dirname = (d.shortname+d.shortext).strip()
            if dirname in ['.','..']: continue
            self.printContents(d.start,path+"\\"+dirname)
        
    def dumpProps(self):
        for k,v in sorted(self.__dict__.iteritems()):
            if k in [ 'root', 'fat', 'file', 'filename' ]: continue
            if type(v) == type(int()):
                print "%-20s: %-10d 0x%04x" % (k,v,v)
            elif type(v) == type(str()):
                print "%-20s: %s" % (k,repr(str(bytearray(v))))

    def findFile(self,path):
        segments = path.split('\\')
        if len(segments) and  segments[0] == 'A:':
            segments = segments[1:]
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
                else:
                    return None
                    #raise S3Exception("findFile: directory not found")
            else:
                for f in files:
                    filename = (f.shortname+f.shortext).strip()
                    if filename == segments[0]:
                        return f
                else:
                    return None
                    #raise S3Exception("findFile: file not found in directory")
        
    def readFile(self,f):
        buf = ''
        if self.debug: print "readFile: cluster", f.start
        self.seek(self.clusterToOffset(f.start))
        buf += self.read(self.clustersize)
        cluster = self.lookupCluster(f.start)
        while not cluster in [0x0, 0xfff]:
            if self.debug: print "readFile: cluster", cluster
            self.seek(self.clusterToOffset(cluster))
            buf += self.read(self.clustersize)
            cluster = self.lookupCluster(cluster)
        if cluster == 0:
            print "WARNING: cluster 0, file %s might be corrupt" % \
                repr(f.shortname+f.shortext)
        if f.size > len(buf):
            s = "readFile: unexpected end of file, %d/%d written" % \
                (len(buf),f.size)
            if self.compatible: print "WARNING:", s
            else:               raise S3Exception(s)
        return buf[:f.size]

    def dumpFAT(self):
        l = [ ord(i) for i in self.fat ]
        nentries = len(l)/3*2
        for i in xrange(nentries):
            if i%16==0:
                print'\n0x%03x:' % i,
            print '0x%03x' % self.lookupCluster(i),
        
    def lookupCluster(self,idx):
        if not self.fat: return
        start = idx/2*3
        triplet = [ ord(i) for i in self.fat[start:start+3] ]
        if idx%2 == 0:
            return triplet[0] | ((triplet[1]&0xf)<<8)
        else:
            return (triplet[1] >> 4) | (triplet[2] << 4)

    def extractAll(self,targetdir,cluster=None):
        if not os.path.exists(targetdir):
            os.makedirs(targetdir)
        dirs, files = [], []
        self.readDirectory(dirlist=dirs,filelist=files,cluster=cluster)
        for f in files:
            fname = (f.shortname+f.shortext).strip()
            # replace special characters in filename
            for before, after in self.subst:
                fname = fname.replace(before,after)

            outname = os.path.join(targetdir,fname)
            try:
                #if os.path.exists(outname):
                #    print "WARNING: overwriting '%s'" % outname
                with open(outname,'wb') as outfile:
                    if self.debug: print "Writing '%s'" % outname
                    outfile.write(self.readFile(f))
            except S3Exception, e:
                raise
            except Exception, e:
                s = "extractAll: error writing to file %s" % repr(outname)
                if self.compatible: print "WARNING:", s
                else:               raise S3Exception(s)
        for d in dirs:
            dirname = (d.shortname+d.shortext).strip()
            # replace special characters in dirname
            for before, after in self.subst:
                dirname = dirname.replace(before,after)
            if dirname in ['.','..']: continue
            self.extractAll(os.path.join(targetdir,dirname),cluster=d.start)
