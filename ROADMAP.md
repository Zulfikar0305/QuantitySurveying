# Development Roadmap

## Phase 1: Foundation
- Basic UI
- PDF Loading
- Basic Geometry

## Phase 2: PDF Ingestion and Geometry Extraction (COMPLETED)
- Deterministic PDF ingestion
- Vector geometry extraction
- Text extraction
- Domain models for PDF content
- Coordinate preservation (PDF-native, not pixels)
- Error handling
- Automated tests

## Phase 3: Measurement
### Phase 3 - Task 1: Measurement Foundation (COMPLETED)
- Scale/calibration domain models
- Explicit unit handling (mm, cm, m)
- Deterministic point-to-point distance
- Deterministic polyline length
- Deterministic polygon area (shoelace formula)
- Deterministic polygon perimeter
- Measurement result/traceability models
- Comprehensive unit tests
- Full architecture documentation

### Phase 3 - Task 2: PDF Viewer and Coordinate Mapping Foundation (COMPLETED)
- PDF viewer module (src/modules/viewer/)
- PDF rendering module (PyMuPDF-based rendering)
- Viewport model (zoom, pan, rotation state)
- Coordinate mapper (bidirectional coordinate transformation)
- PDF Viewer widget (PySide6-based UI)
- Page navigation (first, previous, next, last)
- Zoom controls (in, out, reset, fit-to-page)
- Pan/scroll functionality
- Coordinate mapping API (page_to_screen, screen_to_page)
- Page rotation handling (0, 90, 180, 270 degrees)
- Error handling and validation
- Comprehensive unit tests (28 new tests)
- Architecture documentation updates

### Phase 3 - Task 3: (Next)
- Snapping
- Dimension Interpretation
- Verification

## Phase 4: Advanced Features
- Snapping
- Dimension Interpretation
- Verification
