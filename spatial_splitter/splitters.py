"""
Splitting engines for Equal N-Way spatial partitioning and Stratified Ratio splitting.

References:
- Valavi, R., Elith, J., Lahoz-Monfort, J. J., & Guillera-Arroita, G. (2021).
  blockCV: An R package for generating spatially or environmentally separated folds
  for k-fold cross-validation of species distribution models. Methods in Ecology and Evolution.
- Wadoux, A. M. J. C., Heuvelink, G. B., de Bruin, S., & Brus, D. J. (2021).
  Spatial cross-validation is not the right way to evaluate map accuracy.
  Ecological Modelling, 457, 109692.
- Schratz, P., Muenchow, J., Iturritxa, E., Richter, J., & Brenning, A. (2021).
  Hyperparameter tuning and performance assessment of statistical and machine-learning
  models using spatial data. Ecological Modelling, 440, 109413.
"""

import random
from typing import Any, Dict, List, Optional
from .models import Point
from .spatial import SpatialOptimizer


class EqualSplitter:
    """
    Splits points into N equal subsets while mitigating spatial autocorrelation.
    Points are ordered along a 2D Morton curve and allocated via randomized round-robin
    to ensure each subset has broad, uniform coverage without spatial clustering.
    """

    @classmethod
    def split(
        cls,
        points: List[Point],
        num_splits: int,
        class_values: Optional[List[Any]] = None,
        class_mode: str = "one-per-file",
        add_class_id: bool = False,
        class_names: Optional[List[str]] = None,
        seed: int = 42
    ) -> Dict[str, List[Point]]:
        """Partition points into num_splits equal subsets."""
        if not points:
            return {}

        sorted_pts = SpatialOptimizer.sort_spatially(points, seed=seed)
        splits: Dict[int, List[Point]] = {i: [] for i in range(1, num_splits + 1)}
        rng = random.Random(seed)

        # Allocate in small spatial blocks using randomized round-robin
        for block_start in range(0, len(sorted_pts), num_splits):
            block = sorted_pts[block_start:block_start + num_splits]
            s_ids = list(range(1, num_splits + 1))
            rng.shuffle(s_ids)
            for pt, s_id in zip(block, s_ids):
                pt.split_id = s_id
                splits[s_id].append(pt)

        # Class values resolution
        if class_values is None:
            class_values = list(range(1, num_splits + 1))
        elif len(class_values) < num_splits:
            class_values = list(class_values) + list(range(len(class_values) + 1, num_splits + 1))

        named_splits: Dict[str, List[Point]] = {}

        if class_mode == "one-per-file":
            for idx, (s_id, pts) in enumerate(splits.items()):
                c_val = class_values[idx]
                c_name = class_names[idx] if (class_names and idx < len(class_names)) else f"class_{c_val}"
                
                for i, p in enumerate(pts):
                    p.class_val = c_val
                    if add_class_id or class_names:
                        p.class_id = f"{c_name}_{i + 1}"

                # Name output split based on class name if custom name provided, else class_{c_val}
                split_key = c_name if (class_names and idx < len(class_names)) else f"class_{c_val}"
                named_splits[split_key] = pts

        elif class_mode == "balanced":
            for s_id, pts in splits.items():
                pts.sort(key=lambda p: (p.latitude, p.longitude))
                cycle = list(class_values)
                interleaved: List[Any] = []
                while len(interleaved) < len(pts):
                    c = list(cycle)
                    rng.shuffle(c)
                    interleaved.extend(c)
                interleaved = interleaved[:len(pts)]
                
                class_counters: Dict[Any, int] = {}
                for pt, cv in zip(pts, interleaved):
                    pt.class_val = cv
                    if add_class_id or class_names:
                        class_counters[cv] = class_counters.get(cv, 0) + 1
                        pt.class_id = f"class_{cv}_{class_counters[cv]}"
                
                named_splits[f"split_{s_id}"] = pts
        else:
            raise ValueError(f"Unknown class_mode: '{class_mode}'. Choose 'one-per-file' or 'balanced'.")

        return named_splits


class RatioSplitter:
    """
    Performs spatially-stratified ratio splitting (e.g. 70:30 Train/Test or 60:20:20 Train/Val/Test).
    Preserves exact class ratios while mitigating spatial autocorrelation through
    spatially-interleaved sampling along the Morton space-filling curve.
    """

    @classmethod
    def split(
        cls,
        points: List[Point],
        ratios: List[float] = [70.0, 30.0],
        names: Optional[List[str]] = None,
        stratify_col: str = "class",
        add_class_id: bool = False,
        class_names: Optional[List[str]] = None,
        seed: int = 42
    ) -> Dict[str, List[Point]]:
        """
        Partition points according to specified ratios, stratified by class/target column.
        """
        if not points:
            return {}

        total_ratio = sum(ratios)
        norm_ratios = [r / total_ratio for r in ratios]

        if names is None:
            if len(ratios) == 2:
                names = [f"train_{int(norm_ratios[0]*100)}", f"test_{int(norm_ratios[1]*100)}"]
            elif len(ratios) == 3:
                names = [f"train_{int(norm_ratios[0]*100)}", f"val_{int(norm_ratios[1]*100)}", f"test_{int(norm_ratios[2]*100)}"]
            else:
                names = [f"split_{i+1}" for i in range(len(ratios))]

        # Group points by class/stratification column
        groups: Dict[Any, List[Point]] = {}
        for p in points:
            c_val = p.class_val
            if c_val is None and stratify_col in p.properties:
                c_val = p.properties[stratify_col]
            if c_val is None:
                c_val = "unclassified"
            p.class_val = c_val
            groups.setdefault(c_val, []).append(p)

        output_splits: Dict[str, List[Point]] = {name: [] for name in names}

        # For each class group, sort spatially and distribute points according to ratio
        for c_val, group_pts in groups.items():
            sorted_group = SpatialOptimizer.sort_spatially(group_pts, seed=seed)
            n_group = len(sorted_group)

            # Target point counts per split for this class
            counts = [int(round(r * n_group)) for r in norm_ratios]
            diff = n_group - sum(counts)
            if diff != 0:
                counts[0] += diff

            # Spatial stratified interleaved allocation
            stratified_assignment = [None] * n_group
            for split_idx, count in enumerate(counts):
                if count <= 0:
                    continue
                step_val = n_group / count
                for step_i in range(count):
                    pos = int((step_i + (split_idx * 0.33)) * step_val) % n_group
                    while stratified_assignment[pos] is not None:
                        pos = (pos + 1) % n_group
                    stratified_assignment[pos] = split_idx

            for pt, s_idx in zip(sorted_group, stratified_assignment):
                target_name = names[s_idx if s_idx is not None else 0]
                pt.split_id = target_name
                output_splits[target_name].append(pt)

        # Assign unique class_id if requested
        if add_class_id or class_names:
            for s_name, pts in output_splits.items():
                class_counters: Dict[Any, int] = {}
                for pt in pts:
                    c = pt.class_val
                    class_counters[c] = class_counters.get(c, 0) + 1
                    pt.class_id = f"{c}_{class_counters[c]}"

        return output_splits
