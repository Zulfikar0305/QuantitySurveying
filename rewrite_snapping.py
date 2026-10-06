# Rewrite snapping.py with all fixes
content = '''\"\"\"
Deterministic snapping system for measurement points.

This module provides snapping functionality that operates on actual
extracted PDF geometry without AI or external inference services.

Supported snap types:
- line_start: Start point of a line segment
- line_end: End point of a line segment
- polyline_vertex: Vertex of a polyline
- line_intersection: Intersection point between two line segments
- line_midpoint: Midpoint of a line segment
- nearest_on_line: Nearest point on a line segment to the cursor
\"\"\"

from dataclasses import dataclass
from typing import Optional, Tuple, List
import math

from ..pdf_processing.geometry_models import Point, LineSegment
from ..viewer.coordinate_mapper import CoordinateMapper


@dataclass(frozen=True)
class SnapResult:
    \"\"\"Result of a snapping operation.\"\"\"
    snapped: bool
    original_point: Tuple[float, float]
    snapped_point: Tuple[float, float]
    snap_type: Optional[str] = None
    source_geometry_id: Optional[str] = None


class SnappingSystem:
    \"\"\"Deterministic snapping system for measurement points.\"\"\"
    
    def __init__(self, tolerance_page_units: float = 5.0):
        self.tolerance_page_units = tolerance_page_units
        self.tolerance_page_units_sq = tolerance_page_units * tolerance_page_units
    
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
    
    def find_intersections(self, vector_elements) -> List[Tuple[float, float, float]]:
        \"\"\"Find intersection points between line segments.\"\"\"
        intersections = []
        lines = []
        
        # Collect all line segments
        for element in vector_elements:
            line = None
            if hasattr(element, "to_line_segment"):
                line = element.to_line_segment()
            elif hasattr(element, "start") and hasattr(element, "end"):
                line = LineSegment(start=element.start, end=element.end)
            if line:
                lines.append(line)
        
        # Find intersections between all pairs of lines
        n = len(lines)
        for i in range(n):
            for j in range(i + 1, n):
                p1, p2 = lines[i].start, lines[i].end
                p3, p4 = lines[j].start, lines[j].end
                
                # Line intersection using determinant method
                denom = (p1.x - p2.x) * (p3.y - p4.y) - (p1.y - p2.y) * (p3.x - p4.x)
                
                if abs(denom) < 1e-10:  # Lines are parallel
                    continue
                
                t = ((p1.x - p3.x) * (p3.y - p4.y) - (p1.y - p3.y) * (p3.x - p4.x)) / denom
                u = -((p1.x - p2.x) * (p1.y - p3.y) - (p1.y - p2.y) * (p1.x - p3.x)) / denom
                
                # Check if intersection is within both line segments
                if 0 <= t <= 1 and 0 <= u <= 1:
                    intersection_x = p1.x + t * (p2.x - p1.x)
                    intersection_y = p1.y + t * (p2.y - p1.y)
                    
                    # Avoid duplicate intersections
                    intersections.append((intersection_x, intersection_y, 0.0))
        
        return intersections
    
    def find_midpoints(self, vector_elements) -> List[Tuple[float, float, float]]:
        \"\"\"Find midpoint points on line segments.\"\"\"
        midpoints = []
        
        for element in vector_elements:
            line = None
            if hasattr(element, "to_line_segment"):
                line = element.to_line_segment()
            elif hasattr(element, "start") and hasattr(element, "end"):
                line = LineSegment(start=element.start, end=element.end)
            if line:
                mid_x = (line.start.x + line.end.x) / 2.0
                mid_y = (line.start.y + line.end.y) / 2.0
                midpoints.append((mid_x, mid_y, 0.0))
        
        return midpoints
    
    def snap_to_geometry(self, vector_elements, polyline_elements,
                         page_point, enable_intersections: bool = True,
                         enable_midpoints: bool = True,
                         enable_nearest: bool = True) -> SnapResult:
        page_x, page_y = page_point
        
        # Collect all candidates with priority ordering
        # Priority: intersections > midpoints > endpoints > nearest
        all_candidates = []
        
        # Add endpoint/vertex candidates (lowest priority among snap points)
        endpoint_candidates = self.find_snap_candidates(vector_elements, polyline_elements, page_point)
        for cx, cy, dist_sq, snap_type in endpoint_candidates:
            all_candidates.append((cx, cy, dist_sq, snap_type))
        
        # Add intersection candidates (higher priority)
        if enable_intersections:
            intersections = self.find_intersections(vector_elements)
            for cx, cy, dist_sq in intersections:
                all_candidates.append((cx, cy, dist_sq, "intersection"))
        
        # Add midpoint candidates
        if enable_midpoints:
            midpoints = self.find_midpoints(vector_elements)
            for cx, cy, dist_sq in midpoints:
                all_candidates.append((cx, cy, dist_sq, "midpoint"))
        
        # Find best snap within tolerance (prioritize lower distances)
        best_candidate = None
        best_dist_sq = self.tolerance_page_units_sq
        
        for cx, cy, dist_sq, snap_type in all_candidates:
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
        
        # If no snap found, try nearest point on line segment
        if enable_nearest:
            nearest_result = self._find_nearest_on_segment(vector_elements, page_point)
            if nearest_result:
                return nearest_result
        
        return SnapResult(
            snapped=False,
            original_point=page_point,
            snapped_point=page_point,
            snap_type=None,
            source_geometry_id=None
        )
    
    def _find_nearest_on_segment(self, vector_elements, page_point) -> Optional[SnapResult]:
        \"\"\"Find the nearest point on any line segment to the given point.\"\"\"
        page_x, page_y = page_point
        best_point = None
        best_dist_sq = self.tolerance_page_units_sq
        
        for element in vector_elements:
            line = None
            if hasattr(element, "to_line_segment"):
                line = element.to_line_segment()
            elif hasattr(element, "start") and hasattr(element, "end"):
                line = LineSegment(start=element.start, end=element.end)
            if line:
                # Nearest point on line segment calculation
                p1, p2 = line.start, line.end
                
                # Vector from p1 to p2
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                
                # Vector from p1 to point
                dpx = page_x - p1.x
                dpy = page_y - p1.y
                
                # Project onto line
                len_sq = dx * dx + dy * dy
                
                if len_sq < 1e-10:  # Line is a point
                    continue
                
                t = (dpx * dx + dpy * dy) / len_sq
                
                # Clamp to segment
                t = max(0.0, min(1.0, t))
                
                # Nearest point
                nearest_x = p1.x + t * dx
                nearest_y = p1.y + t * dy
                
                # Distance squared
                dist_sq = (page_x - nearest_x) ** 2 + (page_y - nearest_y) ** 2
                
                if dist_sq < best_dist_sq:
                    best_dist_sq = dist_sq
                    best_point = (nearest_x, nearest_y, dist_sq, "nearest_on_segment")
        
        if best_point:
            return SnapResult(
                snapped=True,
                original_point=page_point,
                snapped_point=(best_point[0], best_point[1]),
                snap_type=best_point[3],
                source_geometry_id=None
            )
        
        return None
    
    def snap_from_screen(self, vector_elements, polyline_elements,
                         screen_point, coordinate_mapper, **snap_options) -> SnapResult:
        page_point = coordinate_mapper.screen_to_page(screen_point)
        return self.snap_to_geometry(vector_elements, polyline_elements, page_point, **snap_options)
'''

with open(r"c:\Users\moh09\QuantitySurveying\src\modules\measurement\snapping.py", "w") as f:
    f.write(content)

print("Rewrote snapping.py")
