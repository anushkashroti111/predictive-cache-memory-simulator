"""
cache_map.py - Hash Map Layer (Owner: Priyanshi)

Maps a page URL to its CacheNode (frequency + last access time) using a
hash table built from scratch: a list of buckets (separate chaining) and an
FNV-1a hash function. No dict / set / Counter is used inside the map.

Complexity: average O(1) per operation while chains are short (the table
doubles when load factor exceeds `max_load_factor`); worst case O(n) if every
URL lands in one bucket. Space is O(n) for n unique URLs.
"""

from typing import Iterator, List, Optional

from priority_heap import CacheNode  # single shared node class (Eetal's)

# FNV-1a 32-bit constants (public, standard values)
FNV_OFFSET_BASIS = 2166136261
FNV_PRIME = 16777619


def fnv1a_hash(key: str) -> int:
    """32-bit FNV-1a hash of a string."""
    hash_value = FNV_OFFSET_BASIS
    for byte in key.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * FNV_PRIME) & 0xFFFFFFFF
    return hash_value


def normalize_url(raw) -> Optional[str]:
    """
    Clean a raw URL: strip surrounding whitespace and lowercase it.
    Returns None for anything unusable (not a string, empty, or containing
    internal whitespace), so callers can reject it gracefully.
    """
    if not isinstance(raw, str):
        return None
    url = raw.strip().lower()
    if not url or any(ch.isspace() for ch in url):
        return None
    return url


class CustomHashMap:
    DEFAULT_BUCKETS = 1024
    DEFAULT_MAX_LOAD = 0.75

    def __init__(self, num_buckets: int = DEFAULT_BUCKETS,
                 max_load_factor: Optional[float] = DEFAULT_MAX_LOAD):
        if not isinstance(num_buckets, int) or isinstance(num_buckets, bool) or num_buckets < 1:
            raise ValueError("num_buckets must be an integer >= 1")
        if max_load_factor is not None and max_load_factor <= 0:
            raise ValueError("max_load_factor must be positive or None")
        self.num_buckets = num_buckets
        self.max_load_factor = max_load_factor      # None disables resizing
        # List of lists: buckets[i] is the chain of nodes hashing to i.
        self.buckets: List[List[CacheNode]] = [[] for _ in range(num_buckets)]
        self._size = 0

    # ---------- helpers ----------

    @property
    def bucket_count(self) -> int:
        return self.num_buckets

    @staticmethod
    def _is_valid_url(url) -> bool:
        """A usable key is a non-empty string (cleaning is normalize_url's job)."""
        return isinstance(url, str) and url.strip() != ""

    def _bucket_index(self, url: str) -> int:
        """URL -> number in 0 .. num_buckets-1."""
        return fnv1a_hash(url) % self.num_buckets

    def _resize(self, new_count: int) -> None:
        """Rehash every node into a bigger table. Node objects are reused,
        so heap_index values and heap references stay valid."""
        new_buckets: List[List[CacheNode]] = [[] for _ in range(new_count)]
        for bucket in self.buckets:
            for node in bucket:
                new_buckets[fnv1a_hash(node.url) % new_count].append(node)
        self.buckets = new_buckets
        self.num_buckets = new_count

    # ---------- required API ----------

    def insert(self, url: str) -> CacheNode:
        """
        Return the node for `url`, creating it if the URL is unseen.

        A new node starts at frequency 0, timestamp 0, heap_index -1; the
        ingestion pipeline updates it right after. An existing URL returns the
        existing node (nothing duplicated). Invalid URLs raise ValueError.
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
        if (self.max_load_factor is not None
                and self._size / self.num_buckets > self.max_load_factor):
            self._resize(self.num_buckets * 2)
        return node

    def get(self, url: str) -> Optional[CacheNode]:
        """Find the node for `url` by walking its bucket chain; None if absent."""
        if not self._is_valid_url(url):
            return None
        for node in self.buckets[self._bucket_index(url)]:
            if node.url == url:
                return node
        return None

    def update_access(self, url: str, tick: int) -> CacheNode:
        """frequency += 1 and timestamp = tick. Does NOT touch heap_index."""
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
        return self._size

    def __contains__(self, url) -> bool:
        return self.get(url) is not None

    def nodes(self) -> Iterator[CacheNode]:
        for bucket in self.buckets:
            for node in bucket:
                yield node

    def bucket_lengths(self) -> List[int]:
        return [len(bucket) for bucket in self.buckets]

    def stats(self) -> dict:
        lengths = self.bucket_lengths()
        return {
            "unique_urls": self._size,
            "buckets": self.num_buckets,
            "avg_chain": self._size / self.num_buckets,
            "max_chain": max(lengths),
            "empty_buckets": lengths.count(0),
        }