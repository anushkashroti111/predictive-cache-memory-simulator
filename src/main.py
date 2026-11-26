import argparse
import csv
import json
import time
from typing import Iterable, List, Optional

from cache_map import CustomHashMap, normalize_url
from ingestion import IngestionEngine
from metrics import HitMissTracker, get_top_k
from predictor import CachePredictor
from transition_predictor import TransitionPredictor
from workloads import (
    generate_looping_traffic,
    generate_random_traffic,
    generate_zipfian_traffic,
    load_web_server_log_urls,
)

POLICY_FREQUENCY_RECENCY = "frequency_recency"
POLICY_TRANSITION = "transition"
PREDICTION_POLICIES = (POLICY_FREQUENCY_RECENCY, POLICY_TRANSITION)

BENCHMARK_COLUMNS = [
    "workload",
    "policy",
    "input_accesses",
    "unique_urls",
    "total_steps",
    "evaluated_predictions",
    "correct_predictions",
    "incorrect_predictions",
    "hits",
    "misses",
    "accuracy",
    "latency_ms",
    "top_3_pages",
]


def _write_results_csv(path: str, results: List[dict]) -> None:
    """Replace the CSV with the supplied run results and a stable schema."""
    with open(path, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=BENCHMARK_COLUMNS)
        writer.writeheader()
        for result in results:
            row = dict(result)
            row["top_3_pages"] = json.dumps(row["top_3_pages"])
            writer.writerow(row)


def run_simulation(
    url_stream: Iterable[str],
    workload_name: str = "custom",
    num_buckets: int = CustomHashMap.DEFAULT_BUCKETS,
    csv_output_path: Optional[str] = None,
    policy: str = POLICY_FREQUENCY_RECENCY,
) -> dict:
    if policy not in PREDICTION_POLICIES:
        raise ValueError(f"unknown prediction policy: {policy!r}")

    engine = IngestionEngine(hash_map=CustomHashMap(num_buckets=num_buckets))
    baseline_predictor = CachePredictor(engine.heap)
    transition_predictor = TransitionPredictor()
    tracker = HitMissTracker()
    previous_url = None
    input_accesses = 0

    start_time = time.perf_counter()

    for raw_url in url_stream:
        url = normalize_url(raw_url)
        if url is None:
            continue

        input_accesses += 1
        if previous_url is None:
            engine.process_request(url)
            previous_url = url
            continue

        if policy == POLICY_TRANSITION:
            predicted_url = transition_predictor.predict_next(
                previous_url, fallback=baseline_predictor.predict_next()
            )
        else:
            predicted_url = baseline_predictor.predict_next()
        tracker.record(predicted_url, url)

        # Score before exposing the current access to either prediction policy.
        engine.process_request(url)
        if policy == POLICY_TRANSITION:
            transition_predictor.record_transition(previous_url, url)
        previous_url = url

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    results = {
        "workload": workload_name,
        "policy": policy,
        "input_accesses": input_accesses,
        "unique_urls": len(engine.hash_map),
        "total_steps": tracker.total_steps,
        "evaluated_predictions": tracker.total_steps,
        "correct_predictions": tracker.hits,
        "incorrect_predictions": tracker.misses,
        "hits": tracker.hits,
        "misses": tracker.misses,
        "accuracy": round(tracker.accuracy, 2),
        "latency_ms": round(elapsed_ms, 2),
        "top_3_pages": [n.url for n in get_top_k(engine.heap, 3)],
    }
    if csv_output_path:
        _write_results_csv(csv_output_path, [results])
    return results


def compare_prediction_policies(
    url_stream: Iterable[str],
    workload_name: str = "custom",
    num_buckets: int = CustomHashMap.DEFAULT_BUCKETS,
) -> List[dict]:
    """Run each policy on the same materialized access sequence."""
    accesses = list(url_stream)
    return [
        run_simulation(
            accesses,
            workload_name=workload_name,
            num_buckets=num_buckets,
            policy=policy,
        )
        for policy in PREDICTION_POLICIES
    ]


def run_full_benchmark_suite(output_csv: str = "benchmark_results.csv") -> List[dict]:
    sizes = {
        "small": 1_000,
        "medium": 50_000,
        "large": 500_000,
    }
    generators = {
        "random": generate_random_traffic,
        "looping": generate_looping_traffic,
        "zipfian": generate_zipfian_traffic,
    }

    all_results = []
    for size_label, count in sizes.items():
        for traffic_label, gen_fn in generators.items():
            workload_id = f"{traffic_label}_{size_label}"
            stream = gen_fn(length=count)
            res = run_simulation(
                url_stream=stream,
                workload_name=workload_id,
            )
            all_results.append(res)
            print(
                f"{workload_id:<18} | Steps: {res['total_steps']:<7} | "
                f"Hits: {res['hits']:<7} | Accuracy: {res['accuracy']:>6.2f}% | "
                f"Time: {res['latency_ms']:>8.2f} ms | Top-3: {res['top_3_pages']}"
            )
    _write_results_csv(output_csv, all_results)
    return all_results


def run_policy_comparison_suite(
    output_csv: str = "docs/policy_comparison_results.csv",
) -> List[dict]:
    """Compare both policies across three reproducible workloads and sizes."""
    sizes = (1_000, 10_000, 50_000)
    generators = {
        "random": generate_random_traffic,
        "looping": generate_looping_traffic,
        "zipfian": generate_zipfian_traffic,
    }
    all_results = []
    for workload, generator in generators.items():
        for size in sizes:
            if workload == "looping":
                accesses = generator(length=size)
            else:
                accesses = generator(length=size, seed=42)
            workload_name = f"{workload}_{size}"
            for result in compare_prediction_policies(accesses, workload_name):
                all_results.append(result)
                print(
                    f"{workload_name:<16} | {result['policy']:<17} | "
                    f"Evaluated: {result['evaluated_predictions']:<6} | "
                    f"Hits: {result['hits']:<6} | "
                    f"Accuracy: {result['accuracy']:>6.2f}% | "
                    f"Time: {result['latency_ms']:>8.2f} ms"
                )
    _write_results_csv(output_csv, all_results)
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predictive cache simulator")
    parser.add_argument(
        "--dataset",
        choices=("synthetic", "web-server-logs"),
        default="synthetic",
        help="request source (default: synthetic benchmark suite)",
    )
    parser.add_argument("--limit", type=int, help="maximum access-log rows to process")
    parser.add_argument("--csv", default="benchmark_results.csv", help="results CSV path")
    parser.add_argument(
        "--policy",
        choices=PREDICTION_POLICIES,
        default=POLICY_FREQUENCY_RECENCY,
        help="prediction policy for a single dataset run",
    )
    parser.add_argument(
        "--compare-policies",
        action="store_true",
        help="compare both policies on identical synthetic workloads",
    )
    args = parser.parse_args()

    if args.dataset == "web-server-logs":
        if args.compare_policies:
            parser.error("--compare-policies is only supported with synthetic workloads")
        results = run_simulation(
            load_web_server_log_urls(limit=args.limit),
            workload_name="web-server-logs",
            csv_output_path=args.csv,
            policy=args.policy,
        )
        print(results)
    else:
        if args.limit is not None:
            parser.error("--limit is only supported with --dataset web-server-logs")
        if args.compare_policies:
            run_policy_comparison_suite(output_csv=args.csv)
        elif args.policy != POLICY_FREQUENCY_RECENCY:
            parser.error("--policy is only supported with --dataset web-server-logs")
        else:
            run_full_benchmark_suite(output_csv=args.csv)
