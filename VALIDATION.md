# Validation record

Release date: 2026-11-14 (Asia/Shanghai).

The first-edition baseline runs three complete repetitions of three experiment families using the official digest-verified etcd 3.6.6 darwin/arm64 release, Python 3.11.2 and the v3 JSON gateway. Each cluster has three real processes on one host with independent WAL directories. Raw runtime data is retained locally under ignored build/runs/ and is not part of any export.

Assertions: a pre-crash acknowledged value survives leader SIGKILL; a new leader commits; original-directory restart catches up; one paused follower allows a write; two paused followers yield unknown write/read outcomes within 700 ms; timeout effects and atomic deduplication produce 2/1 counters; four concurrent dedup retries replay; different payload conflicts; an actually paused separate worker resumes after observed lease-key absence; a downstream SQLite fence rejects its lower token after a higher-token write while the plain sink accepts it.

The report keeps every baseline repetition. Its SHA-256 is in results/index.json. Timing is descriptive, not a performance or multi-host claim. The browser checker is a separate finite integer-register model, with an independent unpruned permutation oracle and explicit inconclusive/invalid outcomes. Pending calls are unsupported.

Additional release checks, download reproduction, Linux CI, browser/mobile checks, source visibility and deployment receipts are recorded locally in the author's ops/distributed-systems-lab-release.json. This document does not turn unexecuted extensions into claims: packet partitions, disk destruction, disaster restore, membership change, Byzantine failures and external-system exactly-once effects are not tested.
