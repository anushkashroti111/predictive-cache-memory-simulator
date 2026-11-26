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

Benchmark the hash map itself against the selected access-log data:

```powershell
python tests\benchmark_cache_map.py --n 5000
```

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

## Team

- Priyanshi Chauhan
- Priyanshi Saini
- Gauri Sharma
- Shivangi Patel
- Anushka Shrotriya
