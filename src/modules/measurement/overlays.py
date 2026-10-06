"""
Measurement overlay rendering for interactive measurements.

This module provides visual overlays for measurements:
- Start/end point markers
- Connecting line
- Measurement value display

All overlays use page coordinates so they follow zoom/pan correctly.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum

from ..viewer.coordinate_mapper import CoordinateMapper
from .interaction import SnappedPoint


class OverlayType(Enum):
    POINT = "point"
    LINE = "line"
    TEXT = "text"


@dataclass(frozen=True)
class OverlayItem:
    """A single overlay element."""
    overlay_type: OverlayType
    page_point: Tuple[float, float]
    page_points: Optional[List[Tuple[float, float]]] = None
    text: Optional[str] = None
    color: str = "#ff0000"
    line_width: float = 2.0
    point_radius: float = 5.0


class MeasurementOverlay:
    """Overlay system for measurement visualization."""
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        self.coordinate_mapper = coordinate_mapper
        self.overlays: List[OverlayItem] = []
        self.current_measurement_text: Optional[str] = None
    
    def clear(self):
        """Clear all overlays."""
        self.overlays = []
        self.current_measurement_text = None
    
    def add_start_point(self, point: SnappedPoint):
        """Add a start point marker overlay."""
        self.overlays.append(OverlayItem(
            overlay_type=OverlayType.POINT,
            page_point=point.final_page_point,
            color="#00ff00",
            point_radius=6.0
        ))
    
    def add_end_point(self, point: SnappedPoint):
        """Add an end point marker overlay."""
        self.overlays.append(OverlayItem(
            overlay_type=OverlayType.POINT,
            page_point=point.final_page_point,
            color="#ff0000",
            point_radius=6.0
        ))
    
    def add_measurement_line(self, start_point: SnappedPoint, end_point: SnappedPoint):
        """Add a line connecting start and end points."""
        self.overlays.append(OverlayItem(
            overlay_type=OverlayType.LINE,
            page_point=start_point.final_page_point,
            page_points=[start_point.final_page_point, end_point.final_page_point],
            color="#ff0000",
            line_width=2.0
        ))
    
    def set_measurement_text(self, text: str):
        """Set the measurement value text overlay."""
        self.current_measurement_text = text
    
    def get_screen_overlays(self) -> List[dict]:
        """Convert page-coordinate overlays to screen coordinates."""
        screen_overlays = []
        
        for overlay in self.overlays:
            if overlay.overlay_type == OverlayType.POINT:
                screen_point = self.coordinate_mapper.page_to_screen(overlay.page_point)
                screen_overlays.append({
                    "type": "point",
                    "x": screen_point[0],
                    "y": screen_point[1],
                    "radius": overlay.point_radius * self.coordinate_mapper.zoom,
                    "color": overlay.color,
                    "line_width": overlay.line_width
                })
            elif overlay.overlay_type == OverlayType.LINE and overlay.page_points:
                start_screen = self.coordinate_mapper.page_to_screen(overlay.page_points[0])
                end_screen = self.coordinate_mapper.page_to_screen(overlay.page_points[1])
                screen_overlays.append({
                    "type": "line",
                    "x1": start_screen[0],
                    "y1": start_screen[1],
                    "x2": end_screen[0],
                    "y2": end_screen[1],
                    "color": overlay.color,
                    "line_width": overlay.line_width
                })
        
        return screen_overlays
    
    def get_text_overlay_position(self) -> Optional[Tuple[float, float]]:
        """Get screen position for measurement text."""
        if not self.overlays or not self.current_measurement_text:
            return None
        
        # Position text near the measurement line
        start_point = None
        end_point = None
        
        for overlay in self.overlays:
            if overlay.overlay_type == OverlayType.POINT:
                if overlay.color == "#00ff00":
                    start_point = overlay.page_point
                elif overlay.color == "#ff0000":
                    end_point = overlay.page_point
        
        if start_point and end_point:
            mid_x = (start_point[0] + end_point[0]) / 2
            mid_y = (start_point[1] + end_point[1]) / 2
            return self.coordinate_mapper.page_to_screen((mid_x, mid_y))
        
        return None
