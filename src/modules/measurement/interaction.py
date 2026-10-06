"""
Measurement interaction module for interactive measurement workflows.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum
import math

from ..viewer.coordinate_mapper import CoordinateMapper
from ..pdf_processing.geometry_models import Point, LineSegment
from .measurement_engine import MeasurementEngine
from .measurement_models import MeasurementType, MeasurementResult, TraceabilityInfo
from .calibration import Calibration, Unit


class MeasurementState(Enum):
    IDLE = "idle"
    WAITING_FOR_END = "waiting_for_end"
    COMPLETED = "completed"


@dataclass(frozen=True)
class SnappedPoint:
    snapped: bool
    original_page_point: Tuple[float, float]
    final_page_point: Tuple[float, float]
    snap_type: Optional[str] = None
    source_geometry_id: Optional[str] = None


@dataclass
class MeasurementInteraction:
    coordinate_mapper: Optional[CoordinateMapper] = None
    measurement_engine: Optional[MeasurementEngine] = None
    current_page_index: Optional[int] = None
    current_page_label: Optional[str] = None
    vector_geometry: List = field(default_factory=list)
    polyline_geometry: List = field(default_factory=list)
    state: MeasurementState = MeasurementState.IDLE
    start_point: Optional[SnappedPoint] = None
    snap_tolerance_pixels: float = 10.0
    
    def set_geometry(self, vector_elements: List, polyline_elements: List):
        self.vector_geometry = vector_elements
        self.polyline_geometry = polyline_elements
    
    def set_coordinate_mapper(self, mapper: CoordinateMapper):
        self.coordinate_mapper = mapper
    
    def set_measurement_engine(self, engine: MeasurementEngine):
        self.measurement_engine = engine
    
    def set_page_info(self, page_index: int, page_label: Optional[str] = None):
        self.current_page_index = page_index
        self.current_page_label = page_label
    
    def _convert_screen_to_page(self, screen_x: float, screen_y: float) -> Optional[Tuple[float, float]]:
        if self.coordinate_mapper is None:
            return None
        return self.coordinate_mapper.screen_to_page((screen_x, screen_y))
    
    def _find_snap_candidates(self, page_point: Tuple[float, float]) -> List[Tuple[float, float, float]]:
        candidates = []
        page_x, page_y = page_point
        for element in self.vector_geometry:
            line = None
            if hasattr(element, "to_line_segment"):
                line = element.to_line_segment()
            elif hasattr(element, "start") and hasattr(element, "end"):
                line = LineSegment(start=element.start, end=element.end)
            if line:
                dx = line.start.x - page_x
                dy = line.start.y - page_y
                dist_sq = dx * dx + dy * dy
                candidates.append((line.start.x, line.start.y, dist_sq))
                dx = line.end.x - page_x
                dy = line.end.y - page_y
                dist_sq = dx * dx + dy * dy
                candidates.append((line.end.x, line.end.y, dist_sq))
        for polyline in self.polyline_geometry:
            for point in polyline.points:
                dx = point.x - page_x
                dy = point.y - page_y
                dist_sq = dx * dx + dy * dy
                candidates.append((point.x, point.y, dist_sq))
        return candidates
    
    def _apply_snapping(self, screen_x: float, screen_y: float) -> SnappedPoint:
        page_point = self._convert_screen_to_page(screen_x, screen_y)
        if page_point is None:
            return SnappedPoint(snapped=False, original_page_point=(0.0, 0.0), final_page_point=(0.0, 0.0), snap_type=None, source_geometry_id=None)
        page_x, page_y = page_point
        tolerance_page = self.snap_tolerance_pixels / max(self.coordinate_mapper.zoom, 0.1)
        candidates = self._find_snap_candidates(page_point)
        if not candidates:
            return SnappedPoint(snapped=False, original_page_point=page_point, final_page_point=page_point, snap_type=None, source_geometry_id=None)
        best_candidate = None
        best_dist_sq = tolerance_page * tolerance_page
        for cx, cy, dist_sq in candidates:
            if dist_sq <= best_dist_sq:
                best_dist_sq = dist_sq
                best_candidate = (cx, cy)
        if best_candidate:
            return SnappedPoint(snapped=True, original_page_point=page_point, final_page_point=(best_candidate[0], best_candidate[1]), snap_type="endpoint", source_geometry_id=None)
        return SnappedPoint(snapped=False, original_page_point=page_point, final_page_point=page_point, snap_type=None, source_geometry_id=None)
    
    def handle_click(self, screen_x: float, screen_y: float) -> Optional[MeasurementResult]:
        if self.measurement_engine is None:
            return None
        if self.coordinate_mapper is None:
            return None
        snapped_point = self._apply_snapping(screen_x, screen_y)
        
        if self.state == MeasurementState.IDLE or self.state == MeasurementState.COMPLETED:
            # Start new measurement - first click, wait for second point
            self.state = MeasurementState.WAITING_FOR_END
            self.start_point = snapped_point
            return None
        elif self.state == MeasurementState.WAITING_FOR_END:
            # Second click - complete measurement
            end_point = snapped_point
            start_p = Point(x=self.start_point.final_page_point[0], y=self.start_point.final_page_point[1])
            end_p = Point(x=end_point.final_page_point[0], y=end_point.final_page_point[1])
            dx = end_p.x - start_p.x
            dy = end_p.y - start_p.y
            pdf_distance = math.sqrt(dx * dx + dy * dy)
            
            # Use MeasurementEngine if available for calibrated measurements
            if self.measurement_engine.calibration is not None:
                real_world_distance = self.measurement_engine.calibration.pdf_to_real_world(pdf_distance)
                calibration = self.measurement_engine.calibration
                unit = self.measurement_engine.calibration.unit
                status = "valid"
            else:
                # Uncalibrated - only PDF points available
                real_world_distance = None
                calibration = None
                unit = None
                status = "uncalibrated"
            
            source_points = [{"x": self.start_point.original_page_point[0], "y": self.start_point.original_page_point[1]}, {"x": end_point.original_page_point[0], "y": end_point.original_page_point[1]}]
            traceability = TraceabilityInfo(source_page_index=self.current_page_index, source_page_label=self.current_page_label, source_points=source_points, calculation_method="Euclidean distance")
            result = MeasurementResult(
                measurement_type=MeasurementType.DISTANCE,
                pdf_value=pdf_distance,
                calibration=calibration,
                unit=unit,
                real_world_value=real_world_distance,
                traceability=traceability,
                status=status
            )
            self.state = MeasurementState.COMPLETED
            return result
        return None
    
    def cancel(self):
        self.state = MeasurementState.IDLE
        self.start_point = None
    
    def reset(self):
        self.state = MeasurementState.IDLE
        self.start_point = None


class DistanceTool:
    def __init__(self, coordinate_mapper: CoordinateMapper, measurement_engine: MeasurementEngine):
        self.interaction = MeasurementInteraction(coordinate_mapper=coordinate_mapper, measurement_engine=measurement_engine)
    
    def activate(self, page_index: int, page_label: Optional[str] = None):
        self.interaction.state = MeasurementState.IDLE
        self.interaction.set_page_info(page_index, page_label)
        self.interaction.reset()
    
    def handle_click(self, screen_x: float, screen_y: float) -> Optional[MeasurementResult]:
        return self.interaction.handle_click(screen_x, screen_y)
    
    def cancel(self):
        self.interaction.cancel()
    
    def get_start_point(self) -> Optional[SnappedPoint]:
        return self.interaction.start_point
    
    def set_geometry(self, vector_elements: List, polyline_elements: List):
        self.interaction.set_geometry(vector_elements, polyline_elements)
