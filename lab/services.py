"""Real HTTP endpoints with an explicit commit-before-response fault."""
import json, sqlite3, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .runtime import post,b64,un64

class Service:
    def __init__(self,handler):
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result=handler(self.path,body)
                delay=body.get('response_delay_ms',0)
                if delay: time.sleep(delay/1000)
                raw=json.dumps(result).encode()
                try:
                    self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
                except (BrokenPipeError,ConnectionResetError): pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),H)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def close(self): self.server.shutdown(); self.server.server_close(); self.thread.join()

class Counter:
    def __init__(self,cluster,node,prefix): self.c=cluster; self.node=node; self.prefix=prefix; self.events=[]; self.lock=threading.Lock()
    def handle(self,path,d):
        key=self.prefix+'/counter'; dedup=self.prefix+'/op/'+d['id']; guarded=d['dedup']
        for _ in range(100):
            old=self.c.get(self.node,key); seen=self.c.get(self.node,dedup) if guarded else None
            if seen:
                result=json.loads(un64(seen['value']))
                if result['amount']!=d['amount']: return {'error':'id-conflict'}
                return {**result,'replayed':True}
            n=(int(un64(old['value'])) if old else 0)+d['amount']
            result={'amount':d['amount'],'value':n}
            compare=[{'key':b64(key),'target':'MOD','mod_revision':old['mod_revision'] if old else '0','result':'EQUAL'}]
            writes=[{'request_put':{'key':b64(key),'value':b64(n)}}]
            if guarded:
                compare.append({'key':b64(dedup),'target':'VERSION','version':'0','result':'EQUAL'})
                writes.append({'request_put':{'key':b64(dedup),'value':b64(json.dumps(result))}})
            r=self.c.api(self.node,'kv/txn',{'compare':compare,'success':writes})
            if r.get('succeeded'):
                with self.lock: self.events.append({'kind':'commit','id':d['id'],'value':n,'revision':int(r['header']['revision'])})
                return {**result,'replayed':False}
        raise RuntimeError('CAS retry limit reached')

class Sink:
    """Durable token check and data write in the same SQLite transaction."""
    def __init__(self,path):
        self.path=str(path)
        with sqlite3.connect(self.path) as db:
            db.execute('create table if not exists state (mode text primary key, token integer, value text)')
            db.executemany('insert or ignore into state values (?,0,?)',[('plain','initial'),('fenced','initial')])
    def handle(self,path,d):
        with sqlite3.connect(self.path,timeout=5) as db:
            db.execute('begin immediate')
            token,value=db.execute('select token,value from state where mode=?',(d['mode'],)).fetchone()
            accepted=d['mode']=='plain' or d['token']>=token
            if accepted:
                token,value=d['token'],d['value']; db.execute('update state set token=?,value=? where mode=?',(token,value,d['mode']))
            return {'accepted':accepted,'stored_token':token,'stored_value':value}
