"""
Spatial Splitter Package.

A modular library for spatial point partitioning with autocorrelation mitigation.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .models import Point
from .io import PointReader, PointWriter
from .spatial import SpatialOptimizer
from .splitters import EqualSplitter, RatioSplitter
from .diagnostics import SpatialDiagnostics
from .wizard import InteractiveWizard


class SpatialPointSplitter:
    """
    Main orchestrator pipeline: reads, optimizes, assigns classes, and exports.
    Can be used both as a library and CLI tool.
    """

    def __init__(
        self,
        mode: str = "equal",
        num_splits: int = 5,
        ratios: List[float] = [70.0, 30.0],
        ratio_names: Optional[List[str]] = None,
        stratify_col: str = "class",
        class_values: Optional[List[Any]] = None,
        class_mode: str = "one-per-file",
        add_class_id: bool = False,
        class_names: Optional[List[str]] = None,
        formats: Optional[List[str]] = None,
        prefix: Optional[str] = None,
        seed: int = 42
    ):
        self.mode = mode
        self.num_splits = num_splits
        self.ratios = ratios
        self.ratio_names = ratio_names
        self.stratify_col = stratify_col
        self.class_values = class_values
        self.class_mode = class_mode
        self.add_class_id = add_class_id or (class_names is not None and len(class_names) > 0)
        self.class_names = class_names
        self.formats = formats or ["csv", "geojson"]
        self.prefix = prefix
        self.seed = seed

    def process(
        self,
        input_path: Union[str, Path],
        output_dir: Union[str, Path],
        lat_col: Optional[str] = None,
        lon_col: Optional[str] = None,
        id_col: Optional[str] = None,
        stratify_col: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute the complete spatial splitting and export pipeline."""
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        effective_stratify = stratify_col or self.stratify_col

        print(f"\n[1/4] Reading points from: {input_path}...")
        points = PointReader.read(
            input_path,
            lat_col=lat_col,
            lon_col=lon_col,
            id_col=id_col,
            class_col=effective_stratify
        )
        total_points = len(points)
        print(f"      Loaded {total_points} valid geographic points.")

        if self.mode == "ratio":
            ratio_str = ":".join(str(int(r) if r.is_integer() else r) for r in self.ratios)
            print(f"[2/4] Executing Spatially-Stratified Ratio Split ({ratio_str}) on column '{effective_stratify}'...")
            splits = RatioSplitter.split(
                points=points,
                ratios=self.ratios,
                names=self.ratio_names,
                stratify_col=effective_stratify,
                add_class_id=self.add_class_id,
                class_names=self.class_names,
                seed=self.seed
            )
        else:
            print(f"[2/4] Executing Equal N-Way Spatial Split into {self.num_splits} subsets (mode: '{self.class_mode}')...")
            splits = EqualSplitter.split(
                points=points,
                num_splits=self.num_splits,
                class_values=self.class_values,
                class_mode=self.class_mode,
                add_class_id=self.add_class_id,
                class_names=self.class_names,
                seed=self.seed
            )

        print(f"[3/4] Mitigating spatial autocorrelation & verifying geographic dispersion...")
        diagnostics = SpatialDiagnostics.analyze_splits(splits)

        print(f"[4/4] Exporting formats {self.formats} to: {output_dir.resolve()}...")
        created_files = PointWriter.write_splits(
            splits,
            output_dir,
            formats=self.formats,
            prefix=self.prefix
        )

        self._print_report(diagnostics, created_files, output_dir)

        return {
            "total_points": total_points,
            "mode": self.mode,
            "created_files": [str(f) for f in created_files],
            "diagnostics": diagnostics
        }

    @staticmethod
    def _print_report(
        diagnostics: Dict[str, Any],
        created_files: List[Path],
        output_dir: Path
    ) -> None:
        """Display clean terminal verification report."""
        print("\n" + "=" * 70)
        print(" SPATIAL SPLITTING & AUTOCORRELATION MITIGATION REPORT")
        print("=" * 70)
        for key, stats in diagnostics.items():
            print(f" File / Subset: {key}")
            print(f"   Points: {stats['point_count']}")
            print(f"   Class Distribution: {stats['class_distribution']}")
            print(f"   Mean Nearest Neighbor: {stats['mean_nearest_neighbor_m']} m")
            print(f"   Min Nearest Neighbor:  {stats['min_nearest_neighbor_m']} m")
            print(f"   Bounding Box: [minX, minY, maxX, maxY] = {stats['bbox']}")
        print("=" * 70)
        print(f" Successfully generated {len(created_files)} files in: {output_dir.resolve()}\n")


__all__ = [
    "Point",
    "PointReader",
    "PointWriter",
    "SpatialOptimizer",
    "EqualSplitter",
    "RatioSplitter",
    "SpatialDiagnostics",
    "InteractiveWizard",
    "SpatialPointSplitter",
]
