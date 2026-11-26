import os
import sys
import time
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SRC_DIR = os.path.join(os.path.dirname(__file__), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from cache_map import CustomHashMap, normalize_url  # noqa: E402
from ingestion import IngestionEngine  # noqa: E402
from metrics import HitMissTracker, get_top_k  # noqa: E402
from predictor import CachePredictor  # noqa: E402
from workloads import (  # noqa: E402
    generate_looping_traffic,
    generate_random_traffic,
    generate_zipfian_traffic,
)


app = FastAPI(title="Predictive Cache & Memory Access Simulator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKLOAD_GENERATORS = {
    "random": generate_random_traffic,
    "looping": generate_looping_traffic,
    "zipfian": generate_zipfian_traffic,
}


class SimulationRequest(BaseModel):
    workload: Literal["random", "looping", "zipfian"]
    size: int = Field(default=10000, ge=1, le=50000)
    seed: int = Field(default=42)
    top_k: int = Field(default=5, ge=1, le=20)
    snapshot_limit: int = Field(default=80, ge=1, le=200)


class ComparisonRequest(BaseModel):
    size: int = Field(default=10000, ge=1, le=50000)
    seed: int = Field(default=42)
    top_k: int = Field(default=5, ge=1, le=20)


def serialize_hash_map(hash_map: CustomHashMap, bucket_focus: Optional[int] = None) -> dict:
    buckets = []
    for index, chain in enumerate(hash_map.buckets):
        buckets.append({
            "index": index,
            "items": [
                {
                    "item": node.url,
                    "frequency": node.frequency,
                    "last_accessed": node.last_accessed_timestamp,
                    "heap_index": node.heap_index,
                }
                for node in chain
            ],
        })
    return {
        "bucket_count": hash_map.bucket_count,
        "unique_items": len(hash_map),
        "focus_bucket": bucket_focus,
        "stats": hash_map.stats(),
        "buckets": buckets,
    }


def serialize_heap(heap, updated_item: Optional[str] = None) -> dict:
    nodes = [
        {
            "item": node.url,
            "frequency": node.frequency,
            "last_accessed": node.last_accessed_timestamp,
            "index": index,
            "parent": (index - 1) // 2 if index > 0 else None,
            "left": 2 * index + 1 if 2 * index + 1 < len(heap.heap) else None,
            "right": 2 * index + 2 if 2 * index + 2 < len(heap.heap) else None,
            "is_root": index == 0,
            "is_updated": node.url == updated_item,
        }
        for index, node in enumerate(heap.heap)
    ]
    return {"nodes": nodes, "root": nodes[0]["item"] if nodes else None}


def generate_workload(workload: str, size: int, seed: int):
    generator = WORKLOAD_GENERATORS[workload]
    if workload == "looping":
        return generator(length=size)
    return generator(length=size, seed=seed)


def run_detailed_simulation(workload: str, size: int, seed: int, top_k: int, snapshot_limit: int) -> dict:
    accesses = generate_workload(workload, size, seed)
    engine = IngestionEngine(hash_map=CustomHashMap(num_buckets=CustomHashMap.DEFAULT_BUCKETS))
    predictor = CachePredictor(engine.heap)
    tracker = HitMissTracker()
    snapshots = []
    previous_url = None
    input_accesses = 0

    start_time = time.perf_counter()
    snapshot_positions = set()
    if len(accesses) > 0:
        target = min(snapshot_limit, len(accesses))
        snapshot_positions = {
            round(index * (len(accesses) - 1) / max(target - 1, 1))
            for index in range(target)
        }

    for step, raw_url in enumerate(accesses):
        url = normalize_url(raw_url)
        if url is None:
            continue
        input_accesses += 1

        if previous_url is None:
            engine.process_request(url)
            previous_url = url
            if step in snapshot_positions:
                snapshots.append({
                    "step": step,
                    "incoming": url,
                    "predicted": None,
                    "actual": url,
                    "correct": None,
                    "bucket": engine.hash_map._bucket_index(url),
                    "lookup": "warm-up",
                    "collision": False,
                    "hash_table": serialize_hash_map(engine.hash_map, engine.hash_map._bucket_index(url)),
                    "heap": serialize_heap(engine.heap, url),
                })
            continue

        predicted = predictor.predict_next()
        tracker.record(predicted, url)
        before_urls = [node.url for node in engine.heap.heap]
        node = engine.process_request(url)
        after_urls = [node.url for node in engine.heap.heap]
        swapped = [
            index for index, (before, after) in enumerate(zip(before_urls, after_urls))
            if before != after
        ]
        bucket_index = engine.hash_map._bucket_index(url)
        chain = engine.hash_map.buckets[bucket_index]
        collision = len(chain) > 1

        if step in snapshot_positions:
            snapshots.append({
                "step": step,
                "incoming": url,
                "predicted": predicted,
                "actual": url,
                "correct": predicted == url,
                "bucket": bucket_index,
                "lookup": "hit" if engine.hash_map.get(url) is not None else "miss",
                "collision": collision,
                "updated_frequency": node.frequency,
                "updated_timestamp": node.last_accessed_timestamp,
                "swapped_indices": swapped,
                "hash_table": serialize_hash_map(engine.hash_map, bucket_index),
                "heap": serialize_heap(engine.heap, url),
            })
        previous_url = url

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    top_items = [
        {
            "rank": index,
            "item": node.url,
            "frequency": node.frequency,
            "last_accessed": node.last_accessed_timestamp,
        }
        for index, node in enumerate(get_top_k(engine.heap, top_k), start=1)
    ]
    return {
        "workload": workload,
        "seed": seed,
        "input_accesses": input_accesses,
        "unique_urls": len(engine.hash_map),
        "total_steps": tracker.total_steps,
        "evaluated_predictions": tracker.total_steps,
        "hits": tracker.hits,
        "misses": tracker.misses,
        "accuracy": round(tracker.accuracy, 2),
        "latency_ms": round(elapsed_ms, 2),
        "top_k": top_items,
        "top_3_pages": [item["item"] for item in top_items[:3]],
        "hash_table": serialize_hash_map(engine.hash_map),
        "heap": serialize_heap(engine.heap),
        "snapshots": snapshots,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "predictive-cache-simulator"}


@app.get("/api/workloads")
def workloads():
    return {
        "workloads": [
            {"name": "random", "description": "Uniform random page accesses"},
            {"name": "looping", "description": "Repeating A -> B -> C page pattern"},
            {"name": "zipfian", "description": "Skewed popularity-based page accesses"},
        ],
        "sizes": [1000, 10000, 50000],
    }


@app.post("/api/simulation/run")
def run_simulation(request: SimulationRequest):
    try:
        return run_detailed_simulation(
            request.workload,
            request.size,
            request.seed,
            request.top_k,
            request.snapshot_limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/simulation/compare")
def compare(request: ComparisonRequest):
    return {
        workload: run_detailed_simulation(workload, request.size, request.seed, request.top_k, 1)
        for workload in ("random", "looping", "zipfian")
    }
