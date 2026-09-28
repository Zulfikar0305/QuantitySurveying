# PDF processing module for vector geometry and text extraction

from .geometry_models import (
    PdfDocument,
    PageGeometry,
    TextElement,
    DrawingElement,
    LineSegment,
    Polyline,
    Curve,
    Rectangle,
    Point,
    GeometryType,
    PdfProcessingError,
    FileNotFoundError,
    InvalidPdfError,
    EmptyPdfError,
    PermissionError,
)
from .pdf_processor import PdfProcessor

__all__ = [
'PdfDocument',
'PageGeometry',
'TextElement',
'DrawingElement',
'LineSegment',
'Polyline',
'Curve',
'Rectangle',
'Point',
'GeometryType',
'PdfProcessingError',
'FileNotFoundError',
'InvalidPdfError',
'EmptyPdfError',
'PermissionError',
'PdfProcessor',
]
