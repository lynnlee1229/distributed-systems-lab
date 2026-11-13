# Distributed Systems Lab

[English course](https://lynnlee1229.github.io/distributed-systems-lab/en/) · [中文课程](https://lynnlee1229.github.io/distributed-systems-lab/zh/) · [中文说明](README.zh-CN.md)

An original seven-chapter course about what remains guaranteed under delayed messages, failed nodes and concurrent operations. Learn failure assumptions; time and causality; consistency; state-machine replication and Raft; unknown RPC outcomes and deduplication; leases and fencing; recovery and evidence. Each chapter includes goals, prerequisites, a worked example, a diagram, practice, interpretation, self-check answers and primary references.

Three executed experiment families use real etcd 3.6.6 processes and actual HTTP requests: leader crash/restart and unavailable voters; commit-before-response timeout with atomic deduplication; expired lease and a resumed stale worker, comparing fenced and unfenced sinks. Three baseline repetitions are retained. A bounded browser-local single-register history checker is explicitly illustrative and separate from real cluster results.

## Reproduce

Python 3.11+, Node.js 18+, Linux/macOS arm64 or amd64; no third-party Python dependencies, Docker, API keys or paid services.

```sh
python3 scripts/install_etcd.py
python3 scripts/run_all.py --repeats 3 --out build/my-results
python3 scripts/run_network.py --repeats 3 --out build/my-network.json
node tests/demo-models.test.mjs
node tests/checker.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
python3 scripts/check_site.py
python3 -m http.server 18915 --directory build/site
```

Open `/distributed-systems-lab/en/` on that server. Downloaded sources run independently. The installer verifies pinned upstream release-asset digests before extracting only named executables. Use `--out results` deliberately to replace the baseline. The site otherwise renders committed results. Linux CI records a separate new run. See the bilingual setup pages in docs/ for details.

## Scope

Three voting processes on **one host**, separate durable directories, loopback HTTP/gRPC gateway. The fault schedule SIGKILLs one owned leader, restarts it from the same directory, and SIGSTOPs one/two followers. This is not a packet-partition, disk-loss, multi-host scaling or Byzantine experiment. A timeout is an unknown result and is reconciled after recovery. No 2PC implementation or external-system exactly-once claim is made.

Retry effects and their durable operation results commit in the same etcd Txn; no operation keys expire in the bounded run. The downstream fencing mark and write are in one SQLite transaction. Fencing rejects older tokens after observing a newer generation; it does not deduplicate equal-token requests or guarantee current ownership before a new generation reaches the sink. Revision-based tokens assume a continuous cluster lineage; restore requires an epoch/revision plan.

The checker handles one integer read/write register, initial 0, completed operations, comparable finite start/end intervals, nonoverlapping operations per client, at most 12 operations and 50,000 search states by default (max 100,000). Models: linearizability or sequential consistency. Exhaustion means fail; a budget/size limit means inconclusive. No pending calls, multi-key transactions, lease model, Byzantine faults or correctness proof of the implementation.

Raw runtime logs and data stay in ignored build/. Publication and the portable ZIP use an explicit file allowlist. Only this standalone learning companion is public; the personal homepage repository is private. Original material is MIT licensed; linked third-party works retain their own terms and are not bundled. Read VALIDATION.md for checks, limitations and release evidence.

## Interactive edition and deeper practice

Start at [the interactive classroom](https://lynnlee1229.github.io/distributed-systems-lab/en/playground.html): missing receipt, causal paths, draggable read/write history, quorum control, retry identity, stale-worker fencing and real evidence replay. Every chapter embeds its own scene, concrete case and original diagram. Browser scenes are explicit teaching models; the evidence replay reads saved real JSON without inventing packet timing.

The new `run_network.py` keeps three etcd processes alive and partitions only owned loopback peer proxies. It cuts existing cross-group TCP streams and rejects reconnects by the pinned transport's X-Server-From header. Direct client ports remain reachable. Three baseline repetitions show a working majority, an isolated stale serializable read versus unknown default read, healed replicas, and a three-singleton no-majority control. See `results/network.json` and the bilingual network guide. This is connection-level partitioning, not arbitrary packet loss or a TLS proxy.

`resources/courses.json` is the verified searchable MIT 6.5840 Spring 2026 map. Seven units link to specific notes/readings/lab descriptions and independent runnable practice. Public reading access is separate from MIT registration, tuition, grading and credit. No MIT assignment solution, skeleton or test harness is copied. Run `python3 scripts/learning_exercises.py assumptions` or `recovery` to examine the baseline evidence; these are original exercises, not course solutions.
