"""
workloads.py
Owner: Shivangi
"""

import random
from dataclasses import dataclass


WEB_SERVER_LOG_DATASET = "mindweave/web-server-logs"


def load_web_server_log_urls(limit=None):
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool) or limit < 0
    ):
        raise ValueError("limit must be a non-negative integer or None")

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
        ) from exc

    servers = load_dataset(WEB_SERVER_LOG_DATASET, "servers")
    access_logs = load_dataset(WEB_SERVER_LOG_DATASET, "access_logs")
    server_ids = {row["id"] for row in servers["train"]}

    def request_paths():
        count = 0
        if limit == 0:
            return
        for row in access_logs["train"]:
            if row["server_id"] not in server_ids:
                raise ValueError(
                    f"access log references unknown server id {row['server_id']!r}"
                )
            path = row["path"]
            if not isinstance(path, str) or not path.strip():
                raise ValueError(f"access log has an invalid path: {path!r}")
            yield path
            count += 1
            if limit is not None and count >= limit:
                break

    return request_paths()


# Event model
@dataclass
class NavigationEvent:
    """One user click: moving from one page to another."""
    step: int             
    source_url: str        
    destination_url: str   


def to_events(urls):
    """Convert a list of URLs into a list of NavigationEvent objects."""
    events = []
    previous = None
    for step, url in enumerate(urls):
        events.append(NavigationEvent(step, previous, url))
        previous = url
    return events


# Page pool: 50 pages of one website
PAGE_POOL = ["/home"] + [f"/page{i}" for i in range(1, 50)]  


# Random traffic: no pattern at all (baseline / worst case)
def generate_random_traffic(length=10000, pool=PAGE_POOL, seed=42):
    """Return `length` URLs picked uniformly at random from `pool`."""
    rng = random.Random(seed)  # own generator, so results are reproducible
    return [rng.choice(pool) for _ in range(length)]


# Looping traffic: A -> B -> C -> A -> B -> C ... (pure recency pattern)
def generate_looping_traffic(length=10000, pattern=None):
    """Return `length` URLs that repeat `pattern` over and over."""
    if pattern is None:
        pattern = ["/pageA", "/pageB", "/pageC"]
    if not pattern:
        raise ValueError("pattern must contain at least one URL")
    return [pattern[i % len(pattern)] for i in range(length)]


# Zipfian traffic: a few pages get most of the clicks (real-world skew)
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


# Quick self-check: run `python workloads.py`
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
