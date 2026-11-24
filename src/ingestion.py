"""
ingestion.py - Ingestion pipeline: URL request -> HashMap + MaxHeap update.

Owner: Priyanshi (Hash Map & Ingestion Lead)

Per request:
    1. Normalize the URL (strip, lowercase); reject if invalid (clock does NOT advance).
    2. sequence_tick += 1
    3. Known URL  -> frequency += 1, timestamp = tick, sift_up via heap_index
       Unseen URL -> create node in map, append to heap, sift_up
"""
from typing import Iterable, Optional

from cache_map import CustomHashMap, normalize_url
from priority_heap import CacheNode, MaxHeap


class IngestionEngine:
    def __init__(self, heap: Optional[MaxHeap] = None,
                 hash_map: Optional[CustomHashMap] = None):
        # Pass in the shared heap if the predictor already holds one.
        self.heap = heap if heap is not None else MaxHeap()
        self.hash_map = hash_map if hash_map is not None else CustomHashMap()
        # Global logical clock, kept on the instance so separate simulation
        # runs never share state. Make a new engine to reset.
        self.sequence_tick = 0
        self.rejected_count = 0

    def process_request(self, raw_url) -> Optional[CacheNode]:
        """Handle one request. Returns the updated node, or None if rejected."""
        url = normalize_url(raw_url)
        if url is None:
            self.rejected_count += 1
            return None

        self.sequence_tick += 1

        node = self.hash_map.insert(url)            # existing node or new (freq 0)
        is_new = node.heap_index == -1              # not placed in the heap yet
        self.hash_map.update_access(url, self.sequence_tick)

        if is_new:
            self.heap.raw_insert(node)              # sets node.heap_index
        # Frequency and timestamp only ever increase, so priority can only
        # rise: sift_up alone restores the heap property in O(log N).
        self.heap.sift_up(node.heap_index)
        return node

    def ingest_stream(self, urls: Iterable) -> int:
        """
        Process an iterable/generator one URL at a time. Nothing is buffered,
        so memory grows with UNIQUE URLs only, not stream length.
        Returns the number of accepted requests.
        """
        accepted = 0
        for raw in urls:
            if self.process_request(raw) is not None:
                accepted += 1
        return accepted