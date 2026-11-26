"""System-level tests for the integrated predictive-cache simulator."""

import os
import sys
from collections import Counter
from types import SimpleNamespace

import pytest


SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, SRC)

from cache_map import CustomHashMap, fnv1a_hash
from ingestion import IngestionEngine
from main import compare_prediction_policies, run_simulation
from metrics import HitMissTracker, get_top_k
from predictor import CachePredictor
from priority_heap import CacheNode, MaxHeap
from transition_predictor import TransitionPredictor
from workloads import (
    PAGE_POOL,
    generate_looping_traffic,
    generate_random_traffic,
    generate_zipfian_traffic,
    load_web_server_log_urls,
)


def heap_is_valid(heap):
    for i, node in enumerate(heap.heap):
        assert node.heap_index == i
        if i:
            parent = heap.heap[(i - 1) // 2]
            assert not heap.is_higher_priority(node, parent)
    return True


def synchronized(engine):
    assert heap_is_valid(engine.heap)
    assert len(engine.heap) == len(engine.hash_map)
    for node in engine.heap.heap:
        assert engine.hash_map.get(node.url) is node


def test_sim_001_initialization():
    engine = IngestionEngine()
    heap = engine.heap
    assert isinstance(heap, MaxHeap)
    assert isinstance(engine.hash_map, CustomHashMap)
    assert heap.is_empty()
    assert engine.sequence_tick == 0
    assert len(engine.hash_map.buckets) == 1024
    assert CachePredictor(heap).predict_next() is None
    assert HitMissTracker().summary() == {
        "total_steps": 0,
        "hits": 0,
        "misses": 0,
        "accuracy": 0.0,
    }


def test_sim_002_empty_integrated_stream():
    result = run_simulation([], workload_name="empty")
    assert result["total_steps"] == 0
    assert result["hits"] == 0
    assert result["misses"] == 0
    assert result["accuracy"] == 0.0
    assert result["unique_urls"] == 0


def test_sim_003_single_url():
    engine = IngestionEngine()
    node = engine.process_request(" /HOME ")
    assert node is engine.hash_map.get("/home")
    assert node.frequency == 1
    assert node.last_accessed_timestamp == 1
    assert node.heap_index == 0
    assert engine.heap.heap[0] is node
    synchronized(engine)


def test_sim_004_repeated_url():
    engine = IngestionEngine()
    for tick in range(1, 101):
        engine.process_request("/home")
    node = engine.hash_map.get("/home")
    assert node.frequency == 100
    assert node.last_accessed_timestamp == 100
    assert node.heap_index == 0
    synchronized(engine)


def test_sim_005_multiple_unique_urls():
    engine = IngestionEngine()
    for i in range(100):
        engine.process_request(f"/page{i}")
    assert len(engine.hash_map) == 100
    assert len(engine.heap) == 100
    assert all(engine.hash_map.get(f"/page{i}") is not None for i in range(100))
    synchronized(engine)


def test_sim_006_hash_collision_handling():
    map_ = CustomHashMap(num_buckets=1, max_load_factor=None)
    nodes = [map_.insert(url) for url in ("/a", "/b", "/c")]
    assert map_.bucket_lengths() == [3]
    assert all(map_.get(url) is node for url, node in zip(("/a", "/b", "/c"), nodes))
    assert map_.get("/a") is not map_.get("/b")


def test_sim_007_heap_priority_and_tiebreaker():
    heap = MaxHeap()
    low = CacheNode("/low", 1, 1)
    older = CacheNode("/older", 5, 2)
    newer = CacheNode("/newer", 6, 2)
    for node in (low, older, newer):
        heap.raw_insert(node)
        heap.sift_up(node.heap_index)
    assert heap.heap[0].url == "/newer"
    heap.sift_down(0)
    assert heap_is_valid(heap)


def test_heap_and_top_k_resolve_complete_ties_deterministically():
    heap = MaxHeap()
    for url in ("/z", "/m", "/a"):
        node = CacheNode(url, 10, 3)
        heap.raw_insert(node)
        heap.sift_up(node.heap_index)

    assert heap.heap[0].url == "/a"
    assert [node.url for node in get_top_k(heap, 3)] == ["/a", "/m", "/z"]


def test_sim_008_predictor_root_and_no_mutation():
    engine = IngestionEngine()
    engine.ingest_stream(["/a", "/b", "/b"])
    predictor = CachePredictor(engine.heap)
    snapshot = list(engine.heap.heap)
    assert predictor.predict_next() == "/b"
    assert engine.heap.heap == snapshot
    assert CachePredictor(MaxHeap()).predict_next() is None


def test_sim_009_heap_index_consistency_after_updates():
    engine = IngestionEngine()
    engine.ingest_stream(["/a", "/b", "/c", "/b", "/a", "/a"])
    synchronized(engine)
    heap = engine.heap
    a = engine.hash_map.get("/a")
    b = engine.hash_map.get("/b")
    assert heap.heap[a.heap_index] is a
    assert heap.heap[b.heap_index] is b
    heap.swap_nodes(a.heap_index, b.heap_index)
    assert heap.heap[a.heap_index] is a
    assert heap.heap[b.heap_index] is b


@pytest.mark.parametrize("length", [0, 1, 100])
def test_sim_010_random_workload_boundaries(length):
    first = generate_random_traffic(length=length, seed=123)
    second = generate_random_traffic(length=length, seed=123)
    assert first == second
    assert len(first) == length
    assert set(first).issubset(set(PAGE_POOL))


def test_sim_011_looping_workload_pattern():
    pattern = ["/A", "/B", "/C"]
    traffic = generate_looping_traffic(length=10, pattern=pattern)
    assert traffic == [pattern[i % len(pattern)] for i in range(10)]
    assert generate_looping_traffic(length=0, pattern=pattern) == []
    with pytest.raises(ValueError):
        generate_looping_traffic(length=10, pattern=[])


def test_sim_012_zipfian_workload_skew_and_boundaries():
    traffic = generate_zipfian_traffic(length=10000, seed=42)
    assert len(traffic) == 10000
    counts = Counter(traffic)
    assert counts["/home"] > counts["/page49"]
    assert generate_zipfian_traffic(length=0, seed=42) == []


def test_sim_013_metrics_validation():
    tracker = HitMissTracker()
    tracker.record(None, "/a")
    tracker.record("/a", "/a")
    tracker.record("/a", "/b")
    tracker.record("/b", "/b")
    summary = tracker.summary()
    assert summary["hits"] == 2
    assert summary["misses"] == 2
    assert summary["total_steps"] == 4
    assert summary["hits"] + summary["misses"] == summary["total_steps"]
    assert summary["accuracy"] == 50.0


@pytest.mark.parametrize("k", [1, 0])
def test_sim_014_top_k_boundaries(k):
    heap = MaxHeap()
    for i, url in enumerate(["/a", "/b", "/c"]):
        node = CacheNode(url, i + 1, i + 1)
        heap.raw_insert(node)
        heap.sift_up(node.heap_index)
    snapshot = [(n.url, n.frequency, n.last_accessed_timestamp, n.heap_index) for n in heap.heap]
    result = get_top_k(heap, k)
    assert len(result) == (1 if k == 1 else 0)
    assert [(n.url, n.frequency, n.last_accessed_timestamp, n.heap_index) for n in heap.heap] == snapshot
    assert get_top_k(MaxHeap(), k) == []


def test_sim_015_top_k_greater_than_heap():
    heap = MaxHeap()
    nodes = [CacheNode("/a", 1, 3), CacheNode("/b", 2, 2), CacheNode("/c", 3, 1)]
    for node in nodes:
        heap.raw_insert(node)
        heap.sift_up(node.heap_index)
    snapshot = list(heap.heap)
    indices = [node.heap_index for node in heap.heap]
    assert [n.url for n in get_top_k(heap, 100)] == ["/a", "/b", "/c"]
    assert heap.heap == snapshot
    assert [node.heap_index for node in heap.heap] == indices


def test_sim_016_burst_identical():
    engine = IngestionEngine()
    engine.ingest_stream(["/burst"] * 10_000)
    assert engine.sequence_tick == 10_000
    assert engine.hash_map.get("/burst").frequency == 10_000
    assert len(engine.heap) == 1
    synchronized(engine)


def test_sim_017_large_mixed_stream():
    rng = __import__("random").Random(123)
    pool = [f"/page{i}" for i in range(500)]
    stream = (rng.choice(pool) for _ in range(500_000))
    engine = IngestionEngine()
    assert engine.ingest_stream(stream) == 500_000
    assert engine.sequence_tick == 500_000
    assert len(engine.heap) == 500
    assert len(engine.hash_map) == 500
    synchronized(engine)


@pytest.mark.parametrize("size", [1_000, 50_000, 500_000])
@pytest.mark.parametrize("workload", ["random", "looping", "zipfian"])
def test_sim_018_benchmark_combinations(size, workload):
    if workload == "random":
        stream = generate_random_traffic(length=size, seed=42)
    elif workload == "looping":
        stream = generate_looping_traffic(length=size)
    else:
        stream = generate_zipfian_traffic(length=size, seed=42)
    result = run_simulation(stream, workload_name=f"{workload}_{size}")
    assert result["input_accesses"] == size
    assert result["evaluated_predictions"] == size - 1
    assert result["total_steps"] == size - 1
    assert result["hits"] + result["misses"] == result["evaluated_predictions"]
    assert result["accuracy"] == round(
        result["hits"] / result["evaluated_predictions"] * 100, 2
    )


def test_huggingface_loader_reads_both_configs_and_limits_rows(monkeypatch):
    calls = []
    configs = {
        "servers": {"train": [{"id": 1}, {"id": 2}]},
        "access_logs": {
            "train": [
                {"server_id": 1, "path": "/Home"},
                {"server_id": 2, "path": "/docs"},
                {"server_id": 1, "path": "/contact"},
            ]
        },
    }

    def fake_load_dataset(dataset_name, config):
        calls.append((dataset_name, config))
        return configs[config]

    monkeypatch.setitem(
        sys.modules, "datasets", SimpleNamespace(load_dataset=fake_load_dataset)
    )

    assert list(load_web_server_log_urls(limit=2)) == ["/Home", "/docs"]
    assert calls == [
        ("mindweave/web-server-logs", "servers"),
        ("mindweave/web-server-logs", "access_logs"),
    ]


def test_huggingface_loader_zero_limit_is_empty(monkeypatch):
    configs = {
        "servers": {"train": [{"id": 1}]},
        "access_logs": {"train": [{"server_id": 1, "path": "/home"}]},
    }
    monkeypatch.setitem(
        sys.modules,
        "datasets",
        SimpleNamespace(load_dataset=lambda _name, config: configs[config]),
    )

    assert list(load_web_server_log_urls(limit=0)) == []


def test_huggingface_loader_rejects_unknown_server(monkeypatch):
    configs = {
        "servers": {"train": [{"id": 1}]},
        "access_logs": {"train": [{"server_id": 99, "path": "/home"}]},
    }
    monkeypatch.setitem(
        sys.modules,
        "datasets",
        SimpleNamespace(load_dataset=lambda _name, config: configs[config]),
    )

    with pytest.raises(ValueError, match="unknown server id"):
        list(load_web_server_log_urls())


@pytest.mark.parametrize("limit", [-1, True, 1.5, "2"])
def test_huggingface_loader_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="limit"):
        load_web_server_log_urls(limit=limit)


