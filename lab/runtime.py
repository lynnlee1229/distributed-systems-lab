"""Owned loopback-only etcd processes; no host network changes."""
import base64, json, os, signal, socket, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def b64(s): return base64.b64encode(str(s).encode()).decode()
def un64(s): return base64.b64decode(s).decode()
def post(url, data, timeout=2):
    req = urllib.request.Request(url, json.dumps(data).encode(), {'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
def wait_until(fn, timeout=15):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            v=fn()
            if v: return v
        except (OSError, ValueError, KeyError): pass
        time.sleep(.1)
    raise TimeoutError('bounded wait expired')
def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]

class Cluster:
    def __init__(self, folder, binary):
        self.folder=Path(folder); self.folder.mkdir(parents=True,exist_ok=True)
        self.binary=str(Path(binary).resolve()); self.ps={}; self.logs=[]; self.paused=set()
        self.clients=[free_port() for _ in range(3)]; self.peers=[free_port() for _ in range(3)]
        if len(set(self.clients+self.peers))!=6: raise RuntimeError('port collision; retry run')
    def start(self,i):
        log=open(self.folder/f'n{i+1}.log','ab'); self.logs.append(log)
        advertised=getattr(self,'advertised',self.peers)
        cluster=','.join(f'n{j+1}=http://127.0.0.1:{p}' for j,p in enumerate(advertised))
        env=os.environ.copy(); env['GOMAXPROCS']='2'; env['GOMEMLIMIT']='128MiB'
        args=[self.binary,'--name',f'n{i+1}','--data-dir',str(self.folder/f'n{i+1}'),
              '--listen-client-urls',f'http://127.0.0.1:{self.clients[i]}',
              '--advertise-client-urls',f'http://127.0.0.1:{self.clients[i]}',
              '--listen-peer-urls',f'http://127.0.0.1:{self.peers[i]}',
              '--initial-advertise-peer-urls',f'http://127.0.0.1:{advertised[i]}',
              '--initial-cluster',cluster,'--initial-cluster-token','synthetic-ds-lab',
              '--heartbeat-interval','100','--election-timeout','1000',
              '--quota-backend-bytes','67108864','--snapshot-count','1000','--log-level','warn']
        self.ps[i]=subprocess.Popen(args,stdout=log,stderr=log,env=env)
    def __enter__(self):
        try:
            for i in range(3): self.start(i)
            wait_until(lambda: len(self.statuses())==3 and self.leader() is not None)
            return self
        except BaseException: self.__exit__(None,None,None); raise
    def api(self,i,path,data,timeout=2): return post(f'http://127.0.0.1:{self.clients[i]}/v3/{path}',data,timeout)
    def status(self,i): return self.api(i,'maintenance/status',{})
    def statuses(self):
        a=[]
        for i in range(3):
            if i in self.paused or self.ps[i].poll() is not None: continue
            try: a.append((i,self.status(i)))
            except OSError: pass
        return a
    def leader(self):
        for i,s in self.statuses():
            if s.get('leader')==s['header']['member_id'] and str(s.get('leader','0'))!='0': return i
    def put(self,i,key,value,timeout=2): return self.api(i,'kv/put',{'key':b64(key),'value':b64(value)},timeout)
    def get(self,i,key,serializable=False,timeout=2):
        r=self.api(i,'kv/range',{'key':b64(key),'serializable':serializable},timeout)
        return r.get('kvs',[None])[0] if r.get('kvs') else None
    def pause(self,i): os.kill(self.ps[i].pid,signal.SIGSTOP); self.paused.add(i)
    def resume(self,i): os.kill(self.ps[i].pid,signal.SIGCONT); self.paused.remove(i)
    def crash(self,i): self.ps[i].kill(); self.ps[i].wait(timeout=5)
    def __exit__(self,*args):
        for i,p in self.ps.items():
            if p.poll() is None:
                if i in self.paused: os.kill(p.pid,signal.SIGCONT)
                p.terminate()
        for p in self.ps.values():
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
        for f in self.logs: f.close()
