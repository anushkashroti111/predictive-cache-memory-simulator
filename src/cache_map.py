"""
cache_map.py  --  Custom Hash Map (separate chaining) for the Predictive Cache Simulator.

Owner: Priyanshi (Hash Map & Ingestion Lead)

Maps  normalized URL string -> CacheNode  in O(1) average time.
The map only stores *references* to CacheNode objects; the same objects live
in Eetal's MaxHeap, so updating a node here updates it there too.
"""
from typing import Iterator, List, Optional

from heap_adapter import CacheNode

DEFAULT_BUCKET_COUNT = 2048   # initial table size (plan suggests 1024 or 2048)
MAX_LOAD_FACTOR = 0.75        # grow the table when size / buckets exceeds this

# FNV-1a 32-bit constants
_FNV_OFFSET_BASIS = 0x811C9DC5
_FNV_PRIME = 0x01000193
_MASK_32 = 0xFFFFFFFF


# --------------------------------------------------------------------------
# URL normalization
# --------------------------------------------------------------------------
def normalize_url(raw_url) -> Optional[str]:
    """
    Clean a raw URL. Returns the normalized string, or None if invalid.

    Steps: reject non-strings -> strip whitespace -> lowercase ->
    reject empty strings and strings with internal whitespace/control chars.
    """
    if not isinstance(raw_url, str):
        return None
    url = raw_url.strip().lower()
    if not url:
        return None
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return None
    return url


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------
def fnv1a_hash(text: str) -> int:
    """32-bit FNV-1a hash of `text` (UTF-8 bytes). Deterministic across runs."""
    h = _FNV_OFFSET_BASIS
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * _FNV_PRIME) & _MASK_32
    return h


# --------------------------------------------------------------------------
# Hash map
# --------------------------------------------------------------------------
class CustomHashMap:
    """
    Hash map using separate chaining: each bucket is a Python list of
    CacheNode references. Keys must already be normalized (see normalize_url);
    the IngestionEngine does that before calling in here.
    """

    def __init__(self, bucket_count: int = DEFAULT_BUCKET_COUNT):
        if not isinstance(bucket_count, int) or bucket_count <= 0:
            raise ValueError("bucket_count must be a positive integer")
        self._buckets: List[List[CacheNode]] = [[] for _ in range(bucket_count)]
        self._size = 0

    # ---- introspection ----
    @property
    def bucket_count(self) -> int:
        return len(self._buckets)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, url: str) -> bool:
        return self.get(url) is not None

    def __iter__(self) -> Iterator[CacheNode]:
        for bucket in self._buckets:
            yield from bucket

    # ---- core operations ----
    def _bucket_index(self, url: str) -> int:
        """Convert a URL into a valid bucket index in [0, bucket_count)."""
        return fnv1a_hash(url) % len(self._buckets)

    def get(self, url: str) -> Optional[CacheNode]:
        """
        Return the node for `url`, or None if absent.
        Hash collisions are handled by scanning the bucket and comparing the
        actual URL strings. Average O(1) given a healthy load factor.
        """
        for node in self._buckets[self._bucket_index(url)]:
            if node.url == url:
                return node
        return None

    def insert(self, node: CacheNode) -> bool:
        """
        Add `node` if its URL is unseen. Returns True if inserted, False if the
        URL already exists (the existing node is NOT overwritten).
        """
        bucket = self._buckets[self._bucket_index(node.url)]
        for existing in bucket:
            if existing.url == node.url:
                return False
        bucket.append(node)
        self._size += 1
        if self._size / len(self._buckets) > MAX_LOAD_FACTOR:
            self._resize(len(self._buckets) * 2)
        return True

    def _resize(self, new_bucket_count: int) -> None:
        """
        Rehash every node into a bigger table. Nodes themselves are reused, so
        their heap_index stays valid; only the bucket lists change.
        """
        old_buckets = self._buckets
        self._buckets = [[] for _ in range(new_bucket_count)]
        for bucket in old_buckets:
            for node in bucket:
                self._buckets[self._bucket_index(node.url)].append(node)