def test_simulation_csv_includes_benchmark_details(tmp_path):
    output = tmp_path / "results.csv"
    result = run_simulation(["/home", "/home", "/docs"], csv_output_path=str(output))

    assert result["input_accesses"] == 3
    assert result["evaluated_predictions"] == 2
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith(
        "workload,policy,input_accesses,unique_urls,total_steps,"
        "evaluated_predictions,correct_predictions,incorrect_predictions"
    )
    assert len(lines) == 2


def test_simulation_excludes_warmup_and_unpredicted_future():
    empty = run_simulation([])
    single = run_simulation(["/only"])
    two = run_simulation(["/first", "/second"])

    assert (empty["input_accesses"], empty["evaluated_predictions"]) == (0, 0)
    assert (single["input_accesses"], single["evaluated_predictions"]) == (1, 0)
    assert (two["input_accesses"], two["evaluated_predictions"]) == (2, 1)
    assert two["hits"] + two["misses"] == 1


def test_transition_predictor_fallback_and_tie_break():
    predictor = TransitionPredictor()
    assert predictor.predict_next("/unseen", fallback="/fallback") == "/fallback"

    predictor.record_transition("/source", "/z")
    predictor.record_transition("/source", "/b")
    assert predictor.predict_next("/source") == "/b"


