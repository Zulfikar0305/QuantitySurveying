import math
from typing import List, Optional
from dataclasses import dataclass, field

from ..pdf_processing.geometry_models import Point

from .calibration import Calibration, Unit
from .measurement_models import MeasurementType, MeasurementResult, TraceabilityInfo


@dataclass
class MeasurementEngine:
    calibration: Optional[Calibration] = None
    
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
        
        if self.calibration is not None:
            real_world_distance = self.calibration.pdf_to_real_world(pdf_distance)
            unit = self.calibration.unit
            calibration = self.calibration
        else:
            real_world_distance = None
            unit = None
            calibration = None
        
        traceability = self._create_traceability([p1, p2], "Euclidean distance", page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.DISTANCE,
            pdf_value=pdf_distance,
            calibration=calibration,
            unit=unit,
            real_world_value=real_world_distance,
            traceability=traceability,
            status="valid" if calibration is not None else "uncalibrated",
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
        
        if self.calibration is not None:
            real_world_length = self.calibration.pdf_to_real_world(pdf_length)
            unit = self.calibration.unit
            calibration = self.calibration
            calc = "Open polyline length" if not closed else "Closed polyline length"
        else:
            real_world_length = None
            unit = None
            calibration = None
            calc = "Open polyline length (uncalibrated)" if not closed else "Closed polyline length (uncalibrated)"
        
        traceability = self._create_traceability(points, calc, page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.POLYLINE_LENGTH,
            pdf_value=pdf_length,
            calibration=calibration,
            unit=unit,
            real_world_value=real_world_length,
            traceability=traceability,
            status="valid" if calibration is not None else "uncalibrated",
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
        
        if self.calibration is not None:
            real_world_area = self.calibration.convert_area(pdf_area)
            unit = self.calibration.unit
            calibration = self.calibration
        else:
            real_world_area = None
            unit = None
            calibration = None
        
        traceability = self._create_traceability(points, "Shoelace formula", page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.POLYGON_AREA,
            pdf_value=pdf_area,
            calibration=calibration,
            unit=unit,
            real_world_value=real_world_area,
            traceability=traceability,
            status="valid" if calibration is not None else "uncalibrated",
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
        
        if self.calibration is not None:
            real_world_perimeter = self.calibration.pdf_to_real_world(pdf_perimeter)
            unit = self.calibration.unit
            calibration = self.calibration
        else:
            real_world_perimeter = None
            unit = None
            calibration = None
        
        traceability = self._create_traceability(points, "Polygon perimeter", page_index, page_label)
        return MeasurementResult(
            measurement_type=MeasurementType.POLYGON_PERIMETER,
            pdf_value=pdf_perimeter,
            calibration=calibration,
            unit=unit,
            real_world_value=real_world_perimeter,
            traceability=traceability,
            status="valid" if calibration is not None else "uncalibrated",
        )
    
    def _distance(self, p1, p2):
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return math.sqrt(dx * dx + dy * dy)