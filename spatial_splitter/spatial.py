"""
Spatial mathematics, distance metrics, and space-filling curve indexing.

References:
- Meyer, H., & Pebesma, E. (2022). Machine learning-based global maps of ecological
  variables and the challenge of assessing them. Nature Communications, 13(1), 2208.
- Milà, C., Mateu, J., Pebesma, E., & Meyer, H. (2022). Nearest neighbour distance
  matching accounting for spatial autocorrelation in machine learning. Methods in
  Ecology and Evolution, 13(5), 1078-1087.
- Morton, G. M. (1966). A computer oriented geodetic data base and a new technique
  in file sequencing. IBM Ltd.
"""

import math
import random
from typing import List, Tuple
from .models import Point


class SpatialOptimizer:
    """
    Mitigates spatial autocorrelation by mapping geographic coordinates onto
    a 2D Morton (Z-order) space-filling curve and calculating geodesic distances.
    """

    @staticmethod
    def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points in meters using
        the Haversine formula on a spherical Earth (R = 6,371,000 m).
        """
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * (math.sin(dlam / 2.0) ** 2))
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @classmethod
    def morton_encode(cls, x_norm: float, y_norm: float, resolution: int = 16) -> int:
        """
        Interleave bits of normalized [0, 1] 2D coordinates to compute a Morton Z-code.
        Preserves spatial locality: points close in 2D space map close on the 1D curve.
        """
        max_val = (1 << resolution) - 1
        ix = min(max(int(x_norm * max_val), 0), max_val)
        iy = min(max(int(y_norm * max_val), 0), max_val)

        z = 0
        for i in range(resolution):
            z |= ((ix & (1 << i)) << i) | ((iy & (1 << i)) << (i + 1))
        return z

    @classmethod
    def sort_spatially(cls, points: List[Point], seed: int = 42) -> List[Point]:
        """
        Sort geographic points along the 2D space-filling Morton curve.
        Deterministic coordinate jitter is added to break ties without changing topology.
        """
        if not points:
            return []

        rng = random.Random(seed)
        min_lon = min(p.longitude for p in points)
        max_lon = max(p.longitude for p in points)
        min_lat = min(p.latitude for p in points)
        max_lat = max(p.latitude for p in points)

        span_lon = max(max_lon - min_lon, 1e-9)
        span_lat = max(max_lat - min_lat, 1e-9)

        indexed: List[Tuple[int, float, Point]] = []
        for p in points:
            nx = (p.longitude - min_lon) / span_lon
            ny = (p.latitude - min_lat) / span_lat
            z = cls.morton_encode(nx, ny)
            jitter = rng.uniform(-1e-5, 1e-5)
            indexed.append((z, jitter, p))

        indexed.sort(key=lambda item: (item[0], item[1]))
        return [p for _, _, p in indexed]
