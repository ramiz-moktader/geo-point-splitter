"""
Data models for the spatial point splitter.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union


@dataclass
class Point:
    """Represents a single geographic point with coordinates and attributes."""
    id: Any
    longitude: float  # X
    latitude: float   # Y
    class_val: Optional[Any] = None
    class_id: Optional[str] = None
    split_id: Optional[Union[int, str]] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert point to dictionary for tabular export (CSV)."""
        res: Dict[str, Any] = {
            "id": self.id,
            "latitude": round(self.latitude, 7),
            "longitude": round(self.longitude, 7),
        }
        if self.class_val is not None:
            res["class"] = self.class_val
        if self.class_id is not None:
            res["class_id"] = self.class_id
        for k, v in self.properties.items():
            if k not in res:
                res[k] = v
        return res

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convert point to a standard GeoJSON feature."""
        props = self.to_dict()
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(self.longitude, 7), round(self.latitude, 7)]
            },
            "properties": props
        }
