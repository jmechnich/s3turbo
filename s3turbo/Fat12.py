from __future__ import print_function
import sys

def _check_cluster(cluster):
    if cluster in [0,1]:
        raise Exception("invalid cluster %d" % cluster)
    return cluster

def _pack(double):
    raw = b''
    raw += chr(double[0] & 0xff)
    raw += chr(double[0] >> 8 | (double[1]&0xf) << 4)
    raw += chr(double[1] >> 4)
    return raw

def _unpack(raw):
    return ((ord(raw[0]) | (ord(raw[1])&0xf)<<8),
            (ord(raw[1]) >> 4 | (ord(raw[2]) << 4)))

class Fat12(object):
    def __init__(self,rawdata=None,rawsize=None):
        if rawdata is None:
            rawdata = _pack((Fat12.FATID,Fat12.TERM))
        self.from_raw(rawdata,rawsize)
        
    def from_raw(self,rawdata,rawsize=None):
        if not rawsize is None and rawsize > len(rawdata):
            rawdata = rawdata.ljust(rawsize-len(rawdata),b'\x00')
        if len(rawdata) % 3 != 0:
            raise Exception("raw data size must be multiple of 3")
        if len(rawdata) < 3:
            raise Exception("raw data size must be at least 3 bytes")
        self.data = []
        for i in range(0,len(rawdata),3):
            self.data += list(_unpack(rawdata[i:i+3]))
        if self.data[0] != Fat12.FATID:
            raise Exception("expected FAT id %x, got %x" %
                            (Fat12.FATID,self.data[0]))
        if self.data[1] != Fat12.TERM:
            raise Exception("expected terminator %x, got %x" %
                            (Fat12.TERM,self.data[1]))
        
    def to_raw(self):
        raw = ''
        for i in range(0,len(self.data),2):
            raw += _pack(self.data[i:i+2])
        return raw

    def get(self,cluster):
        if cluster >= len(self.data):
            raise Exception("invalid cluster %d: out of bounds" % cluster)
        return self.data[cluster]

    def next_cluster(self,cluster):
        _check_cluster(cluster)
        if cluster == Fat12.TERM:
            raise Exception("end of chain reached")
        if cluster >= len(self.data):
            raise Exception("invalid cluster %d: out of bounds" % cluster)
        return self.data[cluster]
        
    def find_empty_cluster(self,start=2,throw=True):
        for i, v in enumerate(self.data[start:],start):
            if v == 0: return i
        else:
            if throw:
                raise Exception("find_empty_cluster: no empty clusters left")
            else:
                return Fat12.TERM

    def nempty_clusters(self,maxsize=None):
        if maxsize is None:
            end = len(self.data)
        else:
            end = maxsize+2
        n=0
        for c in self.data[2:end]:
            if c == 0: n +=1
        return n

    def get_chain(self,start):
        chain = [ start ]
        next = _check_cluster(self.next_cluster(start))
        while next != Fat12.TERM:
            chain.append(next)
            next = _check_cluster(self.next_cluster(next))
        return chain

    def free_chain(self,start):
        next = _check_cluster(self.data[start])
        self.data[start] = 0
        while next != Fat12.TERM:
            tmp = _check_cluster(self.data[next])
            self.data[next] = 0
            next = tmp

    def create_chain(self,nclusters):
        chain = []
        start = self.find_empty_cluster(throw=False)
        if start == Fat12.TERM:
            raise Exception("cannnot create chain, no empty clusters left")
        self.data[start] = Fat12.TERM
        chain.append(start)
        last = start
        next = self.find_empty_cluster(throw=False)
        while len(chain) != nclusters:
            if next == Fat12.TERM:
                raise Exception("cannot extend chain")
            self.data[last] = next
            self.data[next] = Fat12.TERM
            chain.append(next)
            last = next
            next = self.find_empty_cluster(throw=False)
        return chain

    def extend_chain(self,start,nclusters=1):
        oldchain = self.get_chain(start)
        newchain = self.create_chain(nclusters)
        self.data[oldchain[-1]] = newchain[0]
        return newchain
    
    def dump(self,file=sys.stdout):
        for i,v in enumerate(self.data):
            if i%16==0: print('\n0x%03x:' % i,end=" ")
            print('0x%03x' % v,end=" ")
        print()

Fat12.FATID = 0xff9
Fat12.TERM  = 0xfff
