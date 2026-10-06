"""
Deterministic snapping system for measurement points.

This module provides snapping functionality that operates on actual
extracted PDF geometry without AI or external inference services.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
import math

from ..pdf_processing.geometry_models import Point, LineSegment
from ..viewer.coordinate_mapper import CoordinateMapper


@dataclass(frozen=True)
class SnapResult:
    """Result of a snapping operation."""
    snapped: bool
    original_point: Tuple[float, float]
    snapped_point: Tuple[float, float]
    snap_type: Optional[str] = None
    source_geometry_id: Optional[str] = None


class SnappingSystem:
    """Deterministic snapping system for measurement points."""
    
    def __init__(self, tolerance_page_units: float = 5.0):
        self.tolerance_page_units = tolerance_page_units
    
    def find_snap_candidates(self, vector_elements, polyline_elements, 
                             page_point) -> List[Tuple[float, float, float, Optional[str]]]:
        candidates = []
        page_x, page_y = page_point
        
        for element in vector_elements:
            line = None
            if hasattr(element, "to_line_segment"):
                line = element.to_line_segment()
            elif hasattr(element, "start") and hasattr(element, "end"):
                line = LineSegment(start=element.start, end=element.end)
            
            if line:
                dx = line.start.x - page_x
                dy = line.start.y - page_y
                dist_sq = dx * dx + dy * dy
                candidates.append((line.start.x, line.start.y, dist_sq, "line_start"))
                
                dx = line.end.x - page_x
                dy = line.end.y - page_y
                dist_sq = dx * dx + dy * dy
                candidates.append((line.end.x, line.end.y, dist_sq, "line_end"))
        
        for polyline in polyline_elements:
            for point in polyline.points:
                dx = point.x - page_x
                dy = point.y - page_y
                dist_sq = dx * dx + dy * dy
                candidates.append((point.x, point.y, dist_sq, "polyline_vertex"))
        
        return candidates
    
    def snap_to_geometry(self, vector_elements, polyline_elements,
                         page_point) -> SnapResult:
        page_x, page_y = page_point
        
        candidates = self.find_snap_candidates(vector_elements, polyline_elements, page_point)
        
        if not candidates:
            return SnapResult(
                snapped=False,
                original_point=page_point,
                snapped_point=page_point,
                snap_type=None,
                source_geometry_id=None
            )
        
        best_candidate = None
        best_dist_sq = self.tolerance_page_units * self.tolerance_page_units
        
        for cx, cy, dist_sq, snap_type in candidates:
            if dist_sq <= best_dist_sq:
                best_dist_sq = dist_sq
                best_candidate = (cx, cy, dist_sq, snap_type)
        
        if best_candidate:
            return SnapResult(
                snapped=True,
                original_point=page_point,
                snapped_point=(best_candidate[0], best_candidate[1]),
                snap_type=best_candidate[3],
                source_geometry_id=None
            )
        
        return SnapResult(
            snapped=False,
            original_point=page_point,
            snapped_point=page_point,
            snap_type=None,
            source_geometry_id=None
        )
    
    def snap_from_screen(self, vector_elements, polyline_elements,
                         screen_point, coordinate_mapper) -> SnapResult:
        page_point = coordinate_mapper.screen_to_page(screen_point)
        return self.snap_to_geometry(vector_elements, polyline_elements, page_point)
