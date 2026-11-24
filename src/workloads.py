"""
workloads.py
Traffic generators for the Predictive Cache & Memory Access Simulator.

Every generator returns a plain list of URL strings, so any workload
can be plugged into the simulator the same way.
"""

import random
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------
@dataclass
class NavigationEvent:
    """One user click: moving from one page to another."""
    step: int              # position in the traffic stream (0, 1, 2, ...)
    source_url: str        # page the user was on (None for the first request)
    destination_url: str   # page the user requested


def to_events(urls):
    """Convert a list of URLs into a list of NavigationEvent objects."""
    events = []
    previous = None
    for step, url in enumerate(urls):
        events.append(NavigationEvent(step, previous, url))
        previous = url
    return events


# ---------------------------------------------------------------------------
# Page pool: 50 pages of one website
# ---------------------------------------------------------------------------
PAGE_POOL = ["/home"] + [f"/page{i}" for i in range(1, 50)]  # 50 pages


# ---------------------------------------------------------------------------
# Random traffic: no pattern at all (baseline / worst case)
# ---------------------------------------------------------------------------
def generate_random_traffic(length=10000, pool=PAGE_POOL, seed=42):
    """Return `length` URLs picked uniformly at random from `pool`."""
    rng = random.Random(seed)  # own generator, so results are reproducible
    return [rng.choice(pool) for _ in range(length)]


# ---------------------------------------------------------------------------
# Looping traffic: A -> B -> C -> A -> B -> C ... (pure recency pattern)
# ---------------------------------------------------------------------------
def generate_looping_traffic(length=10000, pattern=None):
    """Return `length` URLs that repeat `pattern` over and over."""
    if pattern is None:
        pattern = ["/pageA", "/pageB", "/pageC"]
    if not pattern:
        raise ValueError("pattern must contain at least one URL")
    return [pattern[i % len(pattern)] for i in range(length)]


# ---------------------------------------------------------------------------
# Zipfian traffic: a few pages get most of the clicks (real-world skew)
# ---------------------------------------------------------------------------
def generate_zipfian_traffic(length=10000, pool=PAGE_POOL, exponent=1.35, seed=42):
    """
    Return `length` URLs where page popularity follows a Zipf distribution.

    The page at rank r (1 = most popular) gets weight 1 / r**exponent.
    pool[0] ("/home") is rank 1, so it is the most visited page.
    With 50 pages and exponent 1.35, the top 20% of pages (10 pages)
    receive about 80% of all clicks.
    """
    rng = random.Random(seed)
    weights = [1.0 / (rank ** exponent) for rank in range(1, len(pool) + 1)]
    return rng.choices(pool, weights=weights, k=length)


# ---------------------------------------------------------------------------
# Quick self-check: run `python workloads.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    rand = generate_random_traffic()
    print("Random  :", len(rand), "requests, first 10:", rand[:10])
    print("Unique pages used:", len(set(rand)))

    loop = generate_looping_traffic(length=9)
    print("Looping :", loop)

    for event in to_events(loop[:4]):
        print(event)

    from collections import Counter
    zipf = generate_zipfian_traffic(length=100000)
    counts = Counter(zipf).most_common()
    top_20_percent = sum(c for _, c in counts[: len(PAGE_POOL) // 5])
    print("Zipfian : top 5 pages:", counts[:5])
    print("Share of clicks going to top 20% of pages: "
          f"{100 * top_20_percent / len(zipf):.1f}%")
