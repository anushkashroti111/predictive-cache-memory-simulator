# Test Case Results

| Test ID | Test scenario | Preconditions | Test steps | Expected result | Actual result | Status |
|---|---|---|---|---|---|---|
| TC-SIM-001 | System initialization | Source modules importable | Initialize engine, heap, hash map, predictor, and metrics tracker | Structures initialize with no runtime errors | All initialized as expected; empty heap/predictor/metrics valid | PASS |
| TC-SIM-002 | Empty input | Empty iterable | Run integrated simulation | Zero counters and 0.0% accuracy; no crash | 0 steps, 0 hits, 0 misses, 0.0 accuracy | PASS |
| TC-SIM-003 | Single URL | Fresh engine | Process `/HOME` once | Normalized URL, frequency 1, timestamp 1, heap index 0 | `/home` inserted with the expected metadata | PASS |
| TC-SIM-004 | Repeated URL | Fresh engine | Process `/home` 100 times | Frequency 100, timestamp 100, valid root/index | Frequency and timestamp 100; index 0; synchronized | PASS |
| TC-SIM-005 | Multiple unique URLs | Fresh engine | Process 100 unique URLs | 100 map and heap entries; every URL retrievable | 100 entries in both structures; all lookups passed | PASS |
| TC-SIM-006 | Hash collisions | One-bucket hash map | Insert `/a`, `/b`, `/c` | Independent nodes in one chain | Three independent nodes retrieved correctly | PASS |
| TC-SIM-007 | Heap priority | Fresh heap | Insert frequency/timestamp combinations | Frequency and timestamp ordering remain valid | Root and heap property passed | PASS |
| TC-SIM-008 | Prediction | Engine with `/a`, `/b`, `/b` | Predict and snapshot heap | Root URL returned; heap unchanged; empty returns None | `/b` returned; heap unchanged; empty prediction None | PASS |
| TC-SIM-009 | Heap index consistency | Stream `/a`, `/b`, `/c`, `/b`, `/a`, `/a` | Verify indices and swap nodes | Indices match positions; swaps update both nodes | Indices and swap behavior passed | PASS |
| TC-SIM-010 | Random workload | Fixed seed | Generate sizes 0, 1, and 100; compare repeated runs | Valid pool values, exact length, reproducibility | Exact lengths and repeated-seed equality passed | PASS |
| TC-SIM-011 | Looping workload | Pattern `/A`, `/B`, `/C` | Generate 10 requests and empty/invalid inputs | Repeating pattern and boundary handling | Pattern and boundary behavior passed | PASS |
| TC-SIM-012 | Zipfian workload | Fixed seed | Generate 10,000 requests | Exact length and strong popularity skew | 10,000 results; `/home` exceeded `/page49` | PASS |
| TC-SIM-013 | Metrics | Fresh tracker | Record hits and misses | Correct counters and accuracy formula | 2 hits, 2 misses, 50.0% accuracy | PASS |
| TC-SIM-014 | Top-K K=1 and K=0 | Three-node heap | Extract K=1 and K=0 | K=1 returns root; K=0 returns none; heap unchanged | Passed | PASS |
| TC-SIM-015 | Top-K K > heap size | Three-node heap | Request top 100 | Returns all nodes in priority order without mutation | `/a`, `/b`, `/c`; heap unchanged | PASS |
| TC-SIM-016 | 10,000 identical burst | Fresh engine | Process 10,000 `/burst` requests | Correct frequency and heap integrity | Frequency 10,000; heap/map synchronized | PASS |
| TC-SIM-017 | 500,000 mixed stream | Random fixed-seed pool | Process 500,000 requests | Completion, correct counters, valid heap/map | 500,000 accepted; 500 unique entries; passed | PASS |
| TC-SIM-018 | 9 benchmark combinations | 3 workloads x 3 sizes | Run integrated simulation for every combination | Correct steps and formula; no crashes | All 9 passed | PASS |
| TC-UNIT-001 | Existing cache-map unit suite | Python unittest | Run discovery for test_cache_map.py | All cache-map tests pass | Passed in repository-scoped pytest suite | PASS |
| TC-UNIT-002 | Existing ingestion unit suite | Python unittest | Run discovery for test_ingestion.py | All ingestion tests pass | Passed in repository-scoped pytest suite | PASS |
| TC-FULL-001 | Full pytest suite | pytest installed | Run `python -m pytest -q` against the project `tests` folder | All project tests pass | 84 passed, 0 skipped | PASS |
| TC-BENCH-001 | Benchmark CSV validation | Fresh benchmark file | Check 9 rows, uniqueness, counters, formulas | 9 unique valid combinations | 9 rows, formulas and counts valid | PASS |
| TC-BENCH-002 | Hugging Face dataset smoke test | Network and `datasets` dependency | Load both dataset configs and simulate first 5 requests | Five valid requests, metadata cross-reference valid, detailed CSV row | 5 requests processed; output schema and server references valid | PASS |
| TC-BENCH-003 | Benchmark CSV uniqueness | Simulator benchmark suite | Run all 9 workload/size combinations twice to the same CSV | Exactly 9 unique rows after each run; totals and formulas valid | 9 unique rows persisted after both runs; hit/miss totals matched | PASS |
| TC-BENCH-004 | Full Hugging Face sample | Network and `datasets` dependency | Simulate the full public access-log config | 5,000 requests processed; all server references valid; output totals reconcile | 5,000 requests, 33 unique paths, 168 hits, 4,832 misses | PASS |
| TC-DATA-001 | Dataset loader offline tests | Mock `datasets.load_dataset` fixture | Validate config selection, row limit, zero limit, bad server IDs, and invalid limits | Correct paths returned; invalid inputs rejected | All loader fixture cases passed in pytest | PASS |
| TC-BENCH-005 | Metrics CSV overwrite | Two repeated tracker exports to one path | Export the metrics summary twice | Only the latest single row remains | Header plus one latest row | PASS |
