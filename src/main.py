import time
from typing import Iterable, List, Optional

from cache_map import CustomHashMap, normalize_url
from metrics import HitMissTracker, get_top_k
from predictor import CachePredictor
from priority_heap import MaxHeap
from workloads import (
    generate_looping_traffic,
    generate_random_traffic,
    generate_zipfian_traffic,
)


def run_simulation(
    url_stream: Iterable[str],
    workload_name: str = "custom",
    num_buckets: int = CustomHashMap.DEFAULT_BUCKETS,
    csv_output_path: Optional[str] = None,
) -> dict:
    heap = MaxHeap()
    cache_map = CustomHashMap(num_buckets=num_buckets)
    predictor = CachePredictor(heap)
    tracker = HitMissTracker()

    sequence_tick = 0
    start_time = time.perf_counter()

    for raw_url in url_stream:
        url = normalize_url(raw_url)
        if url is None:
            continue

        sequence_tick += 1

        # 1. Predict BEFORE processing current request at step T
        predicted_url = predictor.predict_next()
        tracker.record(predicted_url, url)

        # 2. Insert/update metadata in Hash Map
        node = cache_map.insert(url)
        cache_map.update_access(url, sequence_tick)

        # 3. Insert into MaxHeap if new, then restore max-heap property
        if node.heap_index == -1:
            heap.raw_insert(node)
        heap.sift_up(node.heap_index)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    if csv_output_path:
        tracker.export_csv(csv_output_path, workload=workload_name)

    results = tracker.summary()
    results["workload"] = workload_name
    results["unique_urls"] = len(cache_map)
    results["latency_ms"] = round(elapsed_ms, 2)
    results["top_3_pages"] = [n.url for n in get_top_k(heap, 3)]
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
                csv_output_path=output_csv,
            )
            all_results.append(res)
            print(
                f"{workload_id:<18} | Steps: {res['total_steps']:<7} | "
                f"Hits: {res['hits']:<7} | Accuracy: {res['accuracy']:>6.2f}% | "
                f"Time: {res['latency_ms']:>8.2f} ms | Top-3: {res['top_3_pages']}"
            )
    return all_results


if __name__ == "__main__":
    run_full_benchmark_suite()
