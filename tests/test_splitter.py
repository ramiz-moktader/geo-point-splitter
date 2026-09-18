"""
Unit tests for the spatial_splitter package.
"""

import math
from pathlib import Path
import pytest

from spatial_splitter.models import Point
from spatial_splitter.spatial import SpatialOptimizer
from spatial_splitter.splitters import EqualSplitter, RatioSplitter
from spatial_splitter.io import PointReader, PointWriter
from spatial_splitter.diagnostics import SpatialDiagnostics


@pytest.fixture
def sample_points():
    """Generate 100 synthetic geographic points across a grid."""
    points = []
    for i in range(10):
        for j in range(10):
            pt_id = i * 10 + j
            lon = 91.75 + (i * 0.01)
            lat = 22.25 + (j * 0.01)
            cls_val = (pt_id % 5) + 1
            points.append(Point(id=pt_id, longitude=lon, latitude=lat, class_val=cls_val))
    return points


class TestModels:
    def test_point_dict(self):
        p = Point(id=1, longitude=91.8, latitude=22.3, class_val=2, class_id="water_1")
        d = p.to_dict()
        assert d["id"] == 1
        assert d["latitude"] == 22.3
        assert d["longitude"] == 91.8
        assert d["class"] == 2
        assert d["class_id"] == "water_1"

    def test_point_geojson_feature(self):
        p = Point(id=42, longitude=91.82, latitude=22.35, class_val=3)
        feat = p.to_geojson_feature()
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        assert feat["geometry"]["coordinates"] == [91.82, 22.35]
        assert feat["properties"]["class"] == 3


class TestSpatialOptimizer:
    def test_haversine_distance(self):
        # Distance between two identical points should be 0
        d = SpatialOptimizer.haversine_distance_m(22.35, 91.80, 22.35, 91.80)
        assert math.isclose(d, 0.0, abs_tol=1e-5)

        # Distance between known points (approx 1 degree latitude ~ 111 km)
        d_deg = SpatialOptimizer.haversine_distance_m(22.0, 91.0, 23.0, 91.0)
        assert 110000 < d_deg < 112000

    def test_morton_encoding_preserves_order(self):
        code1 = SpatialOptimizer.morton_encode(0.1, 0.1)
        code2 = SpatialOptimizer.morton_encode(0.9, 0.9)
        assert code1 < code2

    def test_spatial_sort(self, sample_points):
        sorted_pts = SpatialOptimizer.sort_spatially(sample_points)
        assert len(sorted_pts) == len(sample_points)
        # Verify coordinates exist and are sorted
        assert all(isinstance(p, Point) for p in sorted_pts)


class TestEqualSplitter:
    def test_equal_split_one_per_file(self, sample_points):
        num_splits = 5
        splits = EqualSplitter.split(
            points=sample_points,
            num_splits=num_splits,
            class_mode="one-per-file",
            add_class_id=True,
            class_names=["water", "vegetation", "urban", "soil", "crop"]
        )
        assert len(splits) == 5
        for c_name in ["water", "vegetation", "urban", "soil", "crop"]:
            assert c_name in splits
            pts = splits[c_name]
            assert len(pts) == 20
            # Verify class_id format
            assert pts[0].class_id == f"{c_name}_1"
            assert pts[-1].class_id == f"{c_name}_20"

    def test_equal_split_balanced(self, sample_points):
        num_splits = 4
        splits = EqualSplitter.split(
            points=sample_points,
            num_splits=num_splits,
            class_mode="balanced"
        )
        assert len(splits) == 4
        for s_key, pts in splits.items():
            assert len(pts) == 25


class TestRatioSplitter:
    def test_70_30_ratio_split(self, sample_points):
        splits = RatioSplitter.split(
            points=sample_points,
            ratios=[70.0, 30.0],
            stratify_col="class",
            add_class_id=True
        )
        assert "train_70" in splits
        assert "test_30" in splits

        train_pts = splits["train_70"]
        test_pts = splits["test_30"]

        assert len(train_pts) == 70
        assert len(test_pts) == 30

        # Verify exact class balance
        # 100 points, 5 classes -> 20 points per class
        # 70% of 20 = 14 per class in train, 30% of 20 = 6 per class in test
        train_classes = [p.class_val for p in train_pts]
        test_classes = [p.class_val for p in test_pts]

        for cv in [1, 2, 3, 4, 5]:
            assert train_classes.count(cv) == 14
            assert test_classes.count(cv) == 6


class TestIO:
    def test_read_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("point_id,latitude,longitude,class\n1,22.3,91.8,1\n2,22.4,91.9,2\n")
        pts = PointReader.read(csv_file)
        assert len(pts) == 2
        assert pts[0].latitude == 22.3
        assert pts[0].longitude == 91.8

    def test_write_and_read_csv(self, tmp_path, sample_points):
        out_dir = tmp_path / "out"
        splits = {"split_1": sample_points[:10]}
        created = PointWriter.write_splits(splits, output_dir=out_dir, formats=["csv", "geojson"])
        assert len(created) == 2

        # Read back CSV
        read_pts = PointReader.read(created[0])
        assert len(read_pts) == 10
