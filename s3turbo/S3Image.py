from __future__ import print_function
import cStringIO, os, time, struct

from s3turbo.Util import dateToStr, timeToStr, strToDate, strToTime, makeTimes
from s3turbo.Util import encodePath
from s3turbo.S3Turbo      import S3Exception
from s3turbo.S3BootSector import S3BootSector
from s3turbo.Fat12        import Fat12
from s3turbo.DirEntry     import DirEntry

class S3Image(object):
    def __init__(self,debug=False):
        self.debug = debug
        self.reset()

    def reset(self):
        self.bs          = S3BootSector()
        self.fat         = Fat12(rawsize=self.bs.fat_size())
        self.rootentries = [
            DirEntry(shortname='\x20'*8,
                     shortext='\x20'*3,
                     attr=DirEntry.ATTR_VOLLABEL),
        ]
        self.clusterdata = {}
        
    def ndata_clusters(self):
        skip_sectors = 1 + \
                       self.bs.sectorsperfat*self.bs.nfats + \
                       self.bs.nrootentries*DirEntry.SIZE/self.bs.bytespersector
        return (self.bs.nsectors-skip_sectors)/self.bs.sectorspercluster
    
    def cluster_to_offset(self,cluster):
        return self.bs.root_offset() + \
            self.bs.nrootentries*DirEntry.SIZE + \
            self.bs.cluster_size()*(cluster-2)

    def read_from_file(self,filename,compatibilityMode=False):
        if not os.path.exists(filename):
            raise S3Exception("File '%s' not found" % filename)
        with open(filename,'rb') as f:
            self.read(f,compatibilityMode=compatibilityMode,
                      maxsize=os.path.getsize(filename))
        
    def read(self,f,compatibilityMode=False,maxsize=-1):
        self.reset()

        if compatibilityMode:
            warn_defaults = [
                'bytespersector', 'nfats', 'nrootentries', 'nsectors',
                'sectorsperfat', 'sectorspertrack', 'nsectorsext',
            ]
        else:
            warn_defaults = []
            
        # read boot sector
        self.bs.from_raw(f,warn_defaults=warn_defaults)
        if maxsize > 0 and maxsize != self.bs.disk_size():
            s = "max size (%d bytes) not matching" \
                " size from boot sector (%d bytes)" % \
                (maxsize,self.bs.disk_size())
            if compatibilityMode:
                print("WARNING in %s:\n %s" % (filename,s))
            else:
                raise S3Exception(s)

        # read FAT
        f.seek(self.bs.fat_offset())
        self.fat.from_raw(f.read(self.bs.fat_size()))

        # read root directory
        self.rootentries = []
        f.seek(self.bs.root_offset())
        for i in range(self.bs.nrootentries):
            de = DirEntry(data=f)
            if de.is_empty(): break
            self.rootentries.append(de)
        if not len(self.rootentries):
            raise S3Exception(
                "error reading root directory")
        if not self.rootentries[0].has_attr(DirEntry.ATTR_VOLLABEL):
            raise S3Exception(
                "volume information is not first entry in root directory")

        # read rest of disk
        for cluster in range(2,self.ndata_clusters()+2):
            if self.fat.get(cluster) != 0:
                f.seek(self.cluster_to_offset(cluster))
                self.clusterdata[cluster] = f.read(self.bs.cluster_size())
                    
    def write_to_file(self,filename):
        with open(filename,'wb') as f:
            self.write(f)

    def write(self,f):
        f.write(self.bs.to_raw())
        f.seek(self.bs.fat_offset())
        f.write(self.fat.to_raw())
        f.seek(self.bs.root_offset())
        for e in self.rootentries:
            f.write(e.to_raw())
        for cluster in range(2,self.ndata_clusters()+2):
            f.seek(self.cluster_to_offset(cluster))
            f.write(self.clusterdata.get(cluster,
                                         '\xcb'*self.bs.cluster_size()))
        
    def test_file(self,filename):
        if not os.path.exists(filename):
            raise S3Exception("File '%s' not found" % filename)
        with open(filename,'rb') as f:
            testdata = f.read()

        import hashlib, binascii
        hash_test = hashlib.md5()
        hash_test.update(testdata)
        digest_test = binascii.hexlify(hash_test.digest())
        write = cStringIO.StringIO()
        self.write(write)
        hash_write = hashlib.md5()
        hash_write.update(write.getvalue())
        digest_write = binascii.hexlify(hash_write.digest())

        if self.debug:
            print("md5  in: %s" % digest_test)
            print("md5 out: %s" % digest_write)

        if digest_test != digest_write:
            with open(filename,'rb') as f:
                for cluster in range(2,self.ndata_clusters()+2):
                    f.seek(self.cluster_to_offset(cluster))
                    orig = f.read(self.bs.cluster_size())
                    proc = self.clusterdata.get(cluster,
                                                '\xcb'*self.bs.cluster_size())
                    if orig != proc:
                        print("First mismatch in cluster 0x%x at address 0x%x"%\
                              (cluster,self.cluster_to_offset(cluster)))
                        break
            raise S3Exception("test_file failed")
        
    def set_volname(self,name):
        if len(name) > 11:
            print("WARNING: trimming volume name to 11 characters")
        self.rootentries[0].set_name(name)
        
    def set_voldate(self,date=None):
        if date is None: date = strToDate(time.strftime("%d/%m/%Y"))
        self.rootentries[0].mdate = date
        
    def set_voltime(self,t=None):
        if t is None: t = strToTime(time.strftime("%H:%M:%S"))
        self.rootentries[0].mtime = t
        
    def dump_direntry(self,de,indent=0):
        name = de.decodedName().strip()
        if de.is_dir(): name = '[%s]' % name
        print('%s%-14s %8d %s %s  %2x %7d (0x%x)' % (
            indent*' ', name, de.size, timeToStr(de.mtime), dateToStr(de.mdate),
            de.attr,de.start,self.cluster_to_offset(de.start)))

    def dump_contents(self,start=None,path='A:'):
        if start is None:
            print("-"*80)
            volname = self.rootentries[0].name().strip()
            if not len(volname):
                volname = "<empty>"
            print("Volume: %-17s %s %s" % (
                volname,
                timeToStr(self.rootentries[0].mtime),
                dateToStr(self.rootentries[0].mdate)))
            print("-"*80)
            print("%s %s %s %s %s %s %s" % \
                ("Name".center(16), "Size".center(8), "Time".center(8),
                 "Date".center(10), "Att", "Cluster", "(hex)"))
            print("-"*80)

        dirs,files = self.read_dir(start,no_dotdirs=True)
        print(path)
        for d in dirs:  self.dump_direntry(d,indent=2)
        for f in files: self.dump_direntry(f,indent=2)
        print()
        for d in dirs:
            self.dump_contents(start=d.start,path=path+"\\"+d.name().strip())
        
    def dump_props(self):
        if len(self.rootentries):
            for i in [
                    ('volname', repr(self.rootentries[0].name())),
                    ('voldate', dateToStr(self.rootentries[0].mdate)),
                    ('voltime', timeToStr(self.rootentries[0].mtime)),
            ]: print("%-20s: %s" % i)
        else: print("Root directory is empty!")
        print()
        self.bs.dump()

    def dump_fat(self):
        self.fat.dump()
        
    def read_dir(self,cluster=None,no_dotdirs=False):
        dirs, files = [], []
        if cluster is None:
            for de in self.rootentries:
                if de.has_attr(DirEntry.ATTR_VOLLABEL): pass
                elif de.has_attr(DirEntry.ATTR_DIR):    dirs.append(de)
                else:                                   files.append(de)
        else:
            data = cStringIO.StringIO(self.clusterdata.get(cluster,''))
            de = DirEntry(data=data)
            counter = 0
            while not de.is_empty():
                if not de.is_erased():
                    if de.has_attr(DirEntry.ATTR_VOLLABEL): pass
                    elif de.has_attr(DirEntry.ATTR_DIR):    dirs.append(de)
                    else:                                   files.append(de)
                counter += 1
                if counter*32 == self.bs.cluster_size():
                    cluster = self.fat.next_cluster(cluster)
                    counter = 0
                    data = cStringIO.StringIO(self.clusterdata.get(cluster,''))
                de = DirEntry(data=data)
        if no_dotdirs: dirs = [ d for d in dirs if not d.is_dotdir() ]
        return (dirs,files)

    def find_file(self,path):
        path = encodePath(path)
        segments = path.split('\\')
        if len(segments) and segments[0] == 'A:': segments = segments[1:]
        if not len(segments):
            raise S3Exception("findFile: malformed file path '%s'" % path)
        dircluster = None
        while True:
            dirs, files = self.read_dir(dircluster)
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
        
    def extract_file(self,f,compatibilityMode=False):
        buf = ''
        if self.debug: print("extract_file: cluster %d" % f.start)
        chain = self.fat.get_chain(f.start)
        for cluster in chain:
            buf += self.clusterdata[cluster]
        if f.size > len(buf):
            s = "extract_file: unexpected end of file, %d/%d written" % \
                (len(buf),f.size)
            if compatibilityMode: print("WARNING: "+s)
            else:                 raise S3Exception(s)
        return buf[:f.size]

    def extract_all(self,targetdir,cluster=None,compatibilityMode=False):
        if not os.path.exists(targetdir): os.makedirs(targetdir)
        if cluster is None:
            os.utime(targetdir, makeTimes(self.rootentries[0].mdate,
                                          self.rootentries[0].mtime))
        dirs, files = self.read_dir(cluster)
        for f in files:
            fname = f.decodedName().strip()
            outname = os.path.join(targetdir,fname)
            try:
                with open(outname,'wb') as outfile:
                    if self.debug: print("Writing '%s'" % outname)
                    outfile.write(self.extract_file(f))
                os.utime(outname, makeTimes(f.mdate,f.mtime))
            except S3Exception, e: raise
            except Exception, e:
                if self.debug: raise
                s = "extract_all: error writing to file %s" % repr(outname)
                if compatibilityMode: print("WARNING: "+s)
                else:                 raise S3Exception(s)
        for d in dirs:
            dirname = d.decodedName().strip()
            if dirname == '.':
                os.utime(targetdir, makeTimes(d.mdate,d.mtime))
                continue
            elif dirname == '..': continue
            self.extract_all(os.path.join(targetdir,dirname),cluster=d.start)
