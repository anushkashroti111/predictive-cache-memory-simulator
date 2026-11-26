# Predictive Cache & Memory Access Simulator

A Python simulator that processes web request paths through a custom hash map,
max heap, and frequency/recency predictor. The simulator reports prediction
hits and misses, accuracy, unique paths, elapsed time, and the three highest
priority paths.

## Data source

The real request stream comes from the two configurations of
[`mindweave/web-server-logs`](https://huggingface.co/datasets/mindweave/web-server-logs):

- `access_logs`: each row contributes its `path` as a cache request.
- `servers`: server IDs are loaded and used to validate access-log references.

The public Hugging Face version is a synthetic free sample containing 5,000
access-log rows and 3 server rows. Its dataset card declares CC BY-NC 4.0, so
observe the non-commercial license terms. The full dataset is separately
distributed by its publisher.

Install the runtime dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the access-log simulation (writes one detailed row to
`web_server_logs_results.csv`):

```powershell
python src\main.py --dataset web-server-logs --csv web_server_logs_results.csv
```

To process only the first 1,000 requests:

```powershell
python src\main.py --dataset web-server-logs --limit 1000
```

## Synthetic benchmarks

Running without `--dataset` retains the reproducible random, looping, and
Zipfian benchmarks at 1,000, 50,000, and 500,000 requests each:

```powershell
python src\main.py --csv benchmark_results.csv
```

The output CSV is replaced on each run and contains one row per workload,
including the request count, hit/miss counts, accuracy, latency, unique path
count, and top-three paths.

The historical [fresh benchmark CSV](docs/fresh_benchmark_results.csv) is kept
unchanged. It predates the warm-up correction below; new runs report only
evaluated next-access predictions.

Benchmark the hash map itself against the selected access-log data:

```powershell
python tests\benchmark_cache_map.py --n 5000
```

Compare the baseline and transition policies on identical, seeded sequences
for Random, Looping, and Zipfian workloads at 1,000, 10,000, and 50,000
accesses:

```powershell
python src\main.py --compare-policies --csv docs\policy_comparison_results.csv
```

The comparison CSV records input accesses, unique items, policy, evaluated
predictions, correct/incorrect predictions, hits, misses, accuracy, and
measured runtime. The first valid access is warm-up; each later access is
predicted before it is ingested. Thus an input of N valid accesses has N-1
evaluated predictions; no prediction is scored for an unobserved access after
the final item.

## Tests

```powershell
python -m pytest -q
```

The dataset-loader tests use a small in-memory fixture, so the ordinary test
suite does not require network access or download the Hugging Face dataset.

## Implementation

- `src/cache_map.py`: separate-chaining hash map with FNV-1a hashing.
- `src/priority_heap.py`: max heap ranked by request frequency and recency.
- `src/ingestion.py`: shared request normalization and metadata update pipeline.
- `src/predictor.py`: predicts the current highest-priority path.
- `src/workloads.py`: synthetic workloads and Hugging Face access-log loader.
- `src/main.py`: simulation, benchmark suite, and command-line interface.
- `src/metrics.py`: hit/miss tracking and top-k extraction.
- `src/transition_predictor.py`: separate transition-count prediction policy.

## Prediction algorithms

The **frequency/recency baseline** stores one node per item in the custom
hash table and max heap. Each node tracks its access count and last sequence
number. The heap orders by higher frequency, then newer access, then
lexicographically smaller item for a deterministic final tie-break. At each
prediction opportunity, the heap root is the predicted next item. Its
frequency and recency are updated only after scoring the actual access.

The **transition policy** stores `previous item -> successor -> count` in
nested hash maps. It predicts the most frequently observed successor of the
previous item, breaking ties lexicographically. If no transition is known, it
falls back to the same frequency/recency heap prediction. Both policies use
the same warm-up and scoring opportunities; neither sees the current access
before its prediction is scored.

```text
warm up with first valid access
for each subsequent actual item:
    predict using prior state
    score prediction against actual item
    update frequency/recency state
    record the previous-item -> actual-item transition
```

The core DSA operations follow this outline:

```text
ACCESS(item, sequence):
    node = hash_table.find(item)
    if node is absent:
        node = hash_table.insert(item, frequency=0)
        heap.append(node)
    node.frequency += 1
    node.last_access = sequence
    heap.sift_up(node.heap_index)

TOP_K(k):
    candidates = temporary max-priority queue containing heap.root
    repeat min(k, number of heap items) times:
        best = candidates.remove_max()
        output best
        add best's existing heap children to candidates
```

## Complexity

Let U be the number of unique items, B the number of hash buckets, k the
requested Top-K size, E the number of distinct observed transitions, and d
the number of distinct successors for the current item. Let k be
min(requested Top-K size, U). Complexity assumes constant-time key hashing
and comparison; hashing a URL itself takes O(L) for a URL of length L.

| Operation | Average / amortized time | Worst-case time | Space |
|---|---:|---:|---:|
| Custom hash lookup / insert | O(1) | O(U) from collisions | O(U + B) |
| Hash-table resize | — | O(U + B) | O(U + B) |
| Heap append / sift-up / sift-down | O(1) / O(log U) / O(log U) | O(1) / O(log U) / O(log U) | O(U) |
| Heap priority update (sift-up) | O(log U) | O(log U) | O(1) additional |
| Heap peek / baseline prediction | O(1) | O(1) | O(1) |
| Baseline access update (map + heap) | O(log U) amortized | O(U + log U) | O(1) additional |
| Top-K extraction | O(k log k) | O(k log k) | O(k) |
| Transition count update | O(1) expected | O(E) hash-table worst case | O(E) total |
| Transition prediction / fallback | O(d) / O(1) | O(d) / O(1) | O(1) additional |

The heap does not currently expose extract-maximum or bulk heap construction;
their complexities are therefore not claimed. A full baseline pass is
expected O(N log U), excluding input generation and treating key operations
as constant time. A transition pass adds O(sum(d)) successor-selection work.
Comparing policies buffers the shared input sequence (O(N)) so both receive
identical accesses. Measured processing time excludes workload generation and
Top-K report extraction.

## Team

- Priyanshi Chauhan
- Priyanshi Saini
- Gauri Sharma
- Shivangi Patel
- Anushka Shrotriya
