"""
Spatial diagnostics and validation reporter.

References:
- Milà, C., Mateu, J., Pebesma, E., & Meyer, H. (2022). Nearest neighbour distance
  matching accounting for spatial autocorrelation in machine learning.
  Methods in Ecology and Evolution, 13(5), 1078-1087.
"""

from typing import Any, Dict, List
from .models import Point
from .spatial import SpatialOptimizer


class SpatialDiagnostics:
    """Computes spatial dispersion and nearest-neighbor distance metrics."""

    @classmethod
    def analyze_splits(cls, splits: Dict[str, List[Point]]) -> Dict[str, Any]:
        """Compute spatial statistics per split and class."""
        report = {}
        for split_key, pts in splits.items():
            if not pts:
                continue

            # Class count distribution
            class_counts: Dict[Any, int] = {}
            for p in pts:
                class_counts[p.class_val] = class_counts.get(p.class_val, 0) + 1

            # Nearest-neighbor distance analysis (meters)
            nn_distances: List[float] = []
            if len(pts) > 1:
                for i, p1 in enumerate(pts):
                    min_dist = float("inf")
                    for j, p2 in enumerate(pts):
                        if i == j:
                            continue
                        d = SpatialOptimizer.haversine_distance_m(
                            p1.latitude, p1.longitude, p2.latitude, p2.longitude
                        )
                        if d < min_dist:
                            min_dist = d
                    nn_distances.append(min_dist)

            mean_nn = sum(nn_distances) / len(nn_distances) if nn_distances else 0.0
            min_nn = min(nn_distances) if nn_distances else 0.0

            lons = [p.longitude for p in pts]
            lats = [p.latitude for p in pts]

            report[split_key] = {
                "point_count": len(pts),
                "class_distribution": class_counts,
                "mean_nearest_neighbor_m": round(mean_nn, 1),
                "min_nearest_neighbor_m": round(min_nn, 1),
                "bbox": [round(min(lons), 4), round(min(lats), 4), round(max(lons), 4), round(max(lats), 4)]
            }
        return report
