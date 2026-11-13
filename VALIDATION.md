# Validation record

Release date: 2026-11-14 (Asia/Shanghai).

The first-edition baseline runs three complete repetitions of three experiment families using the official digest-verified etcd 3.6.6 darwin/arm64 release, Python 3.11.2 and the v3 JSON gateway. Each cluster has three real processes on one host with independent WAL directories. Raw runtime data is retained locally under ignored build/runs/ and is not part of any export.

Assertions: a pre-crash acknowledged value survives leader SIGKILL; a new leader commits; original-directory restart catches up; one paused follower allows a write; two paused followers yield unknown write/read outcomes within 700 ms; timeout effects and atomic deduplication produce 2/1 counters; four concurrent dedup retries replay; different payload conflicts; an actually paused separate worker resumes after observed lease-key absence; a downstream SQLite fence rejects its lower token after a higher-token write while the plain sink accepts it.

The report keeps every baseline repetition. Its SHA-256 is in results/index.json. Timing is descriptive, not a performance or multi-host claim. The browser checker is a separate finite integer-register model, with an independent unpruned permutation oracle and explicit inconclusive/invalid outcomes. Pending calls are unsupported.

Additional release checks, download reproduction, Linux CI, browser/mobile checks, source visibility and deployment receipts are recorded locally in the author's ops/distributed-systems-lab-release.json. This document does not turn unexecuted extensions into claims: packet partitions, disk destruction, disaster restore, membership change, Byzantine failures and external-system exactly-once effects are not tested.

## Interactive/depth iteration — 2026-11-14

Audited gaps before choosing the next executable loop: (1) process pauses did not test live-node peer partitions; (2) the entry path was text/JSON first; (3) causal and consistency diagrams were not manipulable; (4) the course references did not map units to specific university materials; (5) saved evidence lacked an accessible event-by-event reader. The chosen real mechanism is connection-level peer partitioning. The other changes teach and expose that evidence without replacing the first-edition baselines.

`results/network.json` contains three actually executed repetitions. All three etcd processes remain alive. Owned proxies cut both directions between the original leader and the majority, while preserving majority-to-majority connections. Independent returned values/caller results check majority progress, stale local reads, unknown default reads/writes, healing and a three-singleton control. Proxy counters corroborate scope. No global network setting is touched. This extension tests plaintext HTTP/1 peer connection cuts/rejections; it does not test arbitrary packet-loss distributions or TLS.

Seven browser scenes and seven original conceptual figures are added inside the course and to a dedicated interactive classroom. The live-quorum scene is an ideal atomic replication/election model, not complete Raft. The fencing scene deliberately includes the counterexample in which A reaches the sink before B's higher token. The retry scene shows a fixed illustrative commit time. The evidence replay reads actual saved records and never substitutes generated data on failure. Learner actions, not decorative animation, change the inspected state.

`resources/courses.json` maps every course unit to official MIT 6.5840 Spring 2026 notes/readings/lab descriptions, with verification date, official prerequisites, public-access limits and original runnable exercises. The university's no-public-solutions policy is linked and honored. This companion does not contain its lab skeleton, tests or solutions, and makes no enrollment, grading or certificate promise.
