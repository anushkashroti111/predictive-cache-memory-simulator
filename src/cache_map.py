#cache_map.py - Hash Map Layer (Owner: Priyanshi)

from typing import Iterator, List, Optional

from priority_heap import CacheNode 

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
        self.max_load_factor = max_load_factor    
        # List of lists: buckets[i] is the chain of nodes hashing to i.
        self.buckets: List[List[CacheNode]] = [[] for _ in range(num_buckets)]
        self._size = 0

    #helper methods

    @property
    def bucket_count(self) -> int:
        return self.num_buckets

    @staticmethod
    def _is_valid_url(url) -> bool:
        return isinstance(url, str) and url.strip() != ""

    def _bucket_index(self, url: str) -> int:
        return fnv1a_hash(url) % self.num_buckets

    def _resize(self, new_count: int) -> None:
        new_buckets: List[List[CacheNode]] = [[] for _ in range(new_count)]
        for bucket in self.buckets:
            for node in bucket:
                new_buckets[fnv1a_hash(node.url) % new_count].append(node)
        self.buckets = new_buckets
        self.num_buckets = new_count

    # required methods for the cache map

    def insert(self, url: str) -> CacheNode:
        if not self._is_valid_url(url):
            raise ValueError(f"invalid URL: {url!r}")
        bucket = self.buckets[self._bucket_index(url)]
        for node in bucket:                     
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

    # extras (tests, benchmarks, report numbers)

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