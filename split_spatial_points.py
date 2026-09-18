#!/usr/bin/env python3
"""
Spatial Point Splitter CLI & Entrypoint.

Partition GeoJSON/CSV points while mitigating spatial autocorrelation.
Supports both Interactive Wizard and full CLI arguments.

Scientific References:
- Meyer & Pebesma (2022). Nature Communications, 13(1), 2208.
- Milà et al. (2022). Methods in Ecology and Evolution, 13(5), 1078-1087.
- Valavi et al. (2021). Methods in Ecology and Evolution.
"""

import argparse
import sys
from pathlib import Path

# Import from modular package
from spatial_splitter import (
    Point,
    PointReader,
    PointWriter,
    SpatialOptimizer,
    EqualSplitter,
    RatioSplitter,
    SpatialDiagnostics,
    InteractiveWizard,
    SpatialPointSplitter,
)


def build_parser() -> argparse.ArgumentParser:
    """Build command-line arguments parser."""
    parser = argparse.ArgumentParser(
        description="Spatial Point Splitter: Partition GeoJSON/CSV points while mitigating spatial autocorrelation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=None,
        help="Path to input point file (.geojson or .csv). If omitted, launches interactive wizard."
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["equal", "ratio"],
        default="equal",
        help="Splitting mode: 'equal' (N equal subsets) or 'ratio' (stratified ratio split like 70:30)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("output_splits"),
        help="Directory to save generated split files"
    )
    parser.add_argument(
        "-n", "--num-splits",
        type=int,
        default=5,
        help="[Equal Mode] Number of separate files to create"
    )
    parser.add_argument(
        "-c", "--classes",
        nargs="+",
        default=None,
        help="[Equal Mode] Class values to assign (defaults to 1..num_splits)"
    )
    parser.add_argument(
        "--class-mode",
        type=str,
        choices=["one-per-file", "balanced"],
        default="one-per-file",
        help="[Equal Mode] 'one-per-file': 1 class per file; 'balanced': even mix of classes in each file"
    )
    parser.add_argument(
        "-r", "--ratio",
        nargs="+",
        type=float,
        default=[70.0, 30.0],
        help="[Ratio Mode] Ratio fractions/percentages (e.g., -r 70 30 or -r 80 20)"
    )
    parser.add_argument(
        "--ratio-names",
        nargs="+",
        default=None,
        help="[Ratio Mode] Names for ratio split files (e.g., --ratio-names train test)"
    )
    parser.add_argument(
        "--stratify-by",
        type=str,
        default="class",
        help="[Ratio Mode] Column name in dataset to stratify across splits"
    )
    parser.add_argument(
        "-f", "--formats",
        type=str,
        default="csv,geojson",
        help="Comma-separated list of formats to export: csv, geojson"
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Optional prefix for output filenames"
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible spatial stratification"
    )
    parser.add_argument(
        "-I", "--interactive",
        action="store_true",
        help="Force launch interactive terminal wizard taking inputs one by one"
    )
    parser.add_argument(
        "--add-class-id",
        action="store_true",
        help="Generate a unique serial class_id for each point (e.g. water_1, water_2)"
    )
    parser.add_argument(
        "--class-names",
        nargs="+",
        default=None,
        help="Custom text class names for splits (e.g. --class-names water vegetation urban)"
    )
    parser.add_argument(
        "--lat-col",
        type=str,
        default=None,
        help="Custom latitude column name for CSV"
    )
    parser.add_argument(
        "--lon-col",
        type=str,
        default=None,
        help="Custom longitude column name for CSV"
    )
    parser.add_argument(
        "--id-col",
        type=str,
        default=None,
        help="Custom ID column name"
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Launch interactive questionnaire if no input file provided or flag specified
    if args.interactive or args.input is None:
        InteractiveWizard.run(SpatialPointSplitter)
        return

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    class_vals = args.classes if args.classes is not None else list(range(1, args.num_splits + 1))

    splitter = SpatialPointSplitter(
        mode=args.mode,
        num_splits=args.num_splits,
        ratios=args.ratio,
        ratio_names=args.ratio_names,
        stratify_col=args.stratify_by,
        class_values=class_vals,
        class_mode=args.class_mode,
        add_class_id=args.add_class_id,
        class_names=args.class_names,
        formats=formats,
        prefix=args.prefix,
        seed=args.seed
    )

    try:
        splitter.process(
            input_path=args.input,
            output_dir=args.output_dir,
            lat_col=args.lat_col,
            lon_col=args.lon_col,
            id_col=args.id_col,
            stratify_col=args.stratify_by
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
