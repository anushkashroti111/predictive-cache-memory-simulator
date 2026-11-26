# Bug Report and Resolution Status

## DEF-001 - Main entry point duplicated ingestion logic

- **Severity:** Medium
- **File and function:** `src/main.py`, `run_simulation`
- **Description:** The simulator duplicated the ingestion implementation instead of using `IngestionEngine`.
- **Resolution:** `run_simulation()` now calls `IngestionEngine.process_request()` after prediction, preserving predict-before-update ordering.
- **Impact:** Future fixes can diverge between unit-tested ingestion and benchmark/system execution.
- **Status:** Resolved

## DEF-002 - Benchmark results were not exported as a complete run

- **Severity:** Medium
- **File and function:** `src/main.py`, `run_full_benchmark_suite`
- **Description:** Benchmark output was written a row at a time during each run and omitted benchmark details.
- **Resolution:** The suite now writes all 9 results in one replacement operation, using a stable schema with latency, unique paths, and top-three paths.
- **Impact:** A repeatable benchmark baseline was not generated as part of a complete run.
- **Status:** Resolved

## DEF-003 - Real request-log workload was not integrated

- **Severity:** Low
- **File and function:** `src/workloads.py`, `load_web_server_log_urls`
- **Description:** The former optional NASA CSV test did not cover the selected web-server-log dataset.
- **Resolution:** Added a Hugging Face loader using both `servers` and `access_logs` configs, with server-reference and path validation. Replaced the skipped NASA CSV case with offline fixture coverage and verified both a five-request smoke test and the full 5,000-row sample.
- **Status:** Resolved

## DEF-004 - README was outdated relative to implementation

- **Severity:** Low
- **File and function:** `README.md`
- **Description:** The README did not describe the implemented simulator or selected dataset.
- **Resolution:** Documented the Hugging Face configs, dataset license/sample scope, installation, CLI, benchmark, and test commands.
- **Impact:** Users may use incorrect setup or project status information.
- **Status:** Resolved

## DEF-005 - Benchmark export omitted details and could duplicate runs

- **Severity:** Medium
- **File and function:** `src/main.py`, `_write_results_csv` and `run_full_benchmark_suite`; `src/metrics.py`, `HitMissTracker.export_csv`
- **Description:** The benchmark entry point previously appended incomplete rows.
- **Resolution:** Main benchmark output replaces the previous CSV and writes the full eight-column result schema. One-off simulations write one complete row; the standalone metrics exporter replaces its metrics-only CSV rather than appending duplicate runs.
- **Impact:** Benchmark artifacts are difficult to compare and may violate the no-duplicates requirement.
- **Status:** Resolved

## DEF-006 - Prediction metrics counted the no-history warm-up

- **Severity:** Medium
- **File and function:** `src/main.py`, `run_simulation`
- **Description:** The first request was compared with `None` and counted as a miss, so an N-access stream reported N predictions despite having only N-1 next-access opportunities.
- **Resolution:** The first valid item now warms the predictor. Each subsequent actual item is scored against prior state before it is ingested. The final item is not followed by an unobservable prediction.
- **Status:** Resolved

## DEF-007 - Advanced prediction policy and complete tie ordering were missing

- **Severity:** Low
- **File and function:** `src/transition_predictor.py`; `src/priority_heap.py`; `src/metrics.py`
- **Description:** The project had only the frequency/recency predictor and did not define a final ordering for equal-frequency, equal-timestamp heap nodes.
- **Resolution:** Added a separate transition-frequency policy with baseline fallback and lexical successor tie-breaking. Heap and Top-K now use URL order for any remaining tie.
- **Status:** Resolved
