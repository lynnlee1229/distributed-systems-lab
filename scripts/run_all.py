#!/usr/bin/env python3
import argparse,concurrent.futures,hashlib,json,os,platform,signal,subprocess,sys,tempfile,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.runtime import Cluster,b64,un64,post,wait_until
from lab.services import Counter,Service,Sink

def observed(fn):
    start=time.monotonic()
    try:
        r=fn(); return {'outcome':'ok','duration_ms':round((time.monotonic()-start)*1000,3),'response':r}
    except (OSError,TimeoutError):
        return {'outcome':'unknown','duration_ms':round((time.monotonic()-start)*1000,3)}
def value(c,i,key):
    r=c.get(i,key);return un64(r['value']) if r else None

def quorum(c):
    key='/lab/quorum';leader=wait_until(lambda:[c.leader()] if c.leader() is not None else None)[0]
    # leader index zero is a valid return; use explicit wrapper elsewhere.
    r=c.put(leader,key,'acknowledged-before-crash')
    before={'leader':f'n{leader+1}','revision':int(r['header']['revision']),'term':int(r['header']['raft_term'])}
    c.crash(leader)
    survivor=next(i for i in range(3) if i!=leader)
    wait_until(lambda: c.leader() is not None and c.leader()!=leader)
    after=c.leader();assert after!=leader
    preserved=value(c,after,key);assert preserved=='acknowledged-before-crash'
    failover=observed(lambda:c.put(after,'/lab/after-crash','committed'))
    assert failover['outcome']=='ok'
    c.start(leader)
    wait_until(lambda:value(c,leader,'/lab/after-crash')=='committed')
    recovered={'node':f'n{leader+1}','value':value(c,leader,key),'after_crash_value':value(c,leader,'/lab/after-crash')}
    lead=c.leader();follower=next(i for i in range(3) if i!=lead)
    c.pause(follower)
    minority=observed(lambda:c.put(lead,'/lab/one-unreachable','committed'))
    assert minority['outcome']=='ok';c.resume(follower)
    wait_until(lambda:value(c,follower,'/lab/one-unreachable')=='committed')
    lead=c.leader();others=[i for i in range(3) if i!=lead]
    for i in others:c.pause(i)
    time.sleep(1.4) # exceeds configured election timeout; not a detection proof.
    noquorum=observed(lambda:c.put(lead,'/lab/unknown','maybe-committed',timeout=.7))
    read=observed(lambda:c.get(lead,key,timeout=.7))
    assert noquorum['outcome']=='unknown' and read['outcome']=='unknown'
    for i in others:c.resume(i)
    wait_until(lambda:c.leader() is not None)
    wait_until(lambda:value(c,c.leader(),key)=='acknowledged-before-crash')
    reconciliation=value(c,c.leader(),'/lab/unknown')
    return {'before':before,'new_leader':f'n{after+1}','committed_write_survived':preserved,
            'failover_write':failover,'wal_restart':recovered,'one_unreachable':minority,
            'two_unreachable_write':noquorum,'two_unreachable_linearizable_read':read,
            'unknown_write_after_recovery':reconciliation,
            'conditions':{'nodes':3,'quorum':2,'faults':['leader SIGKILL and same-data-dir restart','one follower SIGSTOP','two followers SIGSTOP'],
                          'election_timeout_ms':1000,'client_deadline_ms':700},
            'assertions_passed':True}

def retry(c,run):
    cases=[];node=c.leader()
    for guarded in (False,True):
        handler=Counter(c,node,f'/lab/retry/{run}/{guarded}');server=Service(handler.handle)
        try:
            d={'id':'synthetic-op-1','amount':1,'dedup':guarded,'response_delay_ms':800}
            first=observed(lambda:post(server.url+'/increment',d,timeout=.15))
            assert first['outcome']=='unknown'
            wait_until(lambda:len(handler.events)==1)
            commits_at_timeout=list(handler.events)
            second=post(server.url+'/increment',{**d,'response_delay_ms':0})
            final=int(value(c,node,handler.prefix+'/counter'))
            assert final==(1 if guarded else 2)
            extra={}
            if guarded:
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    replies=list(pool.map(lambda _:post(server.url+'/increment',{**d,'response_delay_ms':0}),range(4)))
                conflict=post(server.url+'/increment',{**d,'amount':9,'response_delay_ms':0})
                assert all(x['replayed'] for x in replies) and conflict=={'error':'id-conflict'}
                extra={'concurrent_retries':replies,'changed_payload':conflict}
            cases.append({'dedup':guarded,'first_client':first,'commits_before_delayed_response':commits_at_timeout,
                          'retry_response':second,'final_counter':final,'commits':handler.events,**extra})
        finally: server.close()
    return {'conditions':{'response_delay_after_commit_ms':800,'client_deadline_ms':150,
                          'effect':'etcd CAS counter plus durable operation-result key in one Txn',
                          'dedup_retention':'no expiry in this bounded experiment'},'cases':cases,'assertions_passed':True}

