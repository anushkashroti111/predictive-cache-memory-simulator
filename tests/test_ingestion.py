"""Tests for cache_map.py and ingestion.py.
Run from the repo root:  python -m unittest discover -s tests -v"""
import os
import random
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cache_map import CustomHashMap, fnv1a_hash, normalize_url  # noqa: E402
from ingestion import IngestionEngine  # noqa: E402


def heap_is_valid(heap) -> bool:
    """Max-heap property holds and every node's heap_index is in sync."""
    for i, node in enumerate(heap.heap):
        if node.heap_index != i:
            return False
        if i > 0 and heap.is_higher_priority(node, heap.heap[(i - 1) // 2]):
            return False
    return True


class TestNormalize(unittest.TestCase):
    def test_cleaning(self):
        self.assertEqual(normalize_url("  /Home \n"), "/home")

    def test_rejects_invalid(self):
        for bad in ["", "   ", None, 42, "/a b", "/a\tb"]:
            self.assertIsNone(normalize_url(bad))


class TestHashMap(unittest.TestCase):
    def test_hash_deterministic_and_in_range(self):
        m = CustomHashMap()
        self.assertEqual(fnv1a_hash("/home"), fnv1a_hash("/home"))
        for u in ["/a", "/b", "/dashboard"]:
            self.assertTrue(0 <= m._bucket_index(u) < m.bucket_count)

    def test_bucket_count(self):
        self.assertEqual(CustomHashMap().bucket_count, 1024)

    def test_collisions_resolved(self):
        m = CustomHashMap(1, max_load_factor=None)   # every URL in one bucket
        nodes = [m.insert(f"/p{i}") for i in range(3)]
        self.assertEqual(m.bucket_lengths(), [3])
        for n in nodes:
            self.assertIs(m.get(n.url), n)
        self.assertIsNone(m.get("/missing"))

    def test_duplicate_insert_returns_same_node(self):
        m = CustomHashMap()
        first = m.insert("/a")
        self.assertIs(m.insert("/a"), first)
        self.assertEqual(len(m), 1)

    def test_resize_preserves_entries(self):
        m = CustomHashMap(4)
        for i in range(100):
            m.insert(f"/p{i}")
        self.assertGreater(m.bucket_count, 4)
        self.assertEqual(len(m), 100)
        self.assertEqual(sum(m.bucket_lengths()), 100)
        self.assertTrue(all(m.get(f"/p{i}") for i in range(100)))


class TestIngestion(unittest.TestCase):
    def test_tick_and_frequency(self):
        e = IngestionEngine()
        e.ingest_stream(["/a", "/b", "/a"])
        self.assertEqual(e.sequence_tick, 3)
        a = e.hash_map.get("/a")
        self.assertEqual((a.frequency, a.last_accessed_timestamp), (2, 3))
        self.assertEqual(e.heap.heap[0].url, "/a")
        self.assertTrue(heap_is_valid(e.heap))

    def test_tie_breaker_recency(self):
        e = IngestionEngine()
        e.ingest_stream(["/pageA", "/pageB", "/pageC"])
        self.assertEqual(e.heap.heap[0].url, "/pagec")  # normalized to lowercase

    def test_invalid_rejected_without_tick(self):
        e = IngestionEngine()
        accepted = e.ingest_stream(["", "  ", None, 7, "/ok"])
        self.assertEqual(accepted, 1)
        self.assertEqual(e.rejected_count, 4)
        self.assertEqual(e.sequence_tick, 1)

    def test_messy_urls_merge_after_normalizing(self):
        e = IngestionEngine()
        e.ingest_stream(["/Home", "  /home  ", "/HOME\n"])
        self.assertEqual(len(e.hash_map), 1)
        self.assertEqual(e.hash_map.get("/home").frequency, 3)

    def test_empty_stream(self):
        e = IngestionEngine()
        self.assertEqual(e.ingest_stream([]), 0)
        self.assertTrue(e.heap.is_empty())

    def test_burst_identical(self):
        e = IngestionEngine()
        e.ingest_stream(["/dashboard"] * 10_000)
        self.assertEqual(e.hash_map.get("/dashboard").frequency, 10_000)
        self.assertEqual(len(e.heap), 1)

    def test_matches_counter_and_heap_valid(self):
        rng = random.Random(7)
        pool = [f"/page{i}" for i in range(200)]
        stream = [rng.choice(pool) for _ in range(20_000)]
        e = IngestionEngine()
        e.ingest_stream(stream)
        expected = Counter(stream)
        self.assertEqual(len(e.hash_map), len(expected))
        for url, count in expected.items():
            self.assertEqual(e.hash_map.get(url).frequency, count)
        self.assertTrue(heap_is_valid(e.heap))

    def test_large_stream_bounded_memory(self):
        rng = random.Random(1)
        pool = [f"/page{i}" for i in range(50)]
        e = IngestionEngine()
        e.ingest_stream(rng.choice(pool) for _ in range(500_000))  # generator, not a list
        self.assertEqual(len(e.hash_map), 50)
        self.assertEqual(len(e.heap), 50)
        self.assertEqual(e.sequence_tick, 500_000)
        self.assertTrue(heap_is_valid(e.heap))


if __name__ == "__main__":
    unittest.main()