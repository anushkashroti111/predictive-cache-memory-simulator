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
