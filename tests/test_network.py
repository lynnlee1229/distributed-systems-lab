import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.peer_proxy import Policy
class NetworkTests(unittest.TestCase):
    def test_peer_groups_cut_both_directions_and_preserve_majority(self):
        p=Policy();p.configure({'a':0,'b':1,'c':2});p.partition([[0],[1,2]])
        blocked={(s,d) for s in ('a','b','c') for d in range(3) if p.blocked(s,d)}
        self.assertEqual(blocked,{('a',1),('a',2),('b',0),('c',0)})
        self.assertTrue(p.blocked('unrecognized',1));p.partition(None);self.assertFalse(p.blocked('unrecognized',1))
    def test_actual_report_has_independent_controls(self):
        r=json.loads((ROOT/'results/network.json').read_text());self.assertEqual(r['kind'],'real-loopback-peer-partitions');self.assertEqual(len(r['repetitions']),3)
        for x in r['repetitions']:
            self.assertEqual(x['all_processes_alive_during_cut'],[True]*3)
            self.assertEqual(x['majority_write']['outcome'],'ok')
            self.assertEqual(x['isolated_serializable_read'],'before-cut')
            self.assertEqual(x['isolated_linearizable_read']['outcome'],'unknown')
            self.assertEqual(x['healed_values'],['majority-committed']*3)
            self.assertEqual(x['three_singleton_write']['outcome'],'unknown')
            isolated=x['initial_leader']
            self.assertTrue(x['proxy_minority_phase']['cut_connections'])
            self.assertTrue(all((e['from']==isolated)!=(e['to']==isolated) for e in x['proxy_minority_phase']['cut_connections']))
    def test_course_mapping_is_complete_and_does_not_claim_mit_solutions(self):
        r=json.loads((ROOT/'resources/courses.json').read_text());units=json.loads((ROOT/'course.json').read_text())
        self.assertEqual({u['unit'] for u in r['units']},{u['slug'] for u in units})
        self.assertTrue(all(u['materials'] and u['original_practice_command'] for u in r['units']))
        self.assertIn('independent',r['course']['reuse'].lower())
if __name__=='__main__':unittest.main()
