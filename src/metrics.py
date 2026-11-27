"""
metrics.py
Evaluation tools for the Predictive Cache & Memory Access Simulator.
Owner: Shivangi
"""

import csv
import heapq
import os


# Top-K extraction helper
def get_top_k(heap, k):
    array = getattr(heap, "heap", heap)
    if not array or k <= 0:
        return []

    def key(index):
        node = array[index]
        # Match MaxHeap ordering, then use the array index as a final stable key.
        return (-node.frequency, -node.last_accessed_timestamp, node.url, index)

    temp = [key(0)]          # temporary structure holding candidates
    leaders = []
    while temp and len(leaders) < k:
        _, _, _, index = heapq.heappop(temp)
        leaders.append(array[index])
        for child in (2 * index + 1, 2 * index + 2):
            if child < len(array):
                heapq.heappush(temp, key(child))
    return leaders


# Hit / miss tracker
class HitMissTracker:
    

    def __init__(self):
        self.hits = 0
        self.misses = 0

    def record(self, predicted_url, actual_url):
        if predicted_url == actual_url:
            self.hits += 1
        else:
            self.misses += 1    

    @property
    def total_steps(self):
        return self.hits + self.misses

    @property
    def accuracy(self):
        if self.total_steps == 0:
            return 0.0
        return (self.hits / self.total_steps) * 100

    def summary(self):
        return {
            "total_steps": self.total_steps,
            "hits": self.hits,
            "misses": self.misses,
            "accuracy": round(self.accuracy, 2),
        }

    def export_csv(self, path, workload="unknown"):
        """Write this metrics-only summary as a single-row CSV."""
        columns = ["workload", "total_steps", "hits", "misses", "accuracy"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerow({"workload": workload, **self.summary()})


# Self-check with a fake heap: run `python metrics.py`
if __name__ == "__main__":
    from collections import namedtuple

    Node = namedtuple("Node", "url frequency last_accessed_timestamp")
    fake_heap = [
        Node("/home", 9, 40), Node("/a", 5, 30), Node("/b", 5, 35),
        Node("/c", 2, 10), Node("/d", 4, 20), Node("/e", 1, 5),
    ]
    snapshot = list(fake_heap)
    top3 = get_top_k(fake_heap, 3)
    print("Top 3:", [n.url for n in top3])          # /home, /b, /a
    print("Heap unchanged:", fake_heap == snapshot)

    tracker = HitMissTracker()
    tracker.record(None, "/home")        # nothing to predict yet -> miss
    tracker.record("/home", "/home")     # hit
    tracker.record("/home", "/a")        # miss
    tracker.record("/home", "/home")     # hit
    print(tracker.summary())             # 4 steps, 2 hits, 50.0%
    tracker.export_csv("demo_results.csv", workload="demo")
    with open("demo_results.csv", encoding="utf-8") as result_file:
        print(result_file.read())
    os.remove("demo_results.csv")
