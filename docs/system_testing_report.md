# System Testing and Experimental Analysis

## Audit of existing implementation

- The custom separate-chaining hash table stores one node per normalized URL;
  the custom max heap orders nodes by frequency and recency.
- The ingestion engine updates frequency, sequence timestamp, and heap index.
  Top-K uses a temporary candidate heap and leaves the source heap unchanged.
- Random, looping, and Zipfian generators are seeded/reproducible where
  applicable. Existing archived results cover 1,000, 50,000, and 500,000
  accesses, but only the baseline policy.
- The previous evaluation counted the first access as a miss despite having no
  history, producing N scored items for N accesses. Evaluation now warms up on
  the first valid access and scores the following N-1 accesses before updating
  state. There is no future-access leakage.
- The original `docs/fresh_benchmark_results.csv` was preserved unchanged. Its
  totals reflect the older warm-up convention; use the new policy comparison
  CSV for corrected evaluation.
- Before these focused updates, the repository had recorded 84 passing tests.
  The full suite was not rerun, per the request to rely on existing system
  test evidence and run targeted checks only.

## Policy comparison

`docs/policy_comparison_results.csv` contains 18 measured rows: both policies
on the same seeded Random, Looping, and Zipfian sequences at 1,000, 10,000,
and 50,000 accesses. Every pair has equal input and evaluation counts; invalid
paths are ignored, the first valid path is warm-up, and all later predictions
are scored before ingesting the actual path.

Observations:

- **Looping:** transition prediction reaches 99.70%, 99.97%, and 99.99%;
  the global frequency/recency policy remains at 0%. Remembered successors
  capture the repeated cycle after initial warm-up.
- **Random:** both policies are near 2%; the transition policy improves the
  measured result slightly but cannot infer a stable next item from random
  traffic.
- **Zipfian:** frequency/recency is better (34.83%-36.55%) than transitions
  (32.83%-36.43%). Strong global popularity is a better signal than previous
  item context for this generated workload.
- Transition tracking adds runtime and memory overhead. The single-run timing
  values are environment-sensitive; the accuracy counts are deterministic.

## Targeted post-change validation

- **19 focused pytest cases passed**, covering all nine baseline workload/size
  cases, warm-up and N-1 accounting, deterministic heap/Top-K ties, transition
  tie/fallback behavior, repeated-loop prediction, identical comparison
  opportunities, and CSV output.
- Modified Python modules passed `py_compile`.
- The comparison CSV has 18 rows (nine workload/size pairs x two policies),
  with correct + incorrect = evaluated predictions and hits + misses equal
  evaluated predictions for every row.
- Dataset loader, hash table, ingestion, and broader system behavior retain
  the previously recorded full-suite evidence; they were not redundantly
  rerun.
- A post-correction live Hugging Face run processed 5,000 inputs as 4,999
  evaluations: 168 correct, 4,831 incorrect (3.36%).

## Scope and limitations

- The transition policy is a deterministic transition-frequency data
  structure, not machine learning. Unseen contexts fall back to the assigned
  frequency/recency heap policy.
- Only the previous item is used as transition context. No HTTP status,
  timestamp, or server feature is used to predict.
- Synthetic sequence generation is excluded from reported processing time;
  Top-K extraction is also excluded.
