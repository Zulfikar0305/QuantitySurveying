"""
PDF rendering module using PyMuPDF.

This module handles rendering PDF pages to images suitable for PySide6 display.
It maintains the deterministic nature of the PDF geometry while providing
visualization capabilities.

Rendering Principles:
- Preserve original PDF geometry
- Render to an intermediate image format
- Maintain aspect ratio
- Support configurable zoom via render scale
- Keep rendering deterministic and reproducible
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import pymupdf


class RenderError(Exception):
    """Raised when rendering fails."""
    pass


class InvalidPageError(Exception):
    """Raised when an invalid page is requested."""
    pass


@dataclass(frozen=True)
class RenderedImage:
    """
    Represents a rendered PDF page.
    
    Attributes:
        width: Width in pixels
        height: Height in pixels
        dpi: Rendering DPI
        page_index: Index of the rendered page
        page_label: Optional page label
        rotation: Page rotation angle
    """
    width: int
    height: int
    dpi: float
    page_index: int
    page_label: Optional[str]
    rotation: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'width': self.width,
            'height': self.height,
            'dpi': self.dpi,
            'page_index': self.page_index,
            'page_label': self.page_label,
            'rotation': self.rotation
        }
    
    def __repr__(self) -> str:
        return (
            f"RenderedImage({self.width}x{self.height}px, "
            f"rotation={self.rotation}, dpi={self.dpi:.0f})"
        )


class PDFRenderer:
    """
    Renders PDF pages to images for display.
    
    This renderer:
    - Preserves the PDF's original geometry
    - Does not modify the source PDF
    - Provides deterministic rendering at configured resolutions
    - Handles page rotation correctly
    
    Example:
        renderer = PDFRenderer()
        
        # Render at 150 DPI
        image_data = renderer.render_page(doc, 0, dpi=150)
        
        # Get metadata without rendering
        meta = renderer.get_render_metadata(doc, 0, dpi=150)
    """
    
    DEFAULT_DPI = 150
    MIN_DPI = 72
    MAX_DPI = 600
    
    def __init__(self, default_dpi: float = DEFAULT_DPI):
        """
        Initialize the renderer.
        
        Args:
            default_dpi: Default rendering DPI (72-600 range recommended)
        """
        self.default_dpi = default_dpi
        
        # Validate DPI range
        if not (self.MIN_DPI <= self.default_dpi <= self.MAX_DPI):
            raise ValueError(
                f"Default DPI must be between {self.MIN_DPI} and {self.MAX_DPI}, "
                f"got {self.default_dpi}"
            )
    
    def render_page(
        self,
        doc: 'pymupdf.Document',
        page_index: int,
        dpi: Optional[float] = None,
        rotation: Optional[int] = None
    ) -> bytes:
        """
        Render a PDF page to an image in PNG format.
        
        Args:
            doc: PyMuPDF Document object (must be open)
            page_index: Index of the page to render (0-based)
            dpi: Rendering DPI (uses default if not specified)
            rotation: Page rotation override (uses page's rotation if not specified)
            
        Returns:
            PNG image data as bytes
            
        Raises:
            RenderError: If rendering fails
            InvalidPageError: If page_index is out of range
            ValueError: If DPI is invalid
        """
        if dpi is None:
            dpi = self.default_dpi
        
        if not (self.MIN_DPI <= dpi <= self.MAX_DPI):
            raise ValueError(
                f"DPI must be between {self.MIN_DPI} and {self.MAX_DPI}, got {dpi}"
            )
        
        if page_index < 0 or page_index >= len(doc):
            raise InvalidPageError(
                f"Page index {page_index} out of range (document has {len(doc)} pages)"
            )
        
        try:
            page = doc[page_index]
            
            # Use page's rotation if not overridden
            page_rotation = rotation if rotation is not None else page.rotation
            
            # Calculate render scale based on DPI
            # PyMuPDF uses 72 DPI as base, so scale = dpi / 72
            render_scale = dpi / 72.0
            
            # Create transformation matrix for rotation and scaling
            # rotation_matrix handles page rotation
            # rect is the page rectangle
            rect = page.rect
            
            # Apply rotation if needed
            if page_rotation != 0:
                # Rotate the page for rendering
                page.set_rotation(page_rotation)
            
            # Render with the transformation
            matrix = pymupdf.Matrix(render_scale, render_scale)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Convert to PNG bytes
            image_data = pix.tobytes(output='png')
            
            return image_data
            
        except Exception as e:
            raise RenderError(f"Failed to render page {page_index}: {e}") from e
    
    def get_render_metadata(
        self,
        doc: 'pymupdf.Document',
        page_index: int,
        dpi: Optional[float] = None,
        rotation: Optional[int] = None
    ) -> RenderedImage:
        """
        Get rendering metadata without actually rendering.
        
        Args:
            doc: PyMuPDF Document object
            page_index: Index of the page
            dpi: Rendering DPI
            rotation: Page rotation
            
        Returns:
            RenderedImage metadata object
        """
        if dpi is None:
            dpi = self.default_dpi
            
        if page_index < 0 or page_index >= len(doc):
            raise InvalidPageError(
                f"Page index {page_index} out of range (document has {len(doc)} pages)"
            )
        
        page = doc[page_index]
        page_rotation = rotation if rotation is not None else page.rotation
        render_scale = dpi / 72.0
        
        # Get page dimensions in points
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
        
        # For rotated pages, dimensions are swapped
        if page_rotation in (90, 270):
            page_width, page_height = page_height, page_width
        
        # Calculate rendered dimensions in pixels
        render_width = int(page_width * render_scale)
        render_height = int(page_height * render_scale)
        
        return RenderedImage(
            width=render_width,
            height=render_height,
            dpi=dpi,
            page_index=page_index,
            page_label=page.get_label(),
            rotation=page_rotation
        )
    
    def calculate_zoom_for_fit(
        self,
        doc: 'pymupdf.Document',
        page_index: int,
        viewport_width: int,
        viewport_height: int,
        dpi: Optional[float] = None,
        padding: float = 20.0
    ) -> float:
        """
        Calculate the zoom scale to fit the page in the viewport.
        
        Args:
            doc: PyMuPDF Document object
            page_index: Index of the page
            viewport_width: Viewport width in pixels
            viewport_height: Viewport height in pixels
            dpi: Rendering DPI
            padding: Padding in pixels around the page
            
        Returns:
            Zoom scale factor (screen pixels per PDF point)
        """
        if dpi is None:
            dpi = self.default_dpi
        
        page = doc[page_index]
        page_rotation = page.rotation
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
        
        # For rotated pages, dimensions are swapped
        if page_rotation in (90, 270):
            page_width, page_height = page_height, page_width
        
        # Available space after padding
        available_width = viewport_width - padding * 2
        available_height = viewport_height - padding * 2
        
        # Calculate scale to fit
        scale_x = available_width / page_width
        scale_y = available_height / page_height
        
        # Use the smaller scale to fit within viewport
        scale = min(scale_x, scale_y)
        
        return scale