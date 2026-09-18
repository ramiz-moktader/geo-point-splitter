"""
Input/Output handlers for GeoJSON and CSV formats with auto-detection.
"""

import csv
import json
from pathlib import Path
from typing import List, Optional, Union
from .models import Point


class PointReader:
    """Reads point datasets from GeoJSON or CSV files with header auto-detection."""

    LAT_CANDIDATES = ["latitude", "lat", "y", "coord_y", "lat_deg", "ycoord"]
    LON_CANDIDATES = ["longitude", "long", "lon", "lng", "x", "coord_x", "lon_deg", "xcoord"]
    ID_CANDIDATES = ["rand_point_id", "point_id", "id", "fid", "oid", "objectid"]
    CLASS_CANDIDATES = ["class", "class_val", "classname", "label", "category", "target", "lulc"]

    @classmethod
    def read(
        cls,
        file_path: Union[str, Path],
        lat_col: Optional[str] = None,
        lon_col: Optional[str] = None,
        id_col: Optional[str] = None,
        class_col: Optional[str] = None
    ) -> List[Point]:
        """Load points from file, auto-detecting format based on extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        ext = path.suffix.lower()
        if ext in (".geojson", ".json"):
            return cls._read_geojson(path, id_col=id_col, class_col=class_col)
        elif ext in (".csv", ".tsv", ".txt"):
            return cls._read_csv(path, lat_col=lat_col, lon_col=lon_col, id_col=id_col, class_col=class_col)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats: .geojson, .csv, .tsv")

    @classmethod
    def _read_geojson(
        cls,
        path: Path,
        id_col: Optional[str] = None,
        class_col: Optional[str] = None
    ) -> List[Point]:
        """Parse GeoJSON FeatureCollection."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        if not features:
            raise ValueError(f"No features found in GeoJSON file: {path}")

        points: List[Point] = []
        for idx, feat in enumerate(features):
            geom = feat.get("geometry", {})
            if not geom or geom.get("type") != "Point":
                continue

            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                continue

            lon, lat = float(coords[0]), float(coords[1])
            props = feat.get("properties", {}) or {}

            # Resolve ID
            pt_id = None
            if id_col and id_col in props:
                pt_id = props[id_col]
            else:
                for cand in cls.ID_CANDIDATES:
                    if cand in props and props[cand] is not None:
                        pt_id = props[cand]
                        break
            if pt_id is None:
                pt_id = idx

            # Resolve existing class if present
            c_val = None
            if class_col and class_col in props:
                c_val = props[class_col]
            else:
                for cand in cls.CLASS_CANDIDATES:
                    if cand in props and props[cand] is not None:
                        c_val = props[cand]
                        break

            points.append(Point(id=pt_id, longitude=lon, latitude=lat, class_val=c_val, properties=props))

        return points

    @classmethod
    def _read_csv(
        cls,
        path: Path,
        lat_col: Optional[str] = None,
        lon_col: Optional[str] = None,
        id_col: Optional[str] = None,
        class_col: Optional[str] = None
    ) -> List[Point]:
        """Parse CSV with column auto-detection."""
        with open(path, "r", encoding="utf-8", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = ","
            try:
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                if "\t" in sample:
                    delimiter = "\t"

            reader = csv.DictReader(f, delimiter=delimiter)
            fieldnames = reader.fieldnames or []

            detected_lat = lat_col or cls._find_column(fieldnames, cls.LAT_CANDIDATES)
            detected_lon = lon_col or cls._find_column(fieldnames, cls.LON_CANDIDATES)
            detected_id = id_col or cls._find_column(fieldnames, cls.ID_CANDIDATES)
            detected_class = class_col or cls._find_column(fieldnames, cls.CLASS_CANDIDATES)

            if not detected_lat:
                raise ValueError(f"Latitude column not found in CSV: {fieldnames}. Specify with --lat-col.")
            if not detected_lon:
                raise ValueError(f"Longitude column not found in CSV: {fieldnames}. Specify with --lon-col.")

            points: List[Point] = []
            for idx, row in enumerate(reader):
                try:
                    lat = float(row[detected_lat])
                    lon = float(row[detected_lon])
                except (ValueError, TypeError):
                    continue

                pt_id = row[detected_id] if detected_id and detected_id in row else idx
                c_val = row[detected_class] if detected_class and detected_class in row else None
                props = {k: v for k, v in row.items() if k not in (detected_lat, detected_lon)}
                points.append(Point(id=pt_id, longitude=lon, latitude=lat, class_val=c_val, properties=props))

        return points

    @staticmethod
    def _find_column(fieldnames: List[str], candidates: List[str]) -> Optional[str]:
        """Find matching column name case-insensitively."""
        lookup = {col.lower().strip(): col for col in fieldnames}
        for cand in candidates:
            if cand.lower() in lookup:
                return lookup[cand.lower()]
        return None


class PointWriter:
    """Exports split point datasets to CSV and GeoJSON files."""

    @classmethod
    def write_splits(
        cls,
        splits: dict,
        output_dir: Path,
        formats: List[str] = ["csv", "geojson"],
        prefix: Optional[str] = None
    ) -> List[Path]:
        """Write all splits to target directory in specified formats."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files: List[Path] = []
        formats = [f.strip().lower() for f in formats]

        for split_key, pts in splits.items():
            if not pts:
                continue

            base_name = f"{prefix}_{split_key}" if prefix else str(split_key)

            if "csv" in formats:
                csv_path = output_dir / f"{base_name}.csv"
                cls._write_csv(pts, csv_path)
                created_files.append(csv_path)

            if "geojson" in formats or "json" in formats:
                geojson_path = output_dir / f"{base_name}.geojson"
                cls._write_geojson(pts, geojson_path, split_name=base_name)
                created_files.append(geojson_path)

        return created_files

    @classmethod
    def _write_csv(cls, points: List[Point], file_path: Path) -> None:
        """Write list of points to clean CSV with core columns first."""
        if not points:
            return

        all_dicts = [p.to_dict() for p in points]
        core_fields = [f for f in ["id", "latitude", "longitude", "class", "class_id"] if f in all_dicts[0]]
        other_fields = [k for k in all_dicts[0].keys() if k not in core_fields]
        fieldnames = core_fields + other_fields

        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in all_dicts:
                writer.writerow(d)

    @classmethod
    def _write_geojson(cls, points: List[Point], file_path: Path, split_name: str) -> None:
        """Write list of points to standard GeoJSON FeatureCollection."""
        feature_collection = {
            "type": "FeatureCollection",
            "name": split_name,
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": [p.to_geojson_feature() for p in points]
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(feature_collection, f, indent=2)
