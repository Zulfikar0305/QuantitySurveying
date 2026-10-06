# Development Roadmap

## Current delivery status

The application is now in a coherent product-build phase. The underlying geometry, calibration, measurement engine, viewer and session layers are substantial and preserved. The current work is focused on integrating them into a professional desktop measurement workspace rather than replacing them.

## Completed foundation

- Deterministic PDF processing and geometry extraction
- Calibration and real-world conversion logic
- Distance, polyline, area and perimeter measurement calculations
- Snapping and traceability models
- PySide6 viewer and workspace shell
- Measurement list/session integration
- Local project persistence using SQLite
- CSV/JSON export foundations
- Automated regression coverage for the domain logic

## Active build focus

- Improve measurement workflow polish and drawing interaction clarity
- Strengthen calibration UX and selection/highlighting behavior
- Build out project reopen and takeoff-item foundations
- Align documentation and product messaging with actual implementation

## Near-term roadmap

### Phase 1: Production-grade viewer workflow
- better measurement preview and selection highlighting
- consistent cancel/undo transitions across tools
- stronger page and zoom management in the drawing workspace
- calibration status and snap state presented clearly in the UI

### Phase 2: Reporting and takeoff foundation
- measurement-to-takeoff item conversion
- richer project persistence and reopen flows
- export to CSV/Excel-ready formats and JSON

### Phase 3: Professional desktop polish
- more refined tool palette and status surfaces
- better handling of complex drawing sets and rotated pages
- user-facing QC and validation workflows

## Explicitly not planned as a requirement

- AI-driven measurement or cloud-based geometry interpretation
- hidden scale assumptions
- external OCR dependence
- non-deterministic measurement logic
