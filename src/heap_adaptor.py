"""
heap_adapter.py  --  TEMPORARY COMPATIBILITY SHIM
=================================================
Prefers Eetal's real classes from priority_heap.py. Only if that module
is missing does it define minimal stand-ins with the SAME interface.

WIRING EETAL'S REAL CLASSES: nothing to change. Once priority_heap.py is on
the path, the import below succeeds and the fallback is never used.
(Later, you can replace `from heap_adapter import ...` with
`from priority_heap import ...` in cache_map.py / ingestion.py and delete this file.)
"""
try:
    from priority_heap import CacheNode, MaxHeap
    USING_FALLBACK = False
except ImportError:  # ---- FALLBACK START (delete once priority_heap.py exists) ----
    USING_FALLBACK = True

    class CacheNode:
        def __init__(self, url, timestamp, frequency=1, heap_index=-1):
            self.url = url
            self.frequency = frequency
            self.last_accessed_timestamp = timestamp
            self.heap_index = heap_index

    class MaxHeap:
        def __init__(self):
            self.heap = []

        def __len__(self):
            return len(self.heap)

        def is_empty(self):
            return not self.heap

        def raw_insert(self, node):
            node.heap_index = len(self.heap)
            self.heap.append(node)

        def swap_nodes(self, i, j):
            if i == j:
                return
            self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
            self.heap[i].heap_index = i
            self.heap[j].heap_index = j

        def is_higher_priority(self, a, b):
            if a.frequency != b.frequency:
                return a.frequency > b.frequency
            return a.last_accessed_timestamp > b.last_accessed_timestamp

        def sift_up(self, index):
            while index > 0:
                parent = (index - 1) // 2
                if self.is_higher_priority(self.heap[index], self.heap[parent]):
                    self.swap_nodes(index, parent)
                    index = parent
                else:
                    break

        def sift_down(self, index):
            size = len(self.heap)
            while True:
                best, l, r = index, 2 * index + 1, 2 * index + 2
                if l < size and self.is_higher_priority(self.heap[l], self.heap[best]):
                    best = l
                if r < size and self.is_higher_priority(self.heap[r], self.heap[best]):
                    best = r
                if best == index:
                    break
                self.swap_nodes(index, best)
                index = best
    # ---- FALLBACK END ----