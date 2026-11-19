"""Single-target metrics on ranked real-item IDs; standard-library implementation.

Reference: NVIDIA Transformers4Rec f0ca2b5343dd1e40b5d2422b942f014b224f5c20,
transformers4rec/torch/ranking_metric.py (RecallAt, DCGAt, NDCGAt), Apache-2.0.
Written independently for ranked IDs rather than torch score/one-hot tensors.
"""

from math import log2

K = 20


def score_session(target, ranked_items):
    """Return (Recall@20, NDCG@20); malformed rankings are errors, not misses."""
    ranked_items = list(ranked_items)
    if len(set(ranked_items)) != len(ranked_items):
        raise ValueError("Predictions must contain distinct item IDs")
    try:
        rank = ranked_items[:K].index(target) + 1
    except ValueError:
        return 0.0, 0.0
    return 1.0, 1.0 / log2(rank + 1)


class RankingMetrics:
    """Accumulate per-session sums, so uneven batches/days get correct weight."""

    def __init__(self):
        self.count = 0
        self.recall_sum = 0.0
        self.ndcg_sum = 0.0

    def update(self, target, ranked_items):
        recall, ndcg = score_session(target, ranked_items)
        self.count += 1
        self.recall_sum += recall
        self.ndcg_sum += ndcg

    def compute(self):
        if not self.count:
            raise ValueError("No valid evaluation sessions; metrics are undefined")
        return {
            "n_sessions": self.count,
            "Recall@20": self.recall_sum / self.count,
            "NDCG@20": self.ndcg_sum / self.count,
            "recall_sum": self.recall_sum,
            "ndcg_sum": self.ndcg_sum,
        }
