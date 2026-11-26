import argparse
import csv
import json
import time
from typing import Iterable, List, Optional

from cache_map import CustomHashMap, normalize_url
from ingestion import IngestionEngine
from metrics import HitMissTracker, get_top_k
from predictor import CachePredictor
from workloads import (
    generate_looping_traffic,
    generate_random_traffic,
    generate_zipfian_traffic,
    load_web_server_log_urls,
)


BENCHMARK_COLUMNS = [
    "workload",
    "total_steps",
    "hits",
    "misses",
    "accuracy",
    "latency_ms",
    "unique_urls",
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
) -> dict:
    engine = IngestionEngine(hash_map=CustomHashMap(num_buckets=num_buckets))
    predictor = CachePredictor(engine.heap)
    tracker = HitMissTracker()

    start_time = time.perf_counter()

    for raw_url in url_stream:
        url = normalize_url(raw_url)
        if url is None:
            continue

        # 1. Predict BEFORE processing current request at step T
        predicted_url = predictor.predict_next()
        tracker.record(predicted_url, url)

        # IngestionEngine owns map, frequency, timestamp, and heap updates.
        engine.process_request(url)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    results = tracker.summary()
    results["workload"] = workload_name
    results["unique_urls"] = len(engine.hash_map)
    results["latency_ms"] = round(elapsed_ms, 2)
    results["top_3_pages"] = [n.url for n in get_top_k(engine.heap, 3)]
    if csv_output_path:
        _write_results_csv(csv_output_path, [results])
    return results


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
    args = parser.parse_args()

    if args.dataset == "web-server-logs":
        results = run_simulation(
            load_web_server_log_urls(limit=args.limit),
            workload_name="web-server-logs",
            csv_output_path=args.csv,
        )
        print(results)
    else:
        if args.limit is not None:
            parser.error("--limit is only supported with --dataset web-server-logs")
        run_full_benchmark_suite(output_csv=args.csv)
