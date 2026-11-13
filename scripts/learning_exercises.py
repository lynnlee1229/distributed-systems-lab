#!/usr/bin/env python3
"""Original offline evidence exercises. No MIT assignments or solutions copied."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('unit',choices=['assumptions','recovery']);args=ap.parse_args()
    report=json.loads((ROOT/'results/experiments.json').read_text())
    if args.unit=='assumptions':
        for r in report['repetitions']:
            q=r['quorum'];assert q['two_unreachable_write']['outcome']=='unknown'
            print(json.dumps({'repeat':r['repeat'],'client_observation':'unknown','value_after_recovery':q['unknown_write_after_recovery'],'interpretation':'deadline is not an abort receipt'}))
        print('Challenge: explain why returning not-executed at the deadline would contradict these observations.')
    else:
        network=json.loads((ROOT/'results/network.json').read_text())
        for r in network['repetitions']:
            assert r['healed_values']==['majority-committed']*3
            assert r['isolated_linearizable_read']['outcome']=='unknown'
            assert r['isolated_serializable_read']=='before-cut'
            print(json.dumps({'repeat':r['repeat'],'all_live':r['all_processes_alive_during_cut'],'healed_values':r['healed_values'],'unknown_after_heal':r['isolated_unknown_after_heal']}))
        print('Challenge: distinguish heal/catch-up from backup restore; these records do not destroy disks.')
if __name__=='__main__':main()
