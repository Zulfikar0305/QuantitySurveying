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

### Phase 3 - Task 3: Advanced Deterministic Measurement (COMPLETED)
- Continuous/polyline distance measurement tool
- Polygon area measurement tool
- Polygon perimeter measurement tool
- Enhanced snapping system (endpoints, vertices, intersections, midpoints, nearest point)
- Measurement record/model for traceability
- In-memory measurement session manager
- Page and document isolation
- Full traceability with PDF file, page index, geometry points
- Calibration-aware real-world conversions
- Comprehensive unit tests (120 tests passing)
- Architecture documentation updates

### Phase 3 - Task 5: UI Integration and Snapping Controls (COMPLETED)
- Measurement List UI panel (QWidget-based, dock-style layout)
- Measurement ID, type, page, value, status display
- Calibrated vs uncalibrated measurement indicators
- Select measurement functionality
- Remove selected measurement functionality
- Clear all measurements functionality
- Snapping controls with toggleable options:
  - Endpoint snapping
  - Vertex snapping
  - Intersection snapping
  - Midpoint snapping
  - Nearest point snapping
- All snap types enabled by default
- Individual toggleable via checkboxes
- Snap settings passed to measurement tools
- UI changes reflect immediately in subsequent clicks
- No separate snapping implementation - uses existing deterministic system
- Document reset clears measurement list
- Page navigation preserves measurement list
- Architecture documentation updated
- Full unit test coverage (160 tests passing)

## Phase 4: Advanced Features
- Persistent measurement storage (SQLite)
- Dimension interpretation
- Verification workflow
