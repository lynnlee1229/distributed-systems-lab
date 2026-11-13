"""Bounded loopback peer gates for etcd 3.6.6 plaintext HTTP/1 transport.

Classify first HTTP headers by upstream X-Server-From, then relay bytes.
A cut closes existing TCP streams and rejects reconnects across groups.
This is connection-level partitioning, not arbitrary packet loss or TLS support.
"""
import select,socket,socketserver,threading
from collections import Counter
from .runtime import Cluster

class Policy:
    def __init__(self):
        self.lock=threading.Lock();self.members={};self.groups=None;self.cut=Counter();self.unknown=0;self.connections=Counter()
    def configure(self,members):
        with self.lock:self.members=members
    def partition(self,groups):
        with self.lock:self.groups={i:g for g,group in enumerate(groups) for i in group} if groups else None
    def blocked(self,source,destination):
        with self.lock:
            if self.groups is None:return False
            i=self.members.get(source)
            if i is None:return True
            return self.groups[i]!=self.groups[destination]
    def note(self,source,destination,cut=False):
        with self.lock:
            i=self.members.get(source)
            if i is None:
                if cut:self.unknown+=1
            elif cut:self.cut[(i,destination)]+=1
            else:self.connections[(i,destination)]+=1
    def snapshot(self):
        with self.lock:return {'cut_connections':[{'from':f'n{a+1}','to':f'n{b+1}','count':n} for (a,b),n in sorted(self.cut.items())],
            'observed_peer_connections':[{'from':f'n{a+1}','to':f'n{b+1}','count':n} for (a,b),n in sorted(self.connections.items())],
            'unclassified_connections_rejected':self.unknown}

class PeerGate:
    def __init__(self,destination,backend,policy):
        self.stop=threading.Event();self.limit=threading.BoundedSemaphore(64);self.destination=destination;self.policy=policy
        gate=self
        class Server(socketserver.ThreadingTCPServer):allow_reuse_address=False;daemon_threads=True
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                if not gate.limit.acquire(blocking=False):return
                peer=None;source='';cut=False
                try:
                    self.request.settimeout(3);raw=b''
                    while b'\r\n\r\n' not in raw:
                        part=self.request.recv(4096)
                        if not part:return
                        raw+=part
                        if len(raw)>65536:return
                    header=raw.split(b'\r\n\r\n',1)[0].decode('latin1')
                    for line in header.split('\r\n')[1:]:
                        if line.lower().startswith('x-server-from:'):source=line.split(':',1)[1].strip().lower()
                    if policy.blocked(source,destination):cut=True;return
                    policy.note(source,destination)
                    peer=socket.create_connection(('127.0.0.1',backend),timeout=2);peer.sendall(raw)
                    self.request.settimeout(2);peer.settimeout(2)
                    while not gate.stop.is_set():
                        if policy.blocked(source,destination):cut=True;return
                        readable,_,_=select.select([self.request,peer],[],[],.05)
                        for src in readable:
                            data=src.recv(65536)
                            if not data:return
                            (peer if src is self.request else self.request).sendall(data)
                except OSError:pass
                finally:
                    if cut:policy.note(source,destination,True)
                    if peer:
                        try:peer.shutdown(socket.SHUT_RDWR)
                        except OSError:pass
                        peer.close()
                    try:self.request.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
                    gate.limit.release()
        self.server=Server(('127.0.0.1',0),Handler);self.port=self.server.server_address[1]
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.1},daemon=True);self.thread.start()
    def close(self):self.stop.set();self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)

class GatedCluster(Cluster):
    def __init__(self,folder,binary):
        super().__init__(folder,binary);self.policy=Policy();self.gates=[]
        try:
            self.gates=[PeerGate(i,self.peers[i],self.policy) for i in range(3)]
            self.advertised=[g.port for g in self.gates]
        except BaseException:
            for g in self.gates:g.close()
            raise
    def __exit__(self,*args):
        try:super().__exit__(*args)
        finally:
            for g in self.gates:g.close()
