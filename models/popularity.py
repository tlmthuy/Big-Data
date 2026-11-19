"""Group's cumulative train-only baseline (not supplied by NVIDIA notebook 03)."""

from collections import Counter

from evaluation.ranking import K


class Popularity:
    def __init__(self, catalog):
        self.catalog = catalog
        self.counts = Counter()
        self.trained_days = set()

    def update_partition(self, day, rows):
        """Count each retained train interaction once, regardless of neural epochs."""
        if day in self.trained_days or (self.trained_days and day <= max(self.trained_days)):
            raise ValueError("Train partitions must be updated exactly once, in order")
        counts = Counter()
        n_sessions = 0
        for row in rows:
            if row["split"] != "train" or row["day_index"] != day:
                raise ValueError("Only the requested train partition may update popularity")
            counts.update(self.catalog.sequence(row["product_ids"]))
            n_sessions += 1
        if not n_sessions:
            raise ValueError("Requested train partition is empty")
        self.counts.update(counts)
        self.trained_days.add(day)

    def recommend(self):
        """Unseen catalog items have score zero; ties use encoded ID ascending."""
        return sorted(self.catalog.products, key=lambda item: (-self.counts[item], item))[:K]