def test_transition_policy_learns_looping_successors():
    stream = generate_looping_traffic(length=30, pattern=["/a", "/b", "/c"])
    results = compare_prediction_policies(stream, workload_name="looping")
    baseline, transition = results

    assert baseline["evaluated_predictions"] == transition["evaluated_predictions"] == 29
    assert baseline["hits"] == 0
    assert transition["hits"] == 26
    assert transition["accuracy"] > baseline["accuracy"]


def test_policy_comparison_uses_identical_opportunities():
    results = compare_prediction_policies(
        (url for url in ["/a", "/b", "/c", "/a"])
    )
    assert [result["policy"] for result in results] == [
        "frequency_recency",
        "transition",
    ]
    assert all(result["input_accesses"] == 4 for result in results)
    assert all(result["evaluated_predictions"] == 3 for result in results)
    assert all(
        result["correct_predictions"] + result["incorrect_predictions"] == 3
        for result in results
    )


def test_simulation_rejects_unknown_prediction_policy():
    with pytest.raises(ValueError, match="unknown prediction policy"):
        run_simulation([], policy="unknown")


def test_tracker_csv_replaces_previous_metrics_row(tmp_path):
    output = tmp_path / "metrics.csv"
    tracker = HitMissTracker()
    tracker.record(None, "/home")
    tracker.export_csv(str(output), workload="first")
    tracker.export_csv(str(output), workload="second")

    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "workload,total_steps,hits,misses,accuracy"
    assert len(lines) == 2
    assert lines[1].startswith("second,")
