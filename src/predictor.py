from typing import Optional
from priority_heap import MaxHeap


class CachePredictor:
    def __init__(self, max_heap: MaxHeap):
        self.max_heap = max_heap

    def predict_next(self) -> Optional[str]:
        if self.max_heap.is_empty():
            return None
        return self.max_heap.heap[0].url


def predict_next(max_heap: MaxHeap) -> Optional[str]:
    if max_heap.is_empty():
        return None
    return max_heap.heap[0].url