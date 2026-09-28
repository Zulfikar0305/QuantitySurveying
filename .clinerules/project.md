# Quantity Surveying Project Rules

## Core Principles

1. **Accuracy is the highest priority.** Never sacrifice measurement accuracy for speed or convenience.

2. **Deterministic geometry processing is preferred over AI estimation.** Always prefer mathematical calculations from vector geometry over AI-based guesses.

3. **Never silently invent measurements.** If a measurement cannot be determined from available geometry, report it clearly to the user rather than making assumptions.

4. **Never silently resolve conflicting measurements.** If conflicting measurements are detected, present them to the user for resolution.

5. **All measurements must be traceable to source geometry.** Keep references to the original PDF pages, objects, and coordinates that produced each measurement.

6. **Preserve original PDFs.** Never modify the source PDF files. All processing should work on copies or in-memory representations.

7. **Separation of concerns.** Keep PDF processing, geometry, measurement, UI, persistence, and AI concerns in separate modules.

8. **Avoid monolithic files.** Break functionality into small, focused modules and classes.

9. **Automated tests for numerical calculations.** All mathematical operations require corresponding unit tests.

10. **Inspect existing code before modifying.** Review current implementation details to understand the design and avoid breaking changes.

11. **Do not delete functionality without explicit instruction.** Preserve existing working code unless explicitly directed otherwise.

12. **Run relevant tests after implementation.** Verify changes don't break existing functionality.

13. **Verify application startup when appropriate.** After UI or import changes, test that the application starts correctly.

14. **Verify filesystem changes.** After creating or moving files, verify the expected structure exists.

15. **Recover from command failures.** If a command fails, diagnose the issue, correct it, and retry rather than stopping.

16. **Core measurement functionality must work offline.** The application should function without internet connectivity.

17. **AI is optional, not required.** Deterministic measurement must work without AI features.

18. **Implement features in bounded tasks.** Each development task should have a clear scope and completion criteria.

## Technology Stack

- Python 3.13
- PySide6 for UI
- PyMuPDF for PDF processing
- SQLite for persistence
- pytest for testing

## File Structure

```
QuantitySurveying/
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── modules/
│       ├── __init__.py
│       ├── pdf_processing/
│       │   └── __init__.py
│       └── pdf_geometry/
│           └── __init__.py
├── tests/
│   └── __init__.py
├── ARCHITECTURE.md
├── DEVELOPMENT.md
├── README.md
├── ROADMAP.md
└── requirements.txt
```