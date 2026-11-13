#!/usr/bin/env python3
"""Actual live-process peer partitions; assertions are independent of gate counters."""
import argparse,hashlib,json,platform,signal,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.peer_proxy import GatedCluster
from lab.runtime import wait_until,un64
from scripts.run_all import observed

def getval(c,i,key,serializable=False):
    r=c.get(i,key,serializable=serializable,timeout=1);return un64(r['value']) if r else None

def experiment(folder,binary):
    with GatedCluster(folder,binary) as c:
        states=c.statuses();members={format(int(s['header']['member_id']),'x'):i for i,s in states};assert len(members)==3;c.policy.configure(members)
        c.put(c.leader(),'/lab/network/value','before-cut');wait_until(lambda:all(getval(c,i,'/lab/network/value')=='before-cut' for i in range(3)))
        old=c.leader();majority=[i for i in range(3) if i!=old]
        c.policy.partition([[old],majority]);time.sleep(1.5)
        def newleader():
            for i in majority:
                s=c.status(i)
                if s.get('leader')==s['header']['member_id'] and int(s.get('leader','0')):return [i]
        leader=wait_until(newleader)[0]
        # Independent oracle: caller success + values, not the proxy's configured partition.
        majority_write=observed(lambda:c.put(leader,'/lab/network/value','majority-committed'))
        assert majority_write['outcome']=='ok'
        stale=getval(c,old,'/lab/network/value',True);assert stale=='before-cut'
        isolated_read=observed(lambda:c.get(old,'/lab/network/value',timeout=.6))
        isolated_write=observed(lambda:c.put(old,'/lab/network/isolated','unknown-intent',timeout=.6))
        assert isolated_read['outcome']=='unknown' and isolated_write['outcome']=='unknown'
        live_during_cut=[c.ps[i].poll() is None for i in range(3)];assert all(live_during_cut)
        cut_evidence=c.policy.snapshot();assert cut_evidence['cut_connections']
        # No edge between majority voters may have been cut in this phase.
        assert all((int(x['from'][1:])-1==old)!=(int(x['to'][1:])-1==old) for x in cut_evidence['cut_connections'])
        c.policy.partition(None)
        wait_until(lambda:all(getval(c,i,'/lab/network/value')=='majority-committed' for i in range(3)))
        healed=[getval(c,i,'/lab/network/value') for i in range(3)]
        unknown_after_heal=getval(c,leader,'/lab/network/isolated')
        # Control: same three live processes, now every voter separated.
        c.policy.partition([[0],[1],[2]]);time.sleep(1.5)
        no_majority=observed(lambda:c.put(leader,'/lab/network/no-majority','unknown',timeout=.6))
        assert no_majority['outcome']=='unknown';all_live=[c.ps[i].poll() is None for i in range(3)];assert all(all_live)
        c.policy.partition(None)
        wait_until(lambda:c.leader() is not None)
        after=wait_until(lambda:getval(c,c.leader(),'/lab/network/value')=='majority-committed')
        return {'initial_leader':f'n{old+1}','majority_leader':f'n{leader+1}','groups_during_minority_cut':[[f'n{old+1}'],[f'n{i+1}' for i in majority]],
                'majority_write':majority_write,'isolated_serializable_read':stale,'isolated_linearizable_read':isolated_read,'isolated_write':isolated_write,
                'all_processes_alive_during_cut':live_during_cut,'proxy_minority_phase':cut_evidence,'healed_values':healed,'isolated_unknown_after_heal':unknown_after_heal,
                'three_singleton_write':no_majority,'all_processes_alive_during_singletons':all_live,'final_acknowledged_value_preserved':after,'assertions_passed':True}

def main():
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(143));ap=argparse.ArgumentParser();ap.add_argument('--repeats',type=int,default=3);ap.add_argument('--out',default='results/network.json');args=ap.parse_args()
    if not 1<=args.repeats<=5:raise SystemExit('repeats must be 1..5')
    binary=ROOT/'build/runtime/etcd';version=subprocess.check_output([str(binary),'--version'],text=True);assert 'etcd Version: 3.6.6' in version
    shared=ROOT.parents[1]/'ops';lock=(shared if shared.is_dir() else ROOT/'build')/'lab-heavy-runtime.lock';owner=str(uuid.uuid4())
    try:lock.mkdir()
    except FileExistsError:raise SystemExit('Shared runtime busy; never remove another owner lock')
    (lock/'owner.json').write_text(json.dumps({'lab':'distributed-systems-lab-network','chat':'Distributed Systems Lab depth iteration','owner':owner,'time':datetime.now(timezone.utc).isoformat()}))
    try:
        raw=ROOT/'build/network-runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');raw.mkdir(parents=True)
        repetitions=[]
        for i in range(args.repeats):
            print(f'Real proxy partition {i+1}/{args.repeats}',flush=True);r=experiment(raw/f'repeat-{i+1}',binary);r['repeat']=i+1;repetitions.append(r);(raw/f'repeat-{i+1}.json').write_text(json.dumps(r,indent=2))
        report={'schema':1,'kind':'real-loopback-peer-partitions','recorded_at':datetime.now(timezone.utc).isoformat(),'runtime':{'etcd':'3.6.6','platform':platform.system()+' '+platform.machine(),'python':platform.python_version()},
                'method':'Three live etcd voters; owned plaintext HTTP/1 TCP peer proxies classify X-Server-From; cut existing cross-group connections and reject reconnects; direct client ports remain reachable.',
                'independent_oracle':'Majority write success and exact returned values; stale serializable read versus unknown linearizable read; all subprocesses remain alive; healed replicas agree. Proxy counters corroborate scope, not correctness.',
                'limits':['single host, synthetic data','connection close/reject, not arbitrary packet loss, latency distribution or TLS','not a full Raft implementation or production network chaos matrix','timed-out writes remain unknown and may apply after healing'], 'repetitions':repetitions}
        target=ROOT/args.out;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2)+'\n');print('PASS: actual peer cuts, stale/default read contrast, majority/no-majority control and healing.',flush=True)
    finally:
        if json.loads((lock/'owner.json').read_text())['owner']==owner:(lock/'owner.json').unlink();lock.rmdir()
if __name__=='__main__':main()
