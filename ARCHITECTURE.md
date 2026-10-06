# Architecture Overview

## Product goal

This repository is a local Windows desktop quantity surveying measurement application built around deterministic PDF geometry and explicit scale calibration. The product is not AI-dependent and does not build its measurement logic around external services.

## Core architecture

### 1. PDF processing layer

The PDF processing stack lives under [src/modules/pdf_processing](src/modules/pdf_processing) and is responsible for safely opening files and extracting page geometry.

Key modules:
- [src/modules/pdf_processing/geometry_models.py](src/modules/pdf_processing/geometry_models.py): point, rectangle, segment and polyline models
- [src/modules/pdf_processing/pdf_processor.py](src/modules/pdf_processing/pdf_processor.py): document loading and extraction pipeline

The important design rule is that raw PDF geometry stays authoritative. Rendering is visual only; measurements are derived from geometry and coordinate mapping rather than from image pixels.

### 2. Viewer and coordinate system layer

The viewer layer under [src/modules/viewer](src/modules/viewer) is responsible for page rendering, zoom, pan, fit-to-page, cursor mapping and measurement interaction.

Core modules:
- [src/modules/viewer/viewport.py](src/modules/viewer/viewport.py): explicit viewport state model
- [src/modules/viewer/coordinate_mapper.py](src/modules/viewer/coordinate_mapper.py): page/screen transform logic
- [src/modules/viewer/rendering.py](src/modules/viewer/rendering.py): PDF page rendering pipeline
- [src/modules/viewer/pdf_viewer.py](src/modules/viewer/pdf_viewer.py): Qt-based workflow widget

This layer keeps the coordinate system centralized so the UI does not duplicate conversions or invent a second geometry model.

### 3. Measurement and calibration layer

The deterministic measurement stack is under [src/modules/measurement](src/modules/measurement).

Core modules:
- [src/modules/measurement/calibration.py](src/modules/measurement/calibration.py): explicit scale calibration and unit conversion
- [src/modules/measurement/measurement_engine.py](src/modules/measurement/measurement_engine.py): distance, polyline, area and perimeter calculation logic
- [src/modules/measurement/interaction.py](src/modules/measurement/interaction.py): tool state and measurement interaction flow
- [src/modules/measurement/snapping.py](src/modules/measurement/snapping.py): deterministic snap candidates and target selection
- [src/modules/measurement/measurement_models.py](src/modules/measurement/measurement_models.py): measurement result and traceability objects
- [src/modules/measurement/measurement_session.py](src/modules/measurement/measurement_session.py): session storage per PDF

This is the most important domain surface in the project. The measurement logic is deterministic and remains independent from AI or external interpretation.

### 4. Desktop application shell

The application shell is centered in [src/main.py](src/main.py). It is structured as a drawing-first workspace with:

- top application toolbar for project and viewer controls
- left tool rail for measurement/calibration selection and snapping toggles
- central PDF canvas as the primary workspace
- right measurement list panel
- status bar for page, zoom and calibration state

### 5. Local project and export foundation

The application has started integrating persistent project storage and structured exports:

- [src/modules/project/project_store.py](src/modules/project/project_store.py): SQLite-backed project and measurement persistence
- [src/modules/export/export_manager.py](src/modules/export/export_manager.py): CSV/JSON export foundation

These modules are intentionally local and desktop-focused; they are not meant to introduce a backend or cloud dependency.

## Data flow

The measurement workflow remains:

1. User clicks inside the PDF viewer
2. Qt events are routed to the viewer and converted into page coordinates
3. Snapping selects the best deterministic geometry target
4. The measurement tool records the points and calls the measurement engine
5. Calibration is applied if active
6. The resulting measurement is stored with traceability metadata
7. The overlay and measurement list are updated from the same underlying model

This avoids the common bug pattern where the UI appears to have a tool but never reaches the real calculation path.

## Coordinate system

The project uses the PyMuPDF/MuPDF convention directly:

- origin at the top-left of the page
- X increases right
- Y increases downward
- units are in points

This is preserved consistently across the viewer, mapper and measurement engine.

## Product principles

- geometry remains authoritative
- calibration is explicit
- measurements stay traceable
- local desktop workflow remains the target
- AI is optional later, not required for core work
- UI code should orchestrate domain services rather than duplicate calculation logic

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
