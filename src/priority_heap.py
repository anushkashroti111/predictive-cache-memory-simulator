class CacheNode:
    def __init__(self, url: str, timestamp: int, frequency: int = 1, heap_index: int = -1):
        self.url = url
        self.frequency = frequency
        self.last_accessed_timestamp = timestamp
        self.heap_index = heap_index

    def __repr__(self):
        return (f"CacheNode(url='{self.url}', freq={self.frequency}, "
                f"ts={self.last_accessed_timestamp}, idx={self.heap_index})")


class MaxHeap:
    def __init__(self):
        # Internal array structure to hold CacheNode objects
        self.heap = []

    def __len__(self):
        return len(self.heap)

    def is_empty(self) -> bool:
        return len(self.heap) == 0

    def raw_insert(self, node: CacheNode) -> None:
        """Appends a new node to the heap array and sets its initial heap_index."""
        node.heap_index = len(self.heap)
        self.heap.append(node)

    def swap_nodes(self, i: int, j: int) -> None:
        """Swaps two nodes in the array and keeps their heap_index attributes synchronized."""
        if i == j:
            return
        self.heap[i], self.heap[j] = self.heap[j], self.heap[i]
        self.heap[i].heap_index = i
        self.heap[j].heap_index = j