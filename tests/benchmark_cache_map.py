"""
Efficiency check for the Hash Map Layer
Feeds the first N requests from the Hugging Face access logs into
CustomHashMap and reports time, memory, and bucket-chain statistics.
"""

import argparse
import csv
import os
import sys
import time
import tracemalloc
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cache_map import CustomHashMap  # noqa: E402
from workloads import load_web_server_log_urls  # noqa: E402


def run_stream(urls):
    """Push every URL through the map exactly as the pipeline will."""
    cache_map = CustomHashMap()
    for tick, url in enumerate(urls, start=1):
        if cache_map.get(url) is None:
            cache_map.insert(url)
        cache_map.update_access(url, tick)
    return cache_map


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CustomHashMap on Hugging Face web-server logs"
    )
    parser.add_argument("--n", type=int, default=5000, help="maximum requests (default 5000)")
    parser.add_argument("--csv", help="optional file to save the results to")
    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n must be a positive integer")
    urls = list(load_web_server_log_urls(limit=args.n))
    print(f"Loaded {len(urls):,} requests")

    # Pass 1: timing only (tracemalloc would slow it down)
    start = time.perf_counter()
    cache_map = run_stream(urls)
    elapsed = time.perf_counter() - start

    # Pass 2: peak memory
    del cache_map
    tracemalloc.start()
    cache_map = run_stream(urls)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Correctness check against Counter (checking only, never inside the map)
    expected = Counter(urls)
    correct = (len(cache_map) == len(expected) and
               all(cache_map.get(u).frequency == c for u, c in expected.items()))

    stats = cache_map.stats()
    results = {
        "requests": len(urls),
        "unique_urls": stats["unique_urls"],
        "buckets": stats["buckets"],
        "avg_chain_length": round(stats["avg_chain"], 2),
        "max_chain_length": stats["max_chain"],
        "empty_buckets": stats["empty_buckets"],
        "time_seconds": round(elapsed, 3),
        "microseconds_per_request": round(elapsed / len(urls) * 1e6, 2),
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
        "counts_match_counter": correct,
    }
    for key, value in results.items():
        print(f"{key:>26}: {value}")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(results.keys())
            writer.writerow(results.values())
        print(f"Saved to {args.csv}")

    if not correct:
        sys.exit("MISMATCH: map counts differ from Counter")


if __name__ == "__main__":
    main()
