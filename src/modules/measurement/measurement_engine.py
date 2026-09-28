import math
from typing import List, Optional
from dataclasses import dataclass

from ..pdf_processing.geometry_models import Point

from .calibration import Calibration, Unit
from .measurement_models import MeasurementType, MeasurementResult, TraceabilityInfo


@dataclass
class MeasurementEngine:
    calibration: Calibration
    
    def __post_init__(self):
        if self.calibration is None:
            raise ValueError("Calibration is required")
    
    def _create_traceability(self, points, calculation_method, page_index=None, page_label=None):
        source_points = [{"x": p.x, "y": p.y} for p in points] if points else None
        return TraceabilityInfo(
            source_page_index=page_index,
            source_page_label=page_label,
            source_points=source_points,
            calculation_method=calculation_method,
        )
    
    def measure_distance(self, p1, p2, page_index=None, page_label=None, geometry_ids=None):
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        pdf_distance = math.sqrt(dx * dx + dy * dy)
        real_world_distance = self.calibration.pdf_to_real_world(pdf_distance)
        traceability = self._create_traceability([p1, p2], "Euclidean distance", page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.DISTANCE,
            pdf_value=pdf_distance,
            calibration=self.calibration,
            unit=self.calibration.unit,
            real_world_value=real_world_distance,
            traceability=traceability,
            status="valid",
        )
    
    def measure_polyline_length(self, points, closed=False, page_index=None, page_label=None, geometry_ids=None):
        if len(points) < 2:
            raise ValueError(f"Polyline requires at least 2 points, got {len(points)}")
        pdf_length = 0.0
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            pdf_length += math.sqrt(dx * dx + dy * dy)
        if closed:
            p1, p2 = points[-1], points[0]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            pdf_length += math.sqrt(dx * dx + dy * dy)
        real_world_length = self.calibration.pdf_to_real_world(pdf_length)
        calc = "Open polyline length"
        if closed:
            calc = "Closed polyline length"
        traceability = self._create_traceability(points, calc, page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.POLYLINE_LENGTH,
            pdf_value=pdf_length,
            calibration=self.calibration,
            unit=self.calibration.unit,
            real_world_value=real_world_length,
            traceability=traceability,
            status="valid",
        )
    
    def measure_polygon_area(self, points, page_index=None, page_label=None, geometry_ids=None):
        if len(points) < 3:
            raise ValueError(f"Polygon requires at least 3 vertices, got {len(points)}")
        n = len(points)
        pdf_area = 0.0
        for i in range(n):
            j = (i + 1) % n
            pdf_area += points[i].x * points[j].y
            pdf_area -= points[j].x * points[i].y
        pdf_area = abs(pdf_area) / 2.0
        real_world_area = self.calibration.convert_area(pdf_area)
        traceability = self._create_traceability(points, "Shoelace formula", page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.POLYGON_AREA,
            pdf_value=pdf_area,
            calibration=self.calibration,
            unit=self.calibration.unit,
            real_world_value=real_world_area,
            traceability=traceability,
            status="valid",
        )
    
    def measure_polygon_perimeter(self, points, page_index=None, page_label=None, geometry_ids=None):
        if len(points) < 3:
            raise ValueError(f"Polygon requires at least 3 vertices, got {len(points)}")
        pdf_perimeter = 0.0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            p1, p2 = points[i], points[j]
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            pdf_perimeter += math.sqrt(dx * dx + dy * dy)
        real_world_perimeter = self.calibration.pdf_to_real_world(pdf_perimeter)
        traceability = self._create_traceability(points, "Polygon perimeter", page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.POLYGON_PERIMETER,
            pdf_value=pdf_perimeter,
            calibration=self.calibration,
            unit=self.calibration.unit,
            real_world_value=real_world_perimeter,
            traceability=traceability,
            status="valid",
        )
    
    def _distance(self, p1, p2):
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return math.sqrt(dx * dx + dy * dy)