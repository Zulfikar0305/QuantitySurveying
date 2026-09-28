"""
Geometry models for PDF vector and text extraction.

These are domain models that represent PDF content without exposing
PyMuPDF-specific implementation details.

Coordinate System:
- PyMuPDF/MuPDF uses top-left origin (0,0), X right, Y down (points)
- PDF internally uses bottom-left origin, X right, Y up
- All extracted coordinates are in PyMuPDF's native coordinate space
- Use transformation_matrix for conversions between spaces
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union
from enum import Enum
import pymupdf


class GeometryType(Enum):
    """Types of geometric elements found in PDFs."""
    LINE = "line"
    POLYLINE = "polyline"
    RECTANGLE = "rectangle"
    OVAL = "oval"
    CURVE = "curve"
    BEZIER = "bezier"
    PATH = "path"
    TEXT = "text"
    IMAGE = "image"


class FillRule(Enum):
    """Fill rules for paths."""
    WINDING = "winding"
    EVENODD = "even_odd"


@dataclass(frozen=True)
class Point:
    """
    A point in PDF coordinate space.
    
    PyMuPDF/MuPDF uses a coordinate system with:
    - Origin (0,0) at the top-left of the page
    - X-axis extends right
    - Y-axis extends downward (NOT upward)
    - Coordinates are in points (1/72 inch)
    
    Note: The underlying PDF coordinate system uses bottom-left origin with Y upward.
    PyMuPDF provides transformation matrices to convert between PDF and MuPDF spaces.
    """
    x: float
    y: float
    
    def __repr__(self) -> str:
        return f"Point(x={self.x:.2f}, y={self.y:.2f})"


@dataclass(frozen=True)
class Rectangle:
    """
    A rectangle defined by its bounding box.
    
    The rectangle is defined by its minimum and maximum coordinates.
    """
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def center(self) -> 'Point':
        return Point(
            x=(self.x0 + self.x1) / 2,
            y=(self.y0 + self.y1) / 2
        )
    
    @classmethod
    def from_dict(cls, rect_dict: dict) -> 'Rectangle':
        """Create Rectangle from a PyMuPDF rect-like dictionary."""
        return cls(
            x0=float(rect_dict['x0']),
            y0=float(rect_dict['y0']),
            x1=float(rect_dict['x1']),
            y1=float(rect_dict['y1'])
        )
    
    @classmethod
    def from_pymupdf_rect(cls, rect: pymupdf.Rect) -> 'Rectangle':
        """Create Rectangle from a PyMuPDF Rect object."""
        return cls(
            x0=float(rect.x0),
            y0=float(rect.y0),
            x1=float(rect.x1),
            y1=float(rect.y1)
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'x0': self.x0,
            'y0': self.y0,
            'x1': self.x1,
            'y1': self.y1
        }


@dataclass(frozen=True)
class LineSegment:
    """
    A straight line segment between two points.
    
    Preserves original PDF coordinates without pixel conversion.
    """
    start: Point
    end: Point
    stroke_color: Optional[Tuple[float, float, float]] = None  # RGB tuple or None
    stroke_width: float = 1.0
    stroke_opacity: float = 1.0
    
    @classmethod
    def from_drawings_dict(cls, item: tuple, stroke_info: dict) -> 'LineSegment':
        """
        Create LineSegment from PyMuPDF drawings item.
        
        Args:
            item: Tuple like ('l', start_point, end_point) for line
            stroke_info: Dictionary containing stroke properties
        """
        _, start_pt, end_pt = item
        return cls(
            start=Point(x=float(start_pt.x), y=float(start_pt.y)),
            end=Point(x=float(end_pt.x), y=float(end_pt.y)),
            stroke_color=cls._parse_color(stroke_info.get('color')),
            stroke_width=float(stroke_info.get('width', 1.0)),
            stroke_opacity=float(stroke_info.get('stroke_opacity', 1.0))
        )
    
    @staticmethod
    def _parse_color(color_val) -> Optional[Tuple[float, float, float]]:
        """Parse color value to RGB tuple."""
        if color_val is None:
            return None
        if isinstance(color_val, (tuple, list)):
            if len(color_val) >= 3:
                return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
        return None


@dataclass(frozen=True)
class Polyline:
    """
    A sequence of connected line segments.
    
    Can be open or closed (polygon).
    """
    points: List[Point]
    close_path: bool = False
    stroke_color: Optional[Tuple[float, float, float]] = None
    stroke_width: float = 1.0
    stroke_opacity: float = 1.0
    fill_color: Optional[Tuple[float, float, float]] = None
    fill_opacity: float = 1.0
    
    @classmethod
    def from_drawings_dict(cls, item: list, stroke_info: dict) -> 'Polyline':
        """
        Create Polyline from PyMuPDF drawings items.
        
        Args:
            item: List of drawing commands
            stroke_info: Dictionary containing stroke/fill properties
        """
        points = []
        for cmd in item:
            if cmd[0] == 'l':  # Line to
                _, start, end = cmd
                points.append(Point(x=float(end.x), y=float(end.y)))
            elif cmd[0] == 'm':  # Move to
                _, point = cmd
                points.append(Point(x=float(point.x), y=float(point.y)))
            elif cmd[0] == 're':  # Rectangle
                _, rect, _ = cmd
                # Add all four corners of rectangle
                points.append(Point(x=float(rect.x0), y=float(rect.y0)))
                points.append(Point(x=float(rect.x1), y=float(rect.y0)))
                points.append(Point(x=float(rect.x1), y=float(rect.y1)))
                points.append(Point(x=float(rect.x0), y=float(rect.y1)))
        
        return cls(
            points=points,
            close_path=bool(stroke_info.get('closePath', False)),
            stroke_color=cls._parse_color(stroke_info.get('color')),
            stroke_width=float(stroke_info.get('width', 1.0)),
            stroke_opacity=float(stroke_info.get('stroke_opacity', 1.0)),
            fill_color=cls._parse_color(stroke_info.get('fill')),
            fill_opacity=float(stroke_info.get('fill_opacity', 1.0)) if stroke_info.get('fill') else 0.0
        )
    
    @staticmethod
    def _parse_color(color_val) -> Optional[Tuple[float, float, float]]:
        """Parse color value to RGB tuple."""
        if color_val is None:
            return None
        if isinstance(color_val, (tuple, list)):
            if len(color_val) >= 3:
                return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
        return None


@dataclass(frozen=True)
class Curve:
    """
    A Bezier curve or other curved path segment.
    """
    control_points: List[Point]
    end_point: Point
    stroke_color: Optional[Tuple[float, float, float]] = None
    stroke_width: float = 1.0
    stroke_opacity: float = 1.0
    
    @classmethod
    def from_drawings_dict(cls, item: tuple, stroke_info: dict) -> 'Curve':
        """
        Create Curve from PyMuPDF drawings item.
        
        Args:
            item: Tuple like ('c', cp1, cp2, end) for cubic bezier
            stroke_info: Dictionary containing stroke properties
        """
        # Handle different curve types
        curve_type = item[0]
        control_points = []
        
        if curve_type == 'c':  # Cubic Bezier: (c, p1, p2, p3)
            _, cp1, cp2, end = item
            control_points = [Point(x=float(cp1.x), y=float(cp1.y)),
                             Point(x=float(cp2.x), y=float(cp2.y))]
        elif curve_type == 'y':  # Quadratic Bezier: (y, cp, end)
            _, cp, end = item
            control_points = [Point(x=float(cp.x), y=float(cp.y))]
        elif curve_type == 'l':  # Line (degenerate curve)
            _, start, end = item
            control_points = []
        
        return cls(
            control_points=control_points,
            end_point=Point(x=float(end.x), y=float(end.y)),
            stroke_color=cls._parse_color(stroke_info.get('color')),
            stroke_width=float(stroke_info.get('width', 1.0)),
            stroke_opacity=float(stroke_info.get('stroke_opacity', 1.0))
        )
    
    @staticmethod
    def _parse_color(color_val) -> Optional[Tuple[float, float, float]]:
        """Parse color value to RGB tuple."""
        if color_val is None:
            return None
        if isinstance(color_val, (tuple, list)):
            if len(color_val) >= 3:
                return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
        return None


@dataclass(frozen=True)
class TextElement:
    """
    A text element extracted from the PDF.
    
    Preserves position, content, and formatting information.
    """
    text: str
    bbox: Rectangle  # Bounding box in PDF coordinates
    position: Point  # Reference position (usually bottom-left)
    font_name: Optional[str] = None
    font_size: float = 12.0
    color: Optional[Tuple[float, float, float]] = None
    page_index: int = 0
    
    @classmethod
    def from_text_dict(cls, text_dict: dict, page_index: int = 0) -> "TextElement":
        """
        Create TextElement from PyMuPDF text dictionary.
        """
        bbox = text_dict.get("bbox", text_dict.get("rect", [0, 0, 0, 0]))
        rect = Rectangle(x0=float(bbox[0]), y0=float(bbox[1]), x1=float(bbox[2]), y1=float(bbox[3]))
        position = Point(x=float(text_dict.get("x", rect.x0)), y=float(text_dict.get("y", rect.y0)))
        return cls(text=str(text_dict.get("text", "")), bbox=rect, position=position,
                   font_name=text_dict.get("font"), font_size=float(text_dict.get("size", 12.0)),
                   color=cls._parse_color(text_dict.get("color")), page_index=page_index)
    
    @staticmethod
    def _parse_color(color_val):
        if color_val is None:
            return None
        if isinstance(color_val, (tuple, list)) and len(color_val) >= 3:
            return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
        return None


@dataclass(frozen=True)
class DrawingElement:
    """
    A single vector drawing element (line, shape, etc.).
    
    Wraps line segments, polylines, curves, and other vector elements.
    """
    geometry_type: GeometryType
    geometry: Union[LineSegment, Polyline, Curve, Rectangle]
    stroke_color: Optional[Tuple[float, float, float]] = None
    stroke_width: float = 1.0
    stroke_opacity: float = 1.0
    fill_color: Optional[Tuple[float, float, float]] = None
    fill_opacity: float = 0.0
    page_index: int = 0
    
    @classmethod
    def from_drawings_dict(cls, drawing_dict: dict, page_index: int = 0) -> "DrawingElement":
        items = drawing_dict.get("items", [])
        stroke_info = {
            "closePath": drawing_dict.get("closePath", False),
            "stroke_opacity": drawing_dict.get("stroke_opacity", 1.0),
            "color": drawing_dict.get("color"),
            "width": drawing_dict.get("width", 1.0),
            "fill": drawing_dict.get("fill"),
            "fill_opacity": drawing_dict.get("fill_opacity", 0.0),
            "even_odd": drawing_dict.get("even_odd"),
        }
        geometry_type, geometry = cls._parse_items(items, stroke_info)
        return cls(geometry_type=geometry_type, geometry=geometry,
                   stroke_color=stroke_info["color"],
                   stroke_width=float(stroke_info["width"]),
                   stroke_opacity=float(stroke_info["stroke_opacity"]),
                   fill_color=stroke_info["fill"],
                   fill_opacity=float(stroke_info["fill_opacity"]) if stroke_info["fill"] else 0.0,
                   page_index=page_index)
    
    @classmethod
    def _parse_items(cls, items: list, stroke_info: dict):
        if not items:
            return GeometryType.RECTANGLE, Rectangle(0, 0, 0, 0)
        if len(items) == 1 and items[0][0] == "re":
            rect = items[0][1]
            rect_obj = Rectangle(x0=float(rect.x0), y0=float(rect.y0), x1=float(rect.x1), y1=float(rect.y1))
            return GeometryType.RECTANGLE, rect_obj
        if len(items) == 1 and items[0][0] == "l":
            _, start, end = items[0]
            line = LineSegment(start=Point(x=float(start.x), y=float(start.y)),
                              end=Point(x=float(end.x), y=float(end.y)),
                              stroke_color=stroke_info["color"],
                              stroke_width=float(stroke_info["width"]),
                              stroke_opacity=float(stroke_info["stroke_opacity"]))
            return GeometryType.LINE, line
        if items[0][0] in ("c", "y", "l"):
            curve = Curve.from_drawings_dict(items[0], stroke_info)
            return GeometryType.CURVE, curve
        polyline = Polyline.from_drawings_dict(items, stroke_info)
        return GeometryType.POLYLINE, polyline
    
    def to_line_segment(self) -> Optional[LineSegment]:
        if self.geometry_type == GeometryType.LINE:
            return self.geometry
        return None
    
    def to_polyline(self) -> Optional[Polyline]:
        if self.geometry_type == GeometryType.POLYLINE:
            return self.geometry
        return None
    
    def to_curve(self) -> Optional[Curve]:
        if self.geometry_type == GeometryType.CURVE:
            return self.geometry
        return None
    
    def to_rectangle(self) -> Optional[Rectangle]:
        if self.geometry_type == GeometryType.RECTANGLE:
            return self.geometry
        return None

@dataclass(frozen=True)
class TextElement:
    """
    A text element extracted from the PDF.
    
    Preserves position, content, and formatting information.
    """
    text: str
    bbox: Rectangle  # Bounding box in PDF coordinates
    position: Point  # Reference position (usually bottom-left)
    font_name: Optional[str] = None
    font_size: float = 12.0
    color: Optional[Tuple[float, float, float]] = None
    page_index: int = 0
    
    @classmethod
    def from_text_dict(cls, text_dict: dict, page_index: int = 0) -> "TextElement":
        """
        Create TextElement from PyMuPDF text dictionary.
        """
        bbox = text_dict.get("bbox", text_dict.get("rect", [0, 0, 0, 0]))
        rect = Rectangle(x0=float(bbox[0]), y0=float(bbox[1]), x1=float(bbox[2]), y1=float(bbox[3]))
        position = Point(x=float(text_dict.get("x", rect.x0)), y=float(text_dict.get("y", rect.y0)))
        return cls(text=str(text_dict.get("text", "")), bbox=rect, position=position,
                   font_name=text_dict.get("font"), font_size=float(text_dict.get("size", 12.0)),
                   color=cls._parse_color(text_dict.get("color")), page_index=page_index)
    
    @staticmethod
    def _parse_color(color_val):
        if color_val is None:
            return None
        if isinstance(color_val, (tuple, list)) and len(color_val) >= 3:
            return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
        return None


@dataclass(frozen=True)
class DrawingElement:
    """
    A single vector drawing element (line, shape, etc.).
    
    Wraps line segments, polylines, curves, and other vector elements.
    """
    geometry_type: GeometryType
    geometry: Union[LineSegment, Polyline, Curve, Rectangle]
    stroke_color: Optional[Tuple[float, float, float]] = None
    stroke_width: float = 1.0
    stroke_opacity: float = 1.0
    fill_color: Optional[Tuple[float, float, float]] = None
    fill_opacity: float = 0.0
    page_index: int = 0
    
    @classmethod
    def from_drawings_dict(cls, drawing_dict: dict, page_index: int = 0) -> "DrawingElement":
        items = drawing_dict.get("items", [])
        stroke_info = {
            "closePath": drawing_dict.get("closePath", False),
            "stroke_opacity": drawing_dict.get("stroke_opacity", 1.0),
            "color": drawing_dict.get("color"),
            "width": drawing_dict.get("width", 1.0),
            "fill": drawing_dict.get("fill"),
            "fill_opacity": drawing_dict.get("fill_opacity", 0.0),
            "even_odd": drawing_dict.get("even_odd"),
        }
        geometry_type, geometry = cls._parse_items(items, stroke_info)
        return cls(geometry_type=geometry_type, geometry=geometry,
                   stroke_color=stroke_info["color"],
                   stroke_width=float(stroke_info["width"]),
                   stroke_opacity=float(stroke_info["stroke_opacity"]),
                   fill_color=stroke_info["fill"],
                   fill_opacity=float(stroke_info["fill_opacity"]) if stroke_info["fill"] else 0.0,
                   page_index=page_index)
    
    @classmethod
    def _parse_items(cls, items: list, stroke_info: dict):
        if not items:
            return GeometryType.RECTANGLE, Rectangle(0, 0, 0, 0)
        if len(items) == 1 and items[0][0] == "re":
            rect = items[0][1]
            rect_obj = Rectangle(x0=float(rect.x0), y0=float(rect.y0), x1=float(rect.x1), y1=float(rect.y1))
            return GeometryType.RECTANGLE, rect_obj
        if len(items) == 1 and items[0][0] == "l":
            _, start, end = items[0]
            line = LineSegment(start=Point(x=float(start.x), y=float(start.y)),
                              end=Point(x=float(end.x), y=float(end.y)),
                              stroke_color=stroke_info["color"],
                              stroke_width=float(stroke_info["width"]),
                              stroke_opacity=float(stroke_info["stroke_opacity"]))
            return GeometryType.LINE, line
        if items[0][0] in ("c", "y", "l"):
            curve = Curve.from_drawings_dict(items[0], stroke_info)
            return GeometryType.CURVE, curve
        polyline = Polyline.from_drawings_dict(items, stroke_info)
        return GeometryType.POLYLINE, polyline
    
    def to_line_segment(self) -> Optional[LineSegment]:
        if self.geometry_type == GeometryType.LINE:
            return self.geometry
        return None
    
    def to_polyline(self) -> Optional[Polyline]:
        if self.geometry_type == GeometryType.POLYLINE:
            return self.geometry
        return None
    
    def to_curve(self) -> Optional[Curve]:
        if self.geometry_type == GeometryType.CURVE:
            return self.geometry
        return None
    
    def to_rectangle(self) -> Optional[Rectangle]:
        if self.geometry_type == GeometryType.RECTANGLE:
            return self.geometry
        return None


@dataclass
class PageGeometry:
    """
    All geometry and text extracted from a single PDF page.
    
    Contains references to all vector elements and text found on the page,
    along with page metadata.
    """
    page_index: int
    page_label: Optional[str] = None
    page_size: Optional[Tuple[float, float]] = None  # (width, height) in points
    media_box: Optional[Rectangle] = None
    crop_box: Optional[Rectangle] = None
    rotation: int = 0
    
    vector_elements: List[DrawingElement] = field(default_factory=list)
    text_elements: List[TextElement] = field(default_factory=list)
    
    # Counts for quick reference
    vector_element_count: int = 0
    text_element_count: int = 0
    
    def add_vector_element(self, element: DrawingElement):
        """Add a vector element to this page."""
        self.vector_elements.append(element)
        self.vector_element_count = len(self.vector_elements)
    
    def add_text_element(self, element: TextElement):
        """Add a text element to this page."""
        self.text_elements.append(element)
        self.text_element_count = len(self.text_elements)
    
    def get_lines(self) -> List[LineSegment]:
        """Get all line elements from this page."""
        return [e.to_line_segment() for e in self.vector_elements 
                if e.to_line_segment() is not None]
    
    def get_rectangles(self) -> List[Rectangle]:
        """Get all rectangle elements from this page."""
        return [e.to_rectangle() for e in self.vector_elements 
                if e.to_rectangle() is not None]
    
    def get_polylines(self) -> List[Polyline]:
        """Get all polyline elements from this page."""
        return [e.to_polyline() for e in self.vector_elements 
                if e.to_polyline() is not None]
    
    def get_curves(self) -> List[Curve]:
        """Get all curve elements from this page."""
        return [e.to_curve() for e in self.vector_elements 
                if e.to_curve() is not None]


@dataclass
class PdfDocument:
    """
    Container for all extracted information from a PDF document.
    
    This is the main output of the PDF processing layer.
    """
    filepath: str
    page_count: int
    pages: List[PageGeometry] = field(default_factory=list)
    
    def get_page(self, index: int) -> Optional[PageGeometry]:
        """Get geometry for a specific page by index."""
        if 0 <= index < len(self.pages):
            return self.pages[index]
        return None
    
    def get_page_by_label(self, label: str) -> Optional[PageGeometry]:
        """Get geometry for a specific page by label."""
        for page in self.pages:
            if page.page_label == label:
                return page
        return None


class PdfProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass


class FileNotFoundError(PdfProcessingError):
    """Raised when the PDF file cannot be found."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"File not found: {filepath}")


class InvalidPdfError(PdfProcessingError):
    """Raised when the file is not a valid PDF."""
    def __init__(self, filepath: str, message: str = "Invalid PDF file"):
        self.filepath = filepath
        self.message = message
        super().__init__(f"Invalid PDF ({filepath}): {message}")


class EmptyPdfError(PdfProcessingError):
    """Raised when the PDF has no pages."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"PDF has no pages: {filepath}")


class PermissionError(PdfProcessingError):
    """Raised when there are permission issues accessing the file."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"Permission denied: {filepath}")
