"""
Tests for src/cache_map.py (Hash Map Layer).
"""

import os
import random
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cache_map import CacheNode, CustomHashMap, fnv1a_hash  # noqa: E402


class TestCacheNode(unittest.TestCase):
    def test_contract_field_names(self):
        node = CacheNode("/pageA", 7, 3, 5)
        self.assertEqual(node.url, "/pageA")
        self.assertEqual(node.last_accessed_timestamp, 7)
        self.assertEqual(node.frequency, 3)
        self.assertEqual(node.heap_index, 5)

    def test_defaults_match_heap_version(self):
        node = CacheNode("/pageA", 1)
        self.assertEqual(node.frequency, 1)
        self.assertEqual(node.heap_index, -1)

    def test_repr(self):
        self.assertEqual(repr(CacheNode("/a", 2, 4, 1)),
                         "CacheNode(url='/a', freq=4, ts=2, idx=1)")


class TestHashFunction(unittest.TestCase):
    def test_known_fnv1a_vectors(self):
        # Official FNV-1a 32-bit test vectors
        self.assertEqual(fnv1a_hash(""), 0x811C9DC5)
        self.assertEqual(fnv1a_hash("a"), 0xE40C292C)
        self.assertEqual(fnv1a_hash("foobar"), 0xBF9CF968)

    def test_deterministic_and_32_bit(self):
        url = "/shuttle/missions/sts-68/news/sts-68-mcc-05.txt"
        self.assertEqual(fnv1a_hash(url), fnv1a_hash(url))
        self.assertTrue(0 <= fnv1a_hash(url) <= 0xFFFFFFFF)


class TestConstruction(unittest.TestCase):
    def test_default_has_1024_empty_buckets(self):
        m = CustomHashMap()
        self.assertEqual(len(m.buckets), 1024)
        self.assertEqual(m.num_buckets, 1024)
        self.assertTrue(all(bucket == [] for bucket in m.buckets))
        self.assertEqual(len(m), 0)

    def test_custom_bucket_count(self):
        self.assertEqual(len(CustomHashMap(8).buckets), 8)

    def test_bad_bucket_count_rejected(self):
        for bad in (0, -5, 2.5, "10", None, True):
            with self.assertRaises(ValueError):
                CustomHashMap(bad)

    def test_empty_map_queries_do_not_crash(self):
        m = CustomHashMap()
        self.assertIsNone(m.get("/home"))
        self.assertEqual(list(m.nodes()), [])
        self.assertEqual(m.stats()["unique_urls"], 0)


class TestInsert(unittest.TestCase):
    def test_new_node_initial_values(self):
        node = CustomHashMap().insert("/home")
        self.assertEqual(node.url, "/home")
        self.assertEqual(node.frequency, 0)
        self.assertEqual(node.last_accessed_timestamp, 0)
        self.assertEqual(node.heap_index, -1)

    def test_node_lands_in_correct_bucket(self):
        m = CustomHashMap()
        node = m.insert("/home")
        index = fnv1a_hash("/home") % 1024
        self.assertIn(node, m.buckets[index])
        self.assertEqual(sum(m.bucket_lengths()), 1)

    def test_duplicate_insert_returns_same_node(self):
        m = CustomHashMap()
        first = m.insert("/home")
        second = m.insert("/home")
        self.assertIs(first, second)
        self.assertEqual(len(m), 1)

    def test_invalid_urls_rejected(self):
        m = CustomHashMap()
        for bad in (None, "", "   ", 123, 4.5, b"/home", ["/home"]):
            with self.assertRaises(ValueError):
                m.insert(bad)
        self.assertEqual(len(m), 0)


class TestGet(unittest.TestCase):
    def test_missing_returns_none(self):
        m = CustomHashMap()
        m.insert("/home")
        self.assertIsNone(m.get("/dashboard"))

    def test_existing_returns_same_object(self):
        m = CustomHashMap()
        node = m.insert("/home")
        self.assertIs(m.get("/home"), node)
        self.assertIn("/home", m)
        self.assertNotIn("/other", m)

    def test_invalid_url_returns_none_not_crash(self):
        m = CustomHashMap()
        for bad in (None, "", "  ", 42):
            self.assertIsNone(m.get(bad))

    def test_urls_are_case_sensitive_and_exact(self):
        m = CustomHashMap()
        m.insert("/Home")
        self.assertIsNone(m.get("/home"))


