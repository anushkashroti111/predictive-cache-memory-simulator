# System Testing Report

## Scope

Validated the custom hash map, heap, predictor, ingestion pipeline, simulator,
synthetic workloads, benchmark export, and the selected Hugging Face
web-server-log source.

## Environment and commands

- Windows, Python 3.14.0, pytest
- `python -m pytest -q "D:\tech projects\predictive-cache-memory-simulator\tests"`
- Live dataset runs: first-five smoke test and full 5,000-row sample
- Full synthetic benchmark suite, with CSV row and overwrite validation
- Hash-map benchmark against the first five Hugging Face requests

## Results

- Project test suite: **84 passed**, no skipped tests.
- Live Hugging Face runs loaded both configurations and validated every server
  reference. The full public sample processed 5,000 requests and wrote a
  detailed results row; the five-request smoke test also passed.
- Hash-map benchmark smoke test: processed 5 requests and matched expected
  request counts.
- Synthetic benchmarks: all 9 workload/size combinations completed. The
  output CSV contained exactly 9 unique workload rows, with hit/miss totals
  matching request counts. A second run replaced the CSV without duplicating
  rows.
- Prediction remains before ingestion of the current request. The simulator
  now delegates metadata and heap changes to `IngestionEngine`.

The loader's automated tests use an in-memory fixture, so the standard test
suite remains network-independent. Live checks used the public Hugging Face
sample (5,000 access-log rows and 3 server rows).

## Notes

- The dataset card declares CC BY-NC 4.0; observe its non-commercial terms.
- The public sample is synthetic and is not the separately distributed full
  dataset.
- Timing varies by environment and is not a stable performance baseline.
