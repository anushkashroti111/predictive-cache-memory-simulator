"""Tests for cache_map.py and ingestion.py. Run from src/:  python -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cache_map import CustomHashMap, fnv1a_hash, normalize_url  # noqa: E402
from heap_adapter import CacheNode  # noqa: E402
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
        self.assertEqual(CustomHashMap().bucket_count, 2048)

    def test_collisions_resolved(self):
        m = CustomHashMap(bucket_count=1)  # force every URL into one bucket
        m.MAX = None
        nodes = [CacheNode(f"/p{i}", i) for i in range(3)]
        for n in nodes:
            self.assertTrue(m.insert(n))
        # (resize triggers at load > 0.75, so just verify lookups stay correct)
        for n in nodes:
            self.assertIs(m.get(n.url), n)
        self.assertIsNone(m.get("/missing"))

    def test_duplicate_insert_rejected(self):
        m = CustomHashMap()
        self.assertTrue(m.insert(CacheNode("/a", 1)))
        self.assertFalse(m.insert(CacheNode("/a", 2)))
        self.assertEqual(len(m), 1)

    def test_resize_preserves_entries(self):
        m = CustomHashMap(bucket_count=4)
        for i in range(100):
            m.insert(CacheNode(f"/p{i}", i))
        self.assertGreater(m.bucket_count, 4)
        self.assertEqual(len(m), 100)
        self.assertTrue(all(m.get(f"/p{i}") for i in range(100)))


class TestIngestion(unittest.TestCase):
    def test_tick_and_frequency(self):
        e = IngestionEngine()
        e.ingest_stream(["/a", "/b", "/a"])
        self.assertEqual(e.sequence_tick, 3)
        a = e.hash_map.get("/a")
        self.assertEqual((a.frequency, a.last_accessed_timestamp), (2, 3))
        self.assertEqual(e.heap.heap[0].url, "/a")

    def test_tie_breaker_recency(self):
        e = IngestionEngine()
        e.ingest_stream(["/pageA", "/pageB", "/pageC"])
        self.assertEqual(e.heap.heap[0].url, "/pagec")  # normalized to lowercase

    def test_invalid_rejected_without_tick(self):
        e = IngestionEngine()
        accepted = e.ingest_stream(["", "  ", None, "/ok"])
        self.assertEqual(accepted, 1)
        self.assertEqual(e.rejected_count, 3)
        self.assertEqual(e.sequence_tick, 1)

    def test_empty_stream(self):
        e = IngestionEngine()
        self.assertEqual(e.ingest_stream([]), 0)
        self.assertTrue(e.heap.is_empty())

    def test_burst_identical(self):
        e = IngestionEngine()
        e.ingest_stream(["/dashboard"] * 10_000)
        self.assertEqual(e.hash_map.get("/dashboard").frequency, 10_000)
        self.assertEqual(len(e.heap), 1)

    def test_large_stream_bounded_memory(self):
        import random
        rng = random.Random(1)
        pool = [f"/page{i}" for i in range(50)]
        e = IngestionEngine()
        e.ingest_stream(rng.choice(pool) for _ in range(500_000))  # generator
        self.assertEqual(len(e.hash_map), 50)
        self.assertEqual(len(e.heap), 50)
        self.assertEqual(e.sequence_tick, 500_000)
        self.assertTrue(heap_is_valid(e.heap))


if __name__ == "__main__":
    unittest.main()