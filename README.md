# QuantitySurveying

Professional desktop quantity surveying measurement workspace for architectural and building-plan PDFs.

## Core purpose

- Open and review architectural/building-plan PDFs
- Fit and navigate drawings in a drawing-first desktop workspace
- Calibrate drawing scale explicitly
- Measure distances, polylines, polygons and perimeters deterministically
- Snap to PDF geometry with explicit snap types
- Preserve measurement traceability back to source PDF coordinates
- Save project sessions locally and export structured measurement data
- Keep the core application independent from AI or cloud services

## Current implementation status

The repository now contains a working desktop app shell and the measurement foundation used by the app:

- PySide6 desktop workspace with left tool rail, center drawing canvas, right measurement panel
- PDF viewer with page navigation, zoom, fit-to-page and panning
- deterministic geometry and measurement engine preserved and integrated
- calibration workflow and measurement list/session management connected to the UI
- local SQLite project persistence and CSV/JSON export foundation

## Requirements

- Python 3.13
- PySide6
- PyMuPDF
- pytest

## Installation

```bash
pip install -r requirements.txt
```

## Running the application

```bash
python -m src.main
```

or

```bash
python src/main.py
```

## Testing

```bash
python -m pytest tests -q
```

## Notes

The underlying geometry system remains the authority. The app does not depend on AI or external services for core measurement functionality.