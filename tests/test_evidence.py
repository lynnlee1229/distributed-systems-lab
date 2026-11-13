import hashlib,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab.services import Sink

class EvidenceTests(unittest.TestCase):
    def test_report_integrity_and_mechanisms(self):
        manifest=json.loads((ROOT/'results/index.json').read_text())
        for f in manifest['files']:self.assertEqual(hashlib.sha256((ROOT/'results'/f['file']).read_bytes()).hexdigest(),f['sha256'])
        r=json.loads((ROOT/'results/experiments.json').read_text())
        self.assertEqual(r['kind'],'real-process-experiments');self.assertEqual(r['runtime']['etcd'],'3.6.6')
        self.assertEqual(len(r['repetitions']),3)
        for a in r['repetitions']:
            q=a['quorum'];self.assertNotEqual(q['before']['leader'],q['new_leader']);self.assertEqual(q['wal_restart']['after_crash_value'],'committed')
            self.assertEqual(q['one_unreachable']['outcome'],'ok');self.assertEqual(q['two_unreachable_write']['outcome'],'unknown')
            self.assertEqual(q['two_unreachable_linearizable_read']['outcome'],'unknown')
            for case in a['retry']['cases']:
                self.assertEqual(case['first_client']['outcome'],'unknown');self.assertEqual(case['final_counter'],1 if case['dedup'] else 2)
                self.assertEqual(len(case['commits']),1 if case['dedup'] else 2)
            f=a['fencing'];self.assertGreater(f['B']['token'],f['A']['token']);self.assertFalse(f['A_late_writes']['fenced']['accepted'])
            self.assertEqual(f['A_late_writes']['plain']['stored_value'],'A-late');self.assertEqual(f['A_late_writes']['fenced']['stored_value'],'B-current')
    def test_durable_fence_survives_reopen_and_is_not_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.sqlite';sink=Sink(path)
            self.assertTrue(sink.handle('',{'mode':'fenced','token':8,'value':'B'})['accepted'])
            recovered=Sink(path)
            self.assertFalse(recovered.handle('',{'mode':'fenced','token':7,'value':'A'})['accepted'])
            self.assertTrue(recovered.handle('',{'mode':'fenced','token':8,'value':'B-again'})['accepted'])
            with sqlite3.connect(path) as db:self.assertEqual(db.execute("select token,value from state where mode='fenced'").fetchone(),(8,'B-again'))
    def test_download_allowlist_excludes_private_runtime(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_site.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        names=[str(p.relative_to(ROOT)) for p in m.kit_files()]
        self.assertTrue(all(not n.startswith(('build/','.git/')) for n in names));self.assertIn('lab/runtime.py',names);self.assertIn('results/experiments.json',names)
if __name__=='__main__':unittest.main()
