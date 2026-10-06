"""
Measurement interaction module for interactive measurement workflows.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum
import math

from ..viewer.coordinate_mapper import CoordinateMapper
from ..pdf_processing.geometry_models import Point, LineSegment, Polyline
from .measurement_engine import MeasurementEngine
from .measurement_models import MeasurementType, MeasurementResult, TraceabilityInfo
from .calibration import Calibration, Unit
from .snapping import SnappingSystem


class MeasurementState(Enum):
    IDLE = "idle"
    WAITING_FOR_END = "waiting_for_end"
    COMPLETED = "completed"
    POLYLINE_CONTINUING = "polyline_continuing"
    AREA_CONTINUING = "area_continuing"
    PERIMETER_CONTINUING = "perimeter_continuing"


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
    # For polyline/area/perimeter tools
    current_points: List[Point] = field(default_factory=list)
    snapped_points: List[SnappedPoint] = field(default_factory=list)
    snapping_system: Optional[SnappingSystem] = None
    
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
        self.current_points.clear()
        self.snapped_points.clear()
    
    def reset(self):
        self.state = MeasurementState.IDLE
        self.start_point = None
        self.current_points.clear()
        self.snapped_points.clear()

    def handle_click(self, screen_x: float, screen_y: float) -> Optional[MeasurementResult]:
        """Handle click for simple distance measurement."""
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


class PolylineTool:
    """Tool for measuring polyline/continuous distance with multiple points."""
    
    def __init__(self, coordinate_mapper: CoordinateMapper, measurement_engine: MeasurementEngine):
        self.interaction = MeasurementInteraction(coordinate_mapper=coordinate_mapper, measurement_engine=measurement_engine)
        self.snapping_system = SnappingSystem(tolerance_page_units=5.0)
        self.interaction.snapping_system = self.snapping_system
    
    def activate(self, page_index: int, page_label: Optional[str] = None):
        self.interaction.state = MeasurementState.IDLE
        self.interaction.set_page_info(page_index, page_label)
        self.interaction.reset()
    
    def handle_click(self, screen_x: float, screen_y: float) -> Tuple[Optional[MeasurementResult], Optional[MeasurementResult]]:
        
        if self.interaction.measurement_engine is None:
            return (None, None)
        if self.interaction.coordinate_mapper is None:
            return (None, None)
        
        # Use the tool's snapping system if available, otherwise use base class
        if self.snapping_system is not None:
            page_point = self.interaction._convert_screen_to_page(screen_x, screen_y)
            snapped = self.snapping_system.snap_to_geometry(self.interaction.vector_geometry, self.interaction.polyline_geometry, page_point)
            snapped_point = SnappedPoint(
                snapped=snapped.snapped,
                original_page_point=page_point,
                final_page_point=snapped.snapped_point,
                snap_type=snapped.snap_type,
                source_geometry_id=snapped.source_geometry_id
            )
        else:
            snapped_point = self.interaction._apply_snapping(screen_x, screen_y)
        
        if self.interaction.state == MeasurementState.IDLE:
            self.interaction.state = MeasurementState.POLYLINE_CONTINUING
            self.interaction.current_points = [Point(x=snapped_point.final_page_point[0], y=snapped_point.final_page_point[1])]
            self.interaction.snapped_points = [snapped_point]
            return (None, None)
        
        elif self.interaction.state == MeasurementState.POLYLINE_CONTINUING:
            new_point = Point(x=snapped_point.final_page_point[0], y=snapped_point.final_page_point[1])
            
            self.interaction.current_points.append(new_point)
            
            
            self.interaction.snapped_points.append(snapped_point)
            
            engine = self.interaction.measurement_engine
            result = engine.measure_polyline_length(
                self.interaction.current_points,
                closed=False,
                page_index=self.interaction.current_page_index,
                page_label=self.interaction.current_page_label
            )
            return (None, result)
        
        return (None, None)
    
    def complete(self) -> Optional[MeasurementResult]:
        if len(self.interaction.current_points) < 2:
            return None
        engine = self.interaction.measurement_engine
        result = engine.measure_polyline_length(
            self.interaction.current_points,
            closed=False,
            page_index=self.interaction.current_page_index,
            page_label=self.interaction.current_page_label
        )
        self.interaction.state = MeasurementState.COMPLETED
        return result
    
    def cancel(self):
        self.interaction.cancel()
    
    def reset(self):
        self.interaction.reset()
    
    def get_points(self) -> List[Point]:
        return self.interaction.current_points.copy()
    
    def get_current_measurement(self) -> Optional[MeasurementResult]:
        if len(self.interaction.current_points) < 2:
            return None
        engine = self.interaction.measurement_engine
        return engine.measure_polyline_length(
            self.interaction.current_points,
            closed=False,
            page_index=self.interaction.current_page_index,
            page_label=self.interaction.current_page_label
        )
    
    def set_geometry(self, vector_elements: List, polyline_elements: List):
        self.interaction.set_geometry(vector_elements, polyline_elements)

class AreaTool:
    """Tool for measuring polygon area."""
    
    def __init__(self, coordinate_mapper: CoordinateMapper, measurement_engine: MeasurementEngine):
        self.interaction = MeasurementInteraction(coordinate_mapper=coordinate_mapper, measurement_engine=measurement_engine)
        self.snapping_system = SnappingSystem(tolerance_page_units=5.0)
        self.interaction.snapping_system = self.snapping_system
    
    def activate(self, page_index: int, page_label: Optional[str] = None):
        self.interaction.state = MeasurementState.IDLE
        self.interaction.set_page_info(page_index, page_label)
        self.interaction.reset()
    
    def handle_click(self, screen_x: float, screen_y: float) -> Tuple[Optional[MeasurementResult], Optional[MeasurementResult]]:
        
        if self.interaction.measurement_engine is None:
            return (None, None)
        if self.interaction.coordinate_mapper is None:
            return (None, None)
        
        # Use the tool's snapping system if available, otherwise use base class
        if self.snapping_system is not None:
            page_point = self.interaction._convert_screen_to_page(screen_x, screen_y)
            snapped = self.snapping_system.snap_to_geometry(self.interaction.vector_geometry, self.interaction.polyline_geometry, page_point)
            snapped_point = SnappedPoint(
                snapped=snapped.snapped,
                original_page_point=page_point,
                final_page_point=snapped.snapped_point,
                snap_type=snapped.snap_type,
                source_geometry_id=snapped.source_geometry_id
            )
        else:
            snapped_point = self.interaction._apply_snapping(screen_x, screen_y)
        
        if self.interaction.state == MeasurementState.IDLE:
            self.interaction.state = MeasurementState.AREA_CONTINUING
            self.interaction.current_points = [Point(x=snapped_point.final_page_point[0], y=snapped_point.final_page_point[1])]
            self.interaction.snapped_points = [snapped_point]
            return (None, None)
        
        elif self.interaction.state == MeasurementState.AREA_CONTINUING:
            if len(self.interaction.current_points) >= 3:
                first_point = self.interaction.current_points[0]
                current_x, current_y = snapped_point.final_page_point
                dx = current_x - first_point.x
                dy = current_y - first_point.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance < 10.0:
                    self.interaction.state = MeasurementState.COMPLETED
                    try:
                        engine = self.interaction.measurement_engine
                        result = engine.measure_polygon_area(
                            self.interaction.current_points,
                            page_index=self.interaction.current_page_index,
                            page_label=self.interaction.current_page_label
                        )
                        return (result, None)
                    except ValueError:
                        return (None, None)
            
            new_point = Point(x=snapped_point.final_page_point[0], y=snapped_point.final_page_point[1])
            
            self.interaction.current_points.append(new_point)
            
            
            self.interaction.snapped_points.append(snapped_point)
            
            if len(self.interaction.current_points) >= 3:
                engine = self.interaction.measurement_engine
                try:
                    result = engine.measure_polygon_area(
                        self.interaction.current_points,
                        page_index=self.interaction.current_page_index,
                        page_label=self.interaction.current_page_label
                    )
                    return (None, result)
                except ValueError:
                    # Polygon is degenerate, remove the point and continue
                    self.interaction.current_points.pop()
                    self.interaction.snapped_points.pop()
                    return (None, None)
        
        return (None, None)
    
    def cancel(self):
        self.interaction.cancel()
    
    def reset(self):
        self.interaction.reset()
    
    def get_points(self) -> List[Point]:
        return self.interaction.current_points.copy()
    
    def is_valid_for_completion(self) -> bool:
        return len(self.interaction.current_points) >= 3
    
    def set_geometry(self, vector_elements: List, polyline_elements: List):
        self.interaction.set_geometry(vector_elements, polyline_elements)


class PerimeterTool:
    """Tool for measuring polygon perimeter."""
    
    def __init__(self, coordinate_mapper: CoordinateMapper, measurement_engine: MeasurementEngine):
        self.interaction = MeasurementInteraction(coordinate_mapper=coordinate_mapper, measurement_engine=measurement_engine)
        self.snapping_system = SnappingSystem(tolerance_page_units=5.0)
        self.interaction.snapping_system = self.snapping_system
    
    def activate(self, page_index: int, page_label: Optional[str] = None):
        self.interaction.state = MeasurementState.IDLE
        self.interaction.set_page_info(page_index, page_label)
        self.interaction.reset()
    
    def handle_click(self, screen_x: float, screen_y: float) -> Tuple[Optional[MeasurementResult], Optional[MeasurementResult]]:
        
        if self.interaction.measurement_engine is None:
            return (None, None)
        if self.interaction.coordinate_mapper is None:
            return (None, None)
        
        # Use the tool's snapping system if available, otherwise use base class
        if self.snapping_system is not None:
            page_point = self.interaction._convert_screen_to_page(screen_x, screen_y)
            snapped = self.snapping_system.snap_to_geometry(self.interaction.vector_geometry, self.interaction.polyline_geometry, page_point)
            snapped_point = SnappedPoint(
                snapped=snapped.snapped,
                original_page_point=page_point,
                final_page_point=snapped.snapped_point,
                snap_type=snapped.snap_type,
                source_geometry_id=snapped.source_geometry_id
            )
        else:
            snapped_point = self.interaction._apply_snapping(screen_x, screen_y)
        
        if self.interaction.state == MeasurementState.IDLE:
            
            self.interaction.state = MeasurementState.PERIMETER_CONTINUING
            self.interaction.current_points = [Point(x=snapped_point.final_page_point[0], y=snapped_point.final_page_point[1])]
            self.interaction.snapped_points = [snapped_point]
            return (None, None)
        
        elif self.interaction.state == MeasurementState.PERIMETER_CONTINUING:
            if len(self.interaction.current_points) >= 3:
                first_point = self.interaction.current_points[0]
                current_x, current_y = snapped_point.final_page_point
                dx = current_x - first_point.x
                dy = current_y - first_point.y
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance < 10.0:
                    self.interaction.state = MeasurementState.COMPLETED
                    engine = self.interaction.measurement_engine
                    result = engine.measure_polygon_perimeter(
                        self.interaction.current_points,
                        page_index=self.interaction.current_page_index,
                        page_label=self.interaction.current_page_label
                    )
                    return (result, None)
            
            new_point = Point(x=snapped_point.final_page_point[0], y=snapped_point.final_page_point[1])
            
            self.interaction.current_points.append(new_point)
            
            
            self.interaction.snapped_points.append(snapped_point)
            
            engine = self.interaction.measurement_engine
            if len(self.interaction.current_points) >= 3:
                try:
                    result = engine.measure_polygon_perimeter(
                        self.interaction.current_points,
                        page_index=self.interaction.current_page_index,
                        page_label=self.interaction.current_page_label
                    )
                    return (None, result)
                except ValueError:
                    # Polygon is degenerate, remove the point and continue
                    self.interaction.current_points.pop()
                    self.interaction.snapped_points.pop()
                    return (None, None)
            else:
                # Not enough vertices to measure perimeter yet
                return (None, None)
        
        return (None, None)
    
    def cancel(self):
        self.interaction.cancel()
    
    def reset(self):
        self.interaction.reset()
    
    def get_points(self) -> List[Point]:
        return self.interaction.current_points.copy()
    
    def is_valid_for_completion(self) -> bool:
        return len(self.interaction.current_points) >= 3
    
    def set_geometry(self, vector_elements: List, polyline_elements: List):
        self.interaction.set_geometry(vector_elements, polyline_elements)
