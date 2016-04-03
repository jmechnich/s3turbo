from __future__ import print_function
import sys

def check_cluster(cluster):
    if cluster in [0,1]:
        raise Exception("invalid cluster %d" % cluster)
    return cluster

class Fat12(object):
    def __init__(self,rawdata=b'\xf9\xff\xff',rawsize=None):
        self.from_raw(rawdata,rawsize)
        
    def from_raw(self,rawdata,rawsize=None):
        if not rawsize is None and rawsize > len(rawdata):
            rawdata.ljust(rawsize-len(rawdata),b'\x00')
        if len(rawdata) % 3 != 0:
            raise Exception("raw data size must be multiple of 3")
        data = []
        for i in range(0,len(rawdata),3):
            data.append(ord(rawdata[i]) | (ord(rawdata[i+1])&0xf)<<8)
            data.append(ord(rawdata[i+1]) >> 4 | (ord(rawdata[i+2]) << 4))
        self.data = data
        self.terminator = self.data[1]
        
    def to_raw(self):
        raw = b''
        for i in range(0,len(self.data),2):
            raw += chr(self.data[i] & 0xff)
            raw += chr(self.data[i] >> 8 | (self.data[i+1]&0xf) << 4)
            raw += chr(self.data[i+1] >> 4)
        return raw

    def get(self,cluster):
        if cluster >= len(self.data):
            raise Exception("invalid cluster %d: out of bounds" % cluster)
        return self.data[cluster]

    def next_cluster(self,cluster):
        check_cluster(cluster)
        if cluster == self.terminator:
            raise Exception("end of chain reached")
        if cluster >= len(self.data):
            raise Exception("invalid cluster %d: out of bounds" % cluster)
        return self.data[cluster]
        
    def find_empty_cluster(self,start=0):
        for i, v in enumerate(self.data[start:],start):
            if v == 0: return i
        else: return self.terminator

    def get_chain(self,start):
        chain = [ start ]
        next = check_cluster(self.next_cluster(start))
        while next != self.terminator:
            chain.append(next)
            next = check_cluster(self.next_cluster(next))
        return chain

    def free_chain(self,start):
        next = check_cluster(self.data[start])
        self.data[start] = 0
        while next != self.terminator:
            tmp = check_cluster(self.data[next])
            self.data[next] = 0
            next = tmp

    def create_chain(self,nclusters):
        chain = []
        start = self.find_empty_cluster()
        if start == self.terminator:
            raise Exception("cannnot create chain, all clusters used")
        self.data[start] = self.terminator
        chain.append(start)
        last = start
        next = self.find_empty_cluster()
        print(self.data)
        while len(chain) != nclusters:
            if next == self.terminator:
                raise Exception("cannot extend chain")
            self.data[last] = next
            self.data[next] = self.terminator
            chain.append(next)
            last = next
            next = self.find_empty_cluster()
            print(self.data)
        return chain

    def dump(self,file=sys.stdout):
        for i,v in enumerate(self.data):
            if i%16==0: print('\n0x%03x:' % i,end=" ")
            print('0x%03x' % v,end=" ")
        print()

