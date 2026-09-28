# Architecture Overview

## Core Principles

1. Modular architecture
2. Deterministic geometry processing
3. Local-only operation
4. Clear separation of concerns
5. Explicit verification

## Technology Stack

- PySide6 for UI
- PyMuPDF for PDF processing
- SQLite for persistence
- Pytest for testing

## Modules

### 1. PDF Processing (src/modules/pdf_processing/)

Handles PDF ingestion and vector geometry extraction.

Key components:
- geometry_models.py: Domain models for PDF content (Point, Rectangle, LineSegment, Polyline, Curve, TextElement, DrawingElement, PageGeometry, PdfDocument)
- pdf_processor.py: Main PdfProcessor class for opening and extracting PDF data
- __init__.py: Module exports

Features:
- Opens PDF files safely with error handling
- Extracts page metadata (size, rotation, media/crop boxes)
- Extracts vector geometry (lines, rectangles, paths, curves)
- Extracts text elements with positions and formatting
- Preserves PDF-native coordinates (not converted to pixels)
- Isolates PyMuPDF implementation details

### 2. Measurement (src/modules/measurement/)

Handles geometric measurements with explicit scale calibration.

Key components:
- calibration.py: Calibration model with scale factors and unit conversion
- measurement_models.py: Measurement result and traceability models
- measurement_engine.py: Measurement operations (distance, polyline, polygon)
- __init__.py: Module exports

Features:
- Explicit scale calibration from known reference measurements
- No implicit scale assumptions (e.g., no hardcoded 1:100)
- Deterministic geometric calculations (Euclidean distance, shoelace formula)
- Full traceability: every measurement includes source information
- Support for multiple real-world units (mm, cm, m)

Architecture flow:
```
PDF geometry (Point, Polyline, Polygon)
    ↓
MeasurementEngine with Calibration
    ↓
PDF-space measurement (points or points²)
    ↓
Unit conversion via Calibration
    ↓
Real-world measurement with traceability
```

Key principles:
- PDF measurements use the coordinate system from pdf_processing module
- Real-world units are explicit and must be specified via Calibration
- Area conversions use squared calibration factor
- All calculations are deterministic and reproducible
- Measurement results preserve source page, geometry, and calculation method

### 3. Measurement Error Handling

Custom exceptions for measurement domain:
- ValueError for invalid calibration parameters (non-positive distances)
- ValueError for invalid polygon vertices (< 3 points)
- ValueError for invalid polyline points (< 2 points)
- ValueError for negative distances or areas

### 4. UI Layer

User interface components.

### 5. Persistence

Data storage and retrieval.

### 6. Testing Framework

Automated tests for all components.

## PDF Coordinate System

PyMuPDF (which wraps MuPDF) uses a coordinate system with the following characteristics:

### PyMuPDF/MuPDF Coordinate System (used internally)

- **Origin (0,0)**: Top-left of the page
- **X-axis**: Extends to the right
- **Y-axis**: Extends downward (NOT upward)
- **Units**: Points (1/72 inch)
- **A4 page**: 595 x 842 points

This is the coordinate system used by PyMuPDF's `page.rect`, `page.get_drawings()`,
and all geometry extraction functions.

### PDF Coordinate System (different from MuPDF)

- **Origin (0,0)**: Bottom-left of the page
- **X-axis**: Extends to the right
- **Y-axis**: Extends upward

### Transformation Between Spaces

The `page.transformation_matrix` converts from PDF space to MuPDF space:
- For 0-degree rotation: `Matrix(1, 0, 0, -1, 0, page_height)`
- This means: `x_mupdf = x_pdf`, `y_mupdf = page_height - y_pdf`

### Rotation Handling

- `page.rect`: Returns the page rectangle in MuPDF coordinates
- `page.rotation`: Returns the page rotation angle (0, 90, 180, 270)
- `page.transformation_matrix`: Converts PDF space to MuPDF space (handles rotation)
- `page.rotation_matrix`: Rotates points within the rotated page space
- `page.derotation_matrix`: Converts from rotated space back to unrotated space

**Important**: Page coordinates from `page.get_drawings()` and `page.get_text()` 
are returned in the page's unrotated coordinate space (before rotation transformation).
Use `page.rotation_matrix` or `page.derotation_matrix` for coordinate transformations
if needed.

## Error Handling

Custom exceptions for PDF processing:
- PdfProcessingError: Base exception class
- FileNotFoundError: PDF file not found
- InvalidPdfError: File is not a valid PDF
- EmptyPdfError: PDF has no pages
- PermissionError: Access denied to file
