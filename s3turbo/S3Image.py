from __future__ import print_function
import cStringIO, os, time, struct

from s3turbo.Util import date2str, time2str, str2date, str2time
from s3turbo.Util import encode_path, time_conv_to_local, time_conv_from_local
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
        self.clusterdata = {}

    def get_clusterdata(self,index,throw=False):
        if index == 0:
            return self.clusterdata.get(
                0, DirEntry(shortname='\x20'*8, shortext='\x20'*3,
                            attr=DirEntry.ATTR_VOLLABEL).to_raw())
        elif index == 1:
            raise S3Exception("illegal cluster index")
        else:
            if not throw:
                return self.clusterdata.get(
                    index,'\xcb'*self.bs.cluster_size())

        return self.clusterdata[index]

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
        f.seek(self.bs.root_offset())
        rootdir = ''
        for i in range(self.bs.nrootentries):
            buf = f.read(DirEntry.SIZE)
            if buf[0] == DirEntry.TYPE_EMPTY: break
            rootdir += buf
        if not len(rootdir):
            raise S3Exception(
                "error reading root directory")
        vl = DirEntry(data=rootdir[:DirEntry.SIZE])
        if not vl.has_attr(DirEntry.ATTR_VOLLABEL):
            raise S3Exception(
                "volume information is not first entry in root directory")
        self.clusterdata[0] = rootdir
        
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
        f.write(self.get_clusterdata(0))
        for cluster in range(2,self.ndata_clusters()+2):
            f.seek(self.cluster_to_offset(cluster))
            f.write(self.get_clusterdata(cluster))
        
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
                    proc = self.get_clusterdata(cluster)
                    if orig != proc:
                        print("First mismatch in cluster 0x%x at address 0x%x"%\
                              (cluster,self.cluster_to_offset(cluster)))
                        break
            raise S3Exception("test_file failed")
        
    def get_volattr(self,attr):
        cd = self.get_clusterdata(0)
        vl = DirEntry(data=cd[:DirEntry.SIZE])
        if attr == 'name':
            return vl.name().strip()
        else:
            return vl.__getattribute__(attr)

    def get_volname(self):
        name = self.get_volattr('name').strip()
        if not len(name): name = '<empty>'
        return name

    def get_voldate(self):
        return self.get_volattr('mdate')
        
    def get_voltime(self):
        return self.get_volattr('mtime')
        
    def set_volattr(self,attr,value):
        cd = self.get_clusterdata(0)
        vl = DirEntry(data=cd[:DirEntry.SIZE])
        if attr == 'name':
            vl.set_name(value)
        else:
            vl.__setattr__(attr,value)
        self.clusterdata[0] = vl.to_raw() + cd[DirEntry.SIZE:]

    def set_volname(self,name):
        if len(name) > 11:
            print("WARNING: trimming volume name to 11 characters")
            name = name[:11]
        self.set_volattr('name',name)
        
    def set_voldate(self,date=None):
        if date is None: date = str2date(time.strftime("%d/%m/%Y"))
        self.set_volattr('mdate',date)
        
    def set_voltime(self,t=None):
        if t is None: t = str2time(time.strftime("%H:%M:%S"))
        self.set_volattr('mtime',t)

    def set_oemname(self,oemname):
        self.bs.oemname = oemname
        
    def dump_direntry(self,de,indent=0):
        name = de.decodedName().strip()
        if de.is_dir(): name = '[%s]' % name
        print('%s%-14s %8d %s %s  %2x %7d (0x%x)' % (
            indent*' ', name, de.size, time2str(de.mtime), date2str(de.mdate),
            de.attr,de.start,self.cluster_to_offset(de.start)))

    def dump_contents(self,start=0,path='A:',header=True):
        if header:
            print("-"*80)
            empty = self.fat.nempty_clusters(self.ndata_clusters())
            used = self.ndata_clusters()-empty
            print("Volume: %-17s %s %s   %8s B used  %8s B free" % (
                self.get_volname(),
                time2str(self.get_voltime()),
                date2str(self.get_voldate()),
                used*self.bs.cluster_size(),
                empty*self.bs.cluster_size()
            ))
            print("-"*80)
            print("%s %s %s %s %s %s %s" % \
                ("Name".center(16), "Size".center(8), "Time".center(8),
                 "Date".center(10), "Att", "Cluster", "(hex)"))
            print("-"*80)

        dirs,files = self.read_dir(start,no_dotdirs=True)
        print(path)
        empty = True
        for d in dirs:
            self.dump_direntry(d,indent=2)
            empty = False
        for f in files:
            self.dump_direntry(f,indent=2)
            empty = False
        if empty:
            print("  <empty>")
        print()

        for d in dirs:
            if d.is_dotdir(): continue
            self.dump_contents(
                start=d.start, path=path+"\\"+d.decodedName().strip(),
                header=False)
        
    def dump_props(self):
        for i in [
                ('volname', self.get_volname()),
                ('voldate', date2str(self.get_voldate())),
                ('voltime', time2str(self.get_voltime())),
        ]: print("%-20s: %s" % i)
        print()
        self.bs.dump()

    def dump_fat(self):
        self.fat.dump()

    def mkdir(self,path,**kwargs):
        if not (path.startswith("A:\\") or path.startswith("\\")):
            raise S3Exception("mkdir: need absolute path")
        start   = self.check_dirs(path,**kwargs)
        dirs, _ = self.read_dir(start,no_dotdirs=True)
        dirname = path.split('\\')[-1]
        for de in dirs:
            if de.name().strip() == dirname:
                if kwargs.get('errOnExist',False):
                    raise S3Exception("directory already exists")
                else: return
        self.mkdir_real(dirname,start,**kwargs)

    def check_dirs(self,path,**kwargs):
        segments = path.split('\\')[1:]
        start    = 0
        while len(segments) > 1:
            dirs, _ = self.read_dir(start,no_dotdirs=True)
            for de in dirs:
                if de.name().strip() == segments[0]:
                    segments = segments[1:]
                    start    = de.start
                    break
            else:
                if kwargs.get('recursive',True):
                    self.mkdir_real(segments[0],start,**kwargs)
                else:
                    raise S3Exception("subdir %s not found" % segments[0])
        return start

    def mkdir_real(self,name,cluster,**kwargs):
        # actually make directory
        newstart = self.fat.create_chain(1)[0]
        kwargs['attr']  = DirEntry.ATTR_DIR | kwargs.get('attr',0)
        kwargs['start'] = newstart
        kwargs.setdefault('mdate',str2date(time.strftime("%d/%m/%Y")))
        kwargs.setdefault('mtime',str2time(time.strftime("%H:%M:%S")))
        de = DirEntry(**kwargs)
        de.set_name(name)
        self.add_direntry(cluster,de)
        de.set_name('.')
        self.clusterdata[newstart] = de.to_raw()
        de.set_name('..')
        de.start = cluster
        self.clusterdata[newstart] += de.to_raw()

    def copy(self,path,data,**kwargs):
        if not (path.startswith("A:\\") or path.startswith("\\")):
            raise S3Exception("copy: need absolute path")
        start   = self.check_dirs(path,**kwargs)
        dirs, _ = self.read_dir(start,no_dotdirs=True)
        filename = path.split('\\')[-1]
        for de in dirs:
            if de.name().strip() == filename:
                if kwargs.get('errOnExist',True):
                    raise S3Exception("file already exists")
                else: return
        self.copy_real(filename,start,data,**kwargs)

    def copy_real(self,name,cluster,data,**kwargs):
        nclusters = int(len(data)/self.bs.cluster_size()+1)
        # actually make file
        chain = self.fat.create_chain(nclusters)
        kwargs['start'] = chain[0]
        kwargs['size']  = len(data)
        kwargs.setdefault('mdate',str2date(time.strftime("%d/%m/%Y")))
        kwargs.setdefault('mtime',str2time(time.strftime("%H:%M:%S")))
        de = DirEntry(**kwargs)
        de.set_name(name)
        self.add_direntry(cluster,de)
        for i,c in enumerate(chain):
            self.clusterdata[c] = data[i*self.bs.cluster_size():
                                       (i+1)*self.bs.cluster_size()]
        
    def add_direntry(self,cluster,entry):
        if cluster == 0:
            # add new directory to root
            if len(self.get_clusterdata(0))==self.bs.nrootentries*DirEntry.SIZE:
                raise S3Exception("maximum number of root entries reached")
            self.clusterdata[0] = self.get_clusterdata(0) + entry.to_raw()
        else:
            # add new directory to 'normal' directory
            dirchain = self.fat.get_chain(cluster)
            for cluster in dirchain:
                data = self.get_clusterdata(cluster)
                pos = 0
                while pos < self.bs.cluster_size():
                    if not pos < len(data):
                        break
                    if data[pos] != '\0':
                        pos += DirEntry.SIZE
                        continue
                else: continue
                self.clusterdata[cluster] = data + entry.to_raw()
                break
            else:
                cluster = self.fat.extend_chain(cluster)[0]
                self.clusterdata[cluster] = entry.to_raw()
                     
    def read_dir(self,cluster=0,no_dotdirs=False):
        dirs, files = [], []
        data = cStringIO.StringIO(self.get_clusterdata(cluster,throw=True))
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
                if cluster == Fat12.TERM: break
                counter = 0
                data = cStringIO.StringIO(
                    self.get_clusterdata(cluster,throw=True))
            try:    de = DirEntry(data=data)
            except: break
        if no_dotdirs: dirs = [ d for d in dirs if not d.is_dotdir() ]
        return (dirs,files)

    def find_file(self,path):
        path = encode_path(path)
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
            buf += self.get_clusterdata(cluster)
        if f.size > len(buf):
            s = "extract_file: unexpected end of file, %d/%d written" % \
                (len(buf),f.size)
            if compatibilityMode: print("WARNING: "+s)
            else:                 raise S3Exception(s)
        return buf[:f.size]

    def extract_all(self,targetdir,cluster=0,compatibilityMode=False):
        if not os.path.exists(targetdir): os.makedirs(targetdir)
        if cluster == 0:
            os.utime(targetdir,
                     time_conv_to_local(self.get_voldate(),self.get_voltime()))
        dirs, files = self.read_dir(cluster)
        for f in files:
            fname = f.decodedName().strip()
            outname = os.path.join(targetdir,fname)
            try:
                with open(outname,'wb') as outfile:
                    if self.debug: print("Writing '%s'" % outname)
                    outfile.write(self.extract_file(f))
                os.utime(outname, time_conv_to_local(f.mdate,f.mtime))
            except S3Exception, e: raise
            except Exception, e:
                if self.debug: raise
                s = "extract_all: error writing to file %s" % repr(outname)
                if compatibilityMode: print("WARNING: "+s)
                else:                 raise S3Exception(s)
        for d in dirs:
            dirname = d.decodedName().strip()
            if dirname == '.':
                os.utime(targetdir, time_conv_to_local(d.mdate,d.mtime))
                continue
            elif dirname == '..': continue
            self.extract_all(os.path.join(targetdir,dirname),cluster=d.start)

    def add_directory(self,path):
        cut = len(path)
        mdate, mtime = time_conv_from_local(os.path.getmtime(path))
        self.set_voldate(mdate)
        self.set_voltime(mtime)
        for root, dirs, files in os.walk(path):
            newroot = root[cut:].replace('/','\\')
            for orig,dn in [ (d,newroot + '\\' + d) for d in reversed(dirs) ]:
                path  = os.path.join(root,orig)
                mdate, mtime = time_conv_from_local(os.path.getmtime(path))
                if self.debug: print("Adding dir  '%s'" % dn)
                self.mkdir(encode_path(dn),mdate=mdate,mtime=mtime)
            for orig,fn in [ (f,newroot + '\\' + f) for f in reversed(files) ]:
                path = os.path.join(root,orig)
                mdate, mtime = time_conv_from_local(os.path.getmtime(path))
                with open(path,'rb') as f:
                    if self.debug: print("Adding file '%s'" % fn)
                    self.copy(encode_path(fn),f.read(),mdate=mdate,mtime=mtime)
        
