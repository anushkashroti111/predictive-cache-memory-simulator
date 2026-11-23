"""
ingestion.py  --  Ingestion pipeline: URL request -> HashMap + MaxHeap update.

Owner: Priyanshi (Hash Map & Ingestion Lead)

Per request:
    1. Normalize the URL; reject it if invalid (the clock does NOT advance).
    2. sequence_tick += 1
    3. Known URL  -> frequency += 1, timestamp = tick, sift_up via heap_index
       Unseen URL -> new CacheNode, insert into map and heap, sift_up
"""
from typing import Iterable, Optional

from cache_map import CustomHashMap, normalize_url
from heap_adapter import CacheNode, MaxHeap


class IngestionEngine:
    def __init__(self, heap: Optional[MaxHeap] = None,
                 hash_map: Optional[CustomHashMap] = None):
        # Pass in Eetal's heap if one is shared with the predictor.
        self.heap = heap if heap is not None else MaxHeap()
        self.hash_map = hash_map if hash_map is not None else CustomHashMap()
        # Global logical clock. Kept on the instance (not a module global) so
        # separate simulation runs never share state; reset by making a new engine.
        self.sequence_tick = 0
        self.rejected_count = 0

    def process_request(self, raw_url) -> Optional[CacheNode]:
        """Handle one request. Returns the updated node, or None if rejected."""
        url = normalize_url(raw_url)
        if url is None:
            self.rejected_count += 1
            return None

        self.sequence_tick += 1
        node = self.hash_map.get(url)

        if node is not None:
            node.frequency += 1
            node.last_accessed_timestamp = self.sequence_tick
            # Frequency and timestamp only ever increase, so priority can only
            # rise: sift_up alone restores the heap property, in O(log N).
            self.heap.sift_up(node.heap_index)
        else:
            node = CacheNode(url, self.sequence_tick)
            self.hash_map.insert(node)
            self.heap.raw_insert(node)          # sets node.heap_index
            self.heap.sift_up(node.heap_index)
        return node

    def ingest_stream(self, urls: Iterable) -> int:
        """
        Process an iterable/generator of URLs one at a time (nothing is
        buffered, so 500k+ requests use memory proportional to UNIQUE URLs only).
        Returns the number of accepted requests.
        """
        accepted = 0
        for raw in urls:
            if self.process_request(raw) is not None:
                accepted += 1
        return accepted