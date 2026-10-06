# Regression tests for PDFViewer initialization state
# 
# Note: PDFViewer is a QWidget subclass which requires QApplication.
# These tests verify the __init__ code directly by inspecting the source.

import pytest
import sys
import os
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestPDFViewerInitAttributes:
    """Verify PDFViewer __init__ initializes all required attributes."""

    def test_init_source_has_current_page_geometry(self):
        """Verify _current_page_geometry is initialized in __init__."""
        from src.modules.viewer.pdf_viewer import PDFViewer
        init_source = inspect.getsource(PDFViewer.__init__)
        
        # Check that _current_page_geometry is assigned in __init__
        assert '_current_page_geometry = None' in init_source, \
            "_current_page_geometry must be initialized in __init__"

    def test_init_source_has_measurement_session_manager(self):
        """Verify _measurement_session_manager is initialized in __init__."""
        from src.modules.viewer.pdf_viewer import PDFViewer
        init_source = inspect.getsource(PDFViewer.__init__)
        
        assert '_measurement_session_manager:' in init_source, \
            "_measurement_session_manager must be declared in __init__"

    def test_init_source_has_no_lazy_measurement_session_manager(self):
        """Verify there's no lazy initialization of _measurement_session_manager."""
        from src.modules.viewer.pdf_viewer import PDFViewer
        init_source = inspect.getsource(PDFViewer.__init__)
        
        # Should NOT have hasattr check for lazy initialization
        assert 'hasattr' not in init_source or '_measurement_session_manager' not in init_source, \
            "Should not use hasattr for lazy initialization of _measurement_session_manager"