def fencing(c,folder):
    node=c.leader();lock='/lab/lease/lock'
    def acquire(owner):
        grant=c.api(node,'lease/grant',{'TTL':'2'});lease=grant['ID']
        assert int(grant['TTL'])>=2
        r=c.api(node,'kv/txn',{'compare':[{'target':'VERSION','key':b64(lock),'version':'0','result':'EQUAL'}],
              'success':[{'request_put':{'key':b64(lock),'value':b64(owner),'lease':lease}}]})
        assert r.get('succeeded');stored=c.get(node,lock)
        return {'owner':owner,'token':int(stored['create_revision']),'lease':lease,'requested_ttl_seconds':2,'granted_ttl_seconds':int(grant['TTL'])}
    sink=Sink(folder/'sink.sqlite');service=Service(sink.handle);worker=None
    try:
        a=acquire('A');worker=subprocess.Popen([sys.executable,'-m','lab.worker'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        assert worker.stdout.readline().strip()=='ready'
        os.kill(worker.pid,signal.SIGSTOP)
        start=time.monotonic();wait_until(lambda:c.get(node,lock) is None,timeout=12)
        expired_ms=round((time.monotonic()-start)*1000,3)
        b=acquire('B');assert b['token']>a['token']
        fresh={mode:post(service.url+'/write',{'mode':mode,'token':b['token'],'value':'B-current'}) for mode in ('plain','fenced')}
        os.kill(worker.pid,signal.SIGCONT)
        out,err=worker.communicate(json.dumps({'url':service.url,'token':a['token']})+'\n',timeout=5)
        assert worker.returncode==0,err
        late=json.loads(out);assert late['plain']['stored_value']=='A-late' and not late['fenced']['accepted'] and late['fenced']['stored_value']=='B-current'
        c.api(node,'lease/revoke',{'ID':b['lease']})
        return {'conditions':{'fault':'SIGSTOP owned worker A; no lease keepalive','sink':'HTTP plus SQLite BEGIN IMMEDIATE; token check and write atomic'},
                'A':a,'B':b,'observed_key_absence_after_ms':expired_ms,'B_writes':fresh,'A_late_writes':late,'assertions_passed':True}
    finally:
        if worker and worker.poll() is None:
            os.kill(worker.pid,signal.SIGCONT);worker.kill();worker.wait()
        service.close()

def main():
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(143))
    ap=argparse.ArgumentParser();ap.add_argument('--repeats',type=int,default=3);ap.add_argument('--out',default='results');ap.add_argument('--etcd',default='build/runtime/etcd');args=ap.parse_args()
    if not 1<=args.repeats<=10:raise SystemExit('repeats must be 1..10')
    binary=(ROOT/args.etcd).resolve();version=subprocess.check_output([str(binary),'--version'],text=True)
    assert 'etcd Version: 3.6.6' in version
    # Shared machine budget lock when running in the user's Lab workspace; local lock for downloads/CI.
    shared=ROOT.parents[1]/'ops';lock=(shared if shared.is_dir() else ROOT/'build')/'lab-heavy-runtime.lock'
    lock.parent.mkdir(parents=True,exist_ok=True);owner=str(uuid.uuid4())
    try:lock.mkdir()
    except FileExistsError:raise SystemExit('Another owned workload holds the heavy-runtime lock; retry later. Never remove it by age.')
    (lock/'owner.json').write_text(json.dumps({'lab':'distributed-systems-lab','chat':'Distributed Systems Lab','owner':owner,'time':datetime.now(timezone.utc).isoformat()}))
    out=ROOT/args.out;out.mkdir(parents=True,exist_ok=True)
    raw=ROOT/'build/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');raw.mkdir(parents=True)
    records=[]
    try:
        for i in range(args.repeats):
            folder=raw/f'repeat-{i+1}';print(f'Real experiment repetition {i+1}/{args.repeats}',flush=True)
            with Cluster(folder,binary) as c:
                # leader() may return zero: use a truthy envelope for the initial readiness wait.
                wait_until(lambda:[c.leader()] if c.leader() is not None else None)
                q=quorum(c);r=retry(c,i);f=fencing(c,folder)
                records.append({'repeat':i+1,'quorum':q,'retry':r,'fencing':f})
                (raw/f'repeat-{i+1}.json').write_text(json.dumps(records[-1],indent=2))
        report={'schema':1,'kind':'real-process-experiments','recorded_at':datetime.now(timezone.utc).isoformat(),
                'runtime':{'etcd':'3.6.6','platform':platform.system()+' '+platform.machine(),'python':platform.python_version(),
                           'topology':'three loopback etcd processes on one host; independent WAL directories',
                           'transport':'etcd v3 JSON gRPC gateway; HTTP application endpoints',
                           'resource_bounds':'GOMAXPROCS=2, GOMEMLIMIT=128MiB per etcd (soft GC target), 64MiB backend quota'},
                'limitations':['not a multi-host availability or performance benchmark','process crash/pause, not packet partition or disk corruption',
                               'timeouts are unknown outcomes; post-recovery reconciliation is recorded','fencing checks freshness only after the sink has observed the newer token',
                               'no authentication or TLS; loopback synthetic learning runtime only'],
                'repetitions':records}
        target=out/'experiments.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (out/'index.json').write_text(json.dumps({'schema':1,'files':[{'file':'experiments.json','sha256':hashlib.sha256(target.read_bytes()).hexdigest()}]},indent=2)+'\n')
        print('All experiment assertions passed; sanitized results exported.',flush=True)
    finally:
        current=json.loads((lock/'owner.json').read_text())
        if current['owner']==owner:(lock/'owner.json').unlink();lock.rmdir()
if __name__=='__main__':main()