class TestCollisions(unittest.TestCase):
    def test_single_bucket_forces_every_collision(self):
        m = CustomHashMap(1, max_load_factor=None)   # <- was CustomHashMap(1)
        nodes = {u: m.insert(u) for u in ("/a", "/b", "/c", "/d")}
        self.assertEqual(m.bucket_lengths(), [4])
        for url, node in nodes.items():
            self.assertIs(m.get(url), node)
        self.assertIsNone(m.get("/e"))

    def test_real_collision_in_default_1024_map(self):
        # Pigeonhole: among 1025 different URLs, two must share a bucket.
        m = CustomHashMap()
        seen = {}
        pair = None
        for i in range(1025):
            url = f"/page{i}"
            index = fnv1a_hash(url) % 1024
            if index in seen:
                pair = (seen[index], url)
                break
            seen[index] = url
        self.assertIsNotNone(pair)
        first, second = m.insert(pair[0]), m.insert(pair[1])
        self.assertIsNot(first, second)
        self.assertIs(m.get(pair[0]), first)
        self.assertIs(m.get(pair[1]), second)
        self.assertEqual(max(m.bucket_lengths()), 2)

    def test_updates_stay_separate_inside_one_bucket(self):
        m = CustomHashMap(1)
        m.insert("/a")
        m.insert("/b")
        m.update_access("/a", 1)
        m.update_access("/a", 2)
        m.update_access("/b", 3)
        self.assertEqual(m.get("/a").frequency, 2)
        self.assertEqual(m.get("/b").frequency, 1)


class TestUpdateAccess(unittest.TestCase):
    def test_increments_frequency_and_sets_timestamp(self):
        m = CustomHashMap()
        m.insert("/home")
        node = m.update_access("/home", 5)
        self.assertEqual(node.frequency, 1)
        self.assertEqual(node.last_accessed_timestamp, 5)
        node = m.update_access("/home", 9)
        self.assertEqual(node.frequency, 2)
        self.assertEqual(node.last_accessed_timestamp, 9)

    def test_returns_the_same_node_object(self):
        m = CustomHashMap()
        stored = m.insert("/home")
        self.assertIs(m.update_access("/home", 1), stored)

    def test_does_not_touch_heap_index(self):
        m = CustomHashMap()
        node = m.insert("/home")
        node.heap_index = 7          # pretend the heap placed it
        m.update_access("/home", 1)
        self.assertEqual(node.heap_index, 7)

    def test_missing_url_raises_key_error(self):
        with self.assertRaises(KeyError):
            CustomHashMap().update_access("/ghost", 1)

    def test_non_integer_tick_rejected(self):
        m = CustomHashMap()
        m.insert("/home")
        for bad in ("1", 1.5, None, True):
            with self.assertRaises(TypeError):
                m.update_access("/home", bad)

    def test_tie_break_data_a_b_c(self):
        # /pageA, /pageB, /pageC once each: all frequency 1, /pageC newest.
        m = CustomHashMap()
        for tick, url in enumerate(["/pageA", "/pageB", "/pageC"], start=1):
            m.insert(url)
            m.update_access(url, tick)
        nodes = [m.get(u) for u in ("/pageA", "/pageB", "/pageC")]
        self.assertEqual([n.frequency for n in nodes], [1, 1, 1])
        self.assertEqual(max(nodes, key=lambda n: n.last_accessed_timestamp).url, "/pageC")


class TestBoundaryAndStress(unittest.TestCase):
    def test_single_item(self):
        m = CustomHashMap()
        m.insert("/only")
        m.update_access("/only", 1)
        self.assertEqual(len(m), 1)
        self.assertEqual(m.get("/only").frequency, 1)

    def test_burst_of_10000_identical_urls(self):
        m = CustomHashMap()
        m.insert("/dashboard")
        for tick in range(1, 10001):
            m.update_access("/dashboard", tick)
        node = m.get("/dashboard")
        self.assertEqual(node.frequency, 10000)
        self.assertEqual(node.last_accessed_timestamp, 10000)
        self.assertEqual(len(m), 1)

    def test_all_unique_urls(self):
        m = CustomHashMap()
        for i in range(5000):
            m.insert(f"/unique/{i}")
        self.assertEqual(len(m), 5000)
        self.assertEqual(sum(m.bucket_lengths()), 5000)
        self.assertEqual(len(list(m.nodes())), 5000)

    def test_matches_counter_on_random_stream(self):
        rng = random.Random(42)
        pool = [f"/page{i}" for i in range(300)]
        stream = [rng.choice(pool) for _ in range(20000)]
        m = CustomHashMap()
        last_seen = {}
        for tick, url in enumerate(stream, start=1):
            if m.get(url) is None:
                m.insert(url)
            m.update_access(url, tick)
            last_seen[url] = tick
        expected = Counter(stream)          # Counter used ONLY to check the map
        self.assertEqual(len(m), len(expected))
        for url, count in expected.items():
            node = m.get(url)
            self.assertEqual(node.frequency, count)
            self.assertEqual(node.last_accessed_timestamp, last_seen[url])

    def test_stats_keys(self):
        m = CustomHashMap()
        for i in range(10):
            m.insert(f"/p{i}")
        s = m.stats()
        self.assertEqual(s["unique_urls"], 10)
        self.assertEqual(s["buckets"], 1024)
        self.assertGreaterEqual(s["max_chain"], 1)
        self.assertEqual(s["empty_buckets"], 1024 - sum(1 for x in m.bucket_lengths() if x))


if __name__ == "__main__":
    unittest.main()
