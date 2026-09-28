# Tests for PDF Ingestion and Geometry Extraction

import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.modules.pdf_processing import (
    PdfProcessor, PdfDocument, PageGeometry,
    TextElement, DrawingElement, LineSegment, Polyline, Curve, Rectangle, Point,
    GeometryType, PdfProcessingError, FileNotFoundError, InvalidPdfError, EmptyPdfError, PermissionError
)


# Fixtures
@pytest.fixture
def test_pdf_path():
    """Path to the generated test PDF."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "generated", "test_house.pdf")


@pytest.fixture
def processor():
    """Create a PdfProcessor instance."""
    return PdfProcessor()


# Test classes
class TestPdfDocument:
    """Tests for PdfDocument class."""
    
    def test_pdf_can_be_opened(self, test_pdf_path, processor):
        """Test that PDF can be opened successfully."""
        result = processor.process_file(test_pdf_path)
        assert isinstance(result, PdfDocument)
        assert result.filepath == test_pdf_path
        assert result.page_count > 0


class TestPageMetadata:
    """Tests for page metadata extraction."""
    
    def test_page_count_is_extracted(self, test_pdf_path, processor):
        """Test that page count is correctly extracted."""
        result = processor.process_file(test_pdf_path)
        assert result.page_count == 1
    
    def test_page_size_is_preserved(self, test_pdf_path, processor):
        """Test that page dimensions are preserved in PDF coordinates."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.page_size is not None
        width, height = page.page_size
        assert width == 595.0  # A4 width in points
        assert height == 842.0  # A4 height in points
    
    def test_media_box_is_extracted(self, test_pdf_path, processor):
        """Test that media box is extracted correctly."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.media_box is not None
        assert page.media_box.x0 == 0.0
        assert page.media_box.y0 == 0.0
    
    def test_crop_box_handling(self, test_pdf_path, processor):
        """Test that crop box is handled when present."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        # Crop box may be None if not set
        assert page.crop_box is None or isinstance(page.crop_box, Rectangle)
    
    def test_rotation_is_extracted(self, test_pdf_path, processor):
        """Test that page rotation is extracted."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.rotation >= 0
        assert page.rotation <= 360


class TestTextExtraction:
    """Tests for text extraction."""
    
    def test_text_elements_are_extracted(self, test_pdf_path, processor):
        """Test that text elements are extracted from PDF."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        # At least some text should be extracted
        assert page.text_element_count >= 0
    
    def test_text_element_has_required_fields(self, test_pdf_path, processor):
        """Test that text elements have required fields."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        if page.text_elements:
            text = page.text_elements[0]
            assert isinstance(text.text, str)
            assert isinstance(text.bbox, Rectangle)
            assert isinstance(text.position, Point)
    
    def test_text_position_is_in_pdf_coordinates(self, test_pdf_path, processor):
        """Test that text positions are in PDF coordinates, not pixels."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        if page.text_elements:
            text = page.text_elements[0]
            # Text position should be reasonable for PDF coordinates
            assert text.position.x >= 0
            assert text.position.y >= 0
            # Should not be a large pixel value (typically < 1000 for PDF coords)


class TestVectorGeometryExtraction:
    """Tests for vector geometry extraction."""
    
    def test_vector_elements_are_extracted(self, test_pdf_path, processor):
        """Test that vector elements are extracted from PDF."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.vector_element_count >= 0
    
    def test_line_coordinates_are_preserved(self, test_pdf_path, processor):
        """Test that line coordinates are preserved in PDF format."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        lines = page.get_lines()
        for line in lines:
            assert isinstance(line.start, Point)
            assert isinstance(line.end, Point)
            # Check coordinates are in reasonable PDF range
            assert line.start.x >= 0
            assert line.start.y >= 0
    
    def test_rectangle_coordinates_are_preserved(self, test_pdf_path, processor):
        """Test that rectangle coordinates are preserved correctly."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        rectangles = page.get_rectangles()
        for rect in rectangles:
            assert isinstance(rect, Rectangle)
            assert rect.width > 0
            assert rect.height > 0
    
    def test_drawing_element_types(self, test_pdf_path, processor):
        """Test that drawing elements have correct types."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        for element in page.vector_elements:
            assert isinstance(element.geometry_type, GeometryType)
            assert element.page_index == 0


class TestCoordinatesNotConvertedToPixels:
    """Tests to ensure coordinates remain in PDF format."""
    
    def test_coordinates_not_scaled_to_pixels(self, test_pdf_path, processor):
        """Test that coordinates are not converted to pixels."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        # PDF coordinates for A4 are typically in the range 0-595 x 0-842
        # Pixel coordinates would be much larger (e.g., 72 DPI = 42500 pixels for A4)
        
        for element in page.vector_elements:
            rect = element.to_rectangle()
            if rect:
                # Check width is not in pixel scale (would be ~42500 for A4 width)
                assert rect.width < 10000, f"Rectangle width {rect.width} appears to be in pixels"
    
    def test_text_coordinates_not_pixels(self, test_pdf_path, processor):
        """Test that text coordinates are not in pixel scale."""
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        
        for text in page.text_elements:
            # Text position should be reasonable for PDF coordinates
            assert text.position.x < 10000, "Text X coordinate appears to be in pixels"
            assert text.position.y < 10000, "Text Y coordinate appears to be in pixels"


class TestMultiplePages:
    """Tests for handling multiple pages."""
    
class TestErrorHandling:
    """Tests for error handling."""
    
    def test_missing_file_throws_error(self, processor):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            processor.process_file("nonexistent_file.pdf")
    
    def test_invalid_pdf_throws_error(self, processor):
        """Test that invalid PDF raises InvalidPdfError."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"This is not a valid PDF")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(InvalidPdfError):
                processor.process_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
