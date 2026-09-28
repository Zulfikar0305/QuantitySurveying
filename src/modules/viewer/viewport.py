"""
Viewport model for PDF rendering and coordinate transformation.

This module provides an explicit viewport state that tracks:
- Zoom scale
- Horizontal and vertical translation/pan
- Viewport size
- Rendered page size
- Page rotation handling

The viewport model is independent of any UI framework and can be
tested deterministically.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
from math import isclose


@dataclass(frozen=True)
class Viewport:
    """
    Represents the current viewport state for rendering a PDF page.
    
    The viewport transforms PDF page coordinates to screen coordinates:
    - screen_x = page_x * zoom + offset_x
    - screen_y = page_y * zoom + offset_y
    
    The inverse transformation:
    - page_x = (screen_x - offset_x) / zoom
    - page_y = (screen_y - offset_y) / zoom
    
    Attributes:
        zoom: Current zoom scale factor (1.0 = 100%)
        offset_x: Horizontal translation in screen pixels
        offset_y: Vertical translation in screen pixels
        viewport_width: Width of the viewport in screen pixels
        viewport_height: Height of the viewport in screen pixels
        rendered_page_width: Width of the rendered page in screen pixels
        rendered_page_height: Height of the rendered page in screen pixels
        page_rotation: Page rotation angle (0, 90, 180, 270)
    """
    
    zoom: float
    offset_x: float
    offset_y: float
    viewport_width: float
    viewport_height: float
    rendered_page_width: float
    rendered_page_height: float
    page_rotation: int = 0
    
    def __post_init__(self):
        """Validate viewport parameters."""
        if self.zoom <= 0:
            raise ValueError(f"Zoom must be positive, got {self.zoom}")
        if self.viewport_width <= 0:
            raise ValueError(f"Viewport width must be positive, got {self.viewport_width}")
        if self.viewport_height <= 0:
            raise ValueError(f"Viewport height must be positive, got {self.viewport_height}")
        if self.rendered_page_width < 0:
            raise ValueError(f"Rendered page width must be non-negative, got {self.rendered_page_width}")
        if self.rendered_page_height < 0:
            raise ValueError(f"Rendered page height must be non-negative, got {self.rendered_page_height}")
        if self.page_rotation not in (0, 90, 180, 270):
            raise ValueError(f"Page rotation must be 0, 90, 180, or 270, got {self.page_rotation}")
    
    @property
    def is_rotated(self) -> bool:
        """Check if the page is rotated."""
        return self.page_rotation != 0
    
    def fit_to_viewport(self, page_width: float, page_height: float) -> 'Viewport':
        """
        Calculate a new viewport that fits the page to the viewport area.
        
        Preserves aspect ratio by scaling to fit within the viewport.
        
        Args:
            page_width: Width of the page in PDF points
            page_height: Height of the page in PDF points
            
        Returns:
            New Viewport with zoom and offset configured for fit-to-page
        """
        # Handle rotated pages - dimensions are swapped
        if self.page_rotation in (90, 270):
            page_width, page_height = page_height, page_width
        
        # Calculate scale to fit both dimensions
        scale_x = (self.viewport_width - 20) / page_width  # 20px padding
        scale_y = (self.viewport_height - 20) / page_height
        
        zoom = min(scale_x, scale_y)
        
        # Calculate offset to center the page
        rendered_width = page_width * zoom
        rendered_height = page_height * zoom
        
        offset_x = (self.viewport_width - rendered_width) / 2
        offset_y = (self.viewport_height - rendered_height) / 2
        
        return Viewport(
            zoom=zoom,
            offset_x=offset_x,
            offset_y=offset_y,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            rendered_page_width=rendered_width,
            rendered_page_height=rendered_height,
            page_rotation=self.page_rotation
        )
    
    def zoom_in(self, factor: float = 1.2) -> 'Viewport':
        """Return a new viewport with increased zoom."""
        new_zoom = self.zoom * factor
        return self._with_zoom(new_zoom)
    
    def zoom_out(self, factor: float = 1.2) -> 'Viewport':
        """Return a new viewport with decreased zoom."""
        new_zoom = self.zoom / factor
        return self._with_zoom(new_zoom)
    
    def zoom_to(self, zoom: float) -> 'Viewport':
        """Return a new viewport with specified zoom level."""
        return self._with_zoom(zoom)
    
    def _with_zoom(self, new_zoom: float) -> 'Viewport':
        """Helper to create new viewport with different zoom, keeping offset relative."""
        # Adjust offset to maintain the same content position when zoom changes
        # around the viewport center
        center_x = self.viewport_width / 2
        center_y = self.viewport_height / 2
        
        # Convert center to page coordinates
        page_center_x = (center_x - self.offset_x) / self.zoom
        page_center_y = (center_y - self.offset_y) / self.zoom
        
        # Convert back to screen coordinates with new zoom
        new_offset_x = center_x - page_center_x * new_zoom
        new_offset_y = center_y - page_center_y * new_zoom
        
        # Calculate new rendered dimensions
        new_rendered_width = self.rendered_page_width * (new_zoom / self.zoom)
        new_rendered_height = self.rendered_page_height * (new_zoom / self.zoom)
        
        return Viewport(
            zoom=new_zoom,
            offset_x=new_offset_x,
            offset_y=new_offset_y,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            rendered_page_width=new_rendered_width,
            rendered_page_height=new_rendered_height,
            page_rotation=self.page_rotation
        )
    
    def pan(self, dx: float, dy: float) -> 'Viewport':
        """Return a new viewport with panned position."""
        return Viewport(
            zoom=self.zoom,
            offset_x=self.offset_x + dx,
            offset_y=self.offset_y + dy,
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
            rendered_page_width=self.rendered_page_width,
            rendered_page_height=self.rendered_page_height,
            page_rotation=self.page_rotation
        )
    
    def reset_transform(self, page_width: float, page_height: float) -> 'Viewport':
        """
        Reset to a centered view with zoom that fits the page.
        
        Args:
            page_width: Width of the page in PDF points
            page_height: Height of the page in PDF points
            
        Returns:
            New Viewport with reset transformation
        """
        return self.fit_to_viewport(page_width, page_height)
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'zoom': self.zoom,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'viewport_width': self.viewport_width,
            'viewport_height': self.viewport_height,
            'rendered_page_width': self.rendered_page_width,
            'rendered_page_height': self.rendered_page_height,
            'page_rotation': self.page_rotation
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Viewport':
        """Create Viewport from dictionary."""
        return cls(
            zoom=float(data['zoom']),
            offset_x=float(data['offset_x']),
            offset_y=float(data['offset_y']),
            viewport_width=float(data['viewport_width']),
            viewport_height=float(data['viewport_height']),
            rendered_page_width=float(data['rendered_page_width']),
            rendered_page_height=float(data['rendered_page_height']),
            page_rotation=int(data.get('page_rotation', 0))
        )
    
    def __repr__(self) -> str:
        return (
            f"Viewport(zoom={self.zoom:.2f}, offset=({self.offset_x:.1f}, {self.offset_y:.1f}), "
            f"rendered=({self.rendered_page_width:.1f}, {self.rendered_page_height:.1f}), "
            f"rotation={self.page_rotation})"
        )