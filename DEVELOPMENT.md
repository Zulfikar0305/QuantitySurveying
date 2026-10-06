# Development Guidelines

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

For headless/offscreen startup validation:

```bash
$env:QT_QPA_PLATFORM = 'offscreen'
python -m src.main
```

## Testing

```bash
python -m pytest tests -q
```

## Current build status

This repository is in the product-build phase. The codebase already contains a substantial deterministic measurement foundation, and the current objective is to integrate it into a coherent professional desktop workflow rather than rewiring the geometry engine.

## Important constraints

- Keep the measurement engine deterministic and traceable.
- Preserve the PyMuPDF coordinate convention and avoid multiple coordinate systems.
- Do not require AI or cloud services for core functionality.
- Validate startup and regression behavior with focused checks rather than repeated broad test churn during active implementation.