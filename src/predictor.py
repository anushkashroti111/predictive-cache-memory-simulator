from typing import Optional
from priority_heap import MaxHeap


class CachePredictor:
    def __init__(self, max_heap: MaxHeap):
        self.max_heap = max_heap

    def predict_next(self) -> Optional[str]:
        """
        Returns the URL of the highest-priority node at the root (heap[0])
        in O(1) time without modifying the heap structure.
        """
        if self.max_heap.is_empty():
            return None
        return self.max_heap.heap[0].url


def predict_next(max_heap: MaxHeap) -> Optional[str]:
    """Standalone O(1) helper function to peek at the top predicted URL."""
    if max_heap.is_empty():
        return None
    return max_heap.heap[0].url