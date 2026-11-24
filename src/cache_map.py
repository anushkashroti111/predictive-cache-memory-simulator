"""
cache_map.py - Hash Map Layer (by Gauri)

Maps a page URL to its CacheNode (frequency + last access time) using a
hash table built from scratch: a list of buckets, separate chaining for
collisions, and an FNV-1a hash function. No dict / set / Counter is used
inside the map itself.


Average time per operation is O(1) when buckets are short; the worst case is
O(n) if every URL lands in one bucket. Space is O(n) for n unique URLs.
"""

from typing import Iterator, List, Optional


class CacheNode:
    def __init__(self, url: str, timestamp: int, frequency: int = 1, heap_index: int = -1):
        self.url = url
        self.frequency = frequency
        self.last_accessed_timestamp = timestamp
        self.heap_index = heap_index

    def __repr__(self):
        return (f"CacheNode(url='{self.url}', freq={self.frequency}, "
                f"ts={self.last_accessed_timestamp}, idx={self.heap_index})")


# FNV-1a 32-bit constants (public, standard values)
FNV_OFFSET_BASIS = 2166136261
FNV_PRIME = 16777619


def fnv1a_hash(key: str) -> int:
    hash_value = FNV_OFFSET_BASIS
    for byte in key.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * FNV_PRIME) & 0xFFFFFFFF
    return hash_value


class CustomHashMap:
    DEFAULT_BUCKETS = 1024

    def __init__(self, num_buckets: int = DEFAULT_BUCKETS):
        # num_buckets is a parameter only so tests can force collisions
        # (e.g. 1 bucket). The project itself always uses the default 1024.
        if not isinstance(num_buckets, int) or isinstance(num_buckets, bool) or num_buckets < 1:
            raise ValueError("num_buckets must be an integer >= 1")
        self.num_buckets = num_buckets
        # List of lists: buckets[i] is the chain of nodes whose hash maps to i.
        self.buckets: List[List[CacheNode]] = [[] for _ in range(num_buckets)]
        self._size = 0

    # ---------- helpers ----------

    @staticmethod
    def _is_valid_url(url) -> bool:
        """A usable key is a non-empty string (cleaning is the stream layer's job)."""
        return isinstance(url, str) and url.strip() != ""

    def _bucket_index(self, url: str) -> int:
        """URL -> number in 0 .. num_buckets-1."""
        return fnv1a_hash(url) % self.num_buckets

    # ---------- required API ----------

    def insert(self, url: str) -> CacheNode:
        """
        Create and store a node for a URL not seen before.

        The new node starts at frequency 0, timestamp 0, heap_index -1; the
        pipeline calls update_access() right after to make it frequency 1.
        If the URL already exists, the existing node is returned and nothing
        is duplicated. Invalid URLs (not a string / empty) raise ValueError.
        """
        if not self._is_valid_url(url):
            raise ValueError(f"invalid URL: {url!r}")
        bucket = self.buckets[self._bucket_index(url)]
        for node in bucket:                      # collision check
            if node.url == url:
                return node
        node = CacheNode(url, 0, 0, -1)
        bucket.append(node)
        self._size += 1
        return node

    def get(self, url: str) -> Optional[CacheNode]:
        if not self._is_valid_url(url):
            return None
        for node in self.buckets[self._bucket_index(url)]:
            if node.url == url:
                return node
        return None

    def update_access(self, url: str, tick: int) -> CacheNode:
        if not isinstance(tick, int) or isinstance(tick, bool):
            raise TypeError(f"tick must be an int, got {type(tick).__name__}")
        node = self.get(url)
        if node is None:
            raise KeyError(url)
        node.frequency += 1
        node.last_accessed_timestamp = tick
        return node

    # ---------- extras (tests, benchmarks, report numbers) ----------

    def __len__(self) -> int:
        """Number of unique URLs stored."""
        return self._size

    def __contains__(self, url) -> bool:
        return self.get(url) is not None

    def nodes(self) -> Iterator[CacheNode]:
        """Iterate over every stored node (no particular order)."""
        for bucket in self.buckets:
            for node in bucket:
                yield node

    def bucket_lengths(self) -> List[int]:
        """Chain length of every bucket."""
        return [len(bucket) for bucket in self.buckets]

    def stats(self) -> dict:
        """Chain-length summary, handy for the complexity / efficiency section."""
        lengths = self.bucket_lengths()
        return {
            "unique_urls": self._size,
            "buckets": self.num_buckets,
            "avg_chain": self._size / self.num_buckets,
            "max_chain": max(lengths),
            "empty_buckets": lengths.count(0),
        }
