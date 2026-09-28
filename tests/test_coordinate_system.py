# Tests for coordinate system
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pymupdf
from src.modules.pdf_processing import PdfProcessor, Point, Rectangle, PageGeometry


class TestPyMuPDFCoordinateSystem:
    def test_mupdf_has_top_left_origin(self):
        doc = pymupdf.open()
        page = doc.new_page()
        rect = page.rect
        assert rect.x0 == 0.0
        assert rect.y0 == 0.0
        doc.close()

    def test_y_increases_downward(self):
        doc = pymupdf.open()
        page = doc.new_page()
        point_top = pymupdf.Point(100, 100)
        point_lower = pymupdf.Point(100, 700)
        assert point_lower.y > point_top.y
        doc.close()

    def test_transformation_matrix_conversion(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page_height = page.rect.height
        transform = page.transformation_matrix
        assert abs(transform.a - 1.0) < 0.001
        assert transform.d < 0
        pdf_point = pymupdf.Point(100, 100)
        mupdf_point = pdf_point * transform
        expected_y = page_height - 100
        assert abs(mupdf_point.y - expected_y) < 0.001
        doc.close()

    def test_rotation_changes_page_dimensions(self):
        doc = pymupdf.open()
        page = doc.new_page()
        rect_0 = page.rect
        page.set_rotation(90)
        rect_90 = page.rect
        assert abs(rect_90.width - rect_0.height) < 0.001
        doc.close()

    def test_rotation_matrix_for_90_degrees(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.set_rotation(90)
        rotation = page.rotation_matrix
        assert abs(rotation.a) < 0.001
        assert abs(rotation.b - 1.0) < 0.001
        doc.close()

    def test_derotation_matrix(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.set_rotation(90)
        derot = page.derotation_matrix
        assert abs(derot.b + 1.0) < 0.001
        doc.close()


class TestPdfProcessorCoordinates:
    @pytest.fixture
    def test_pdf_path(self):
        return os.path.join(os.path.dirname(__file__), "fixtures", "generated", "test_house.pdf")

    @pytest.fixture
    def processor(self):
        return PdfProcessor()

    def test_extracted_geometry_has_top_left_origin(self, test_pdf_path, processor):
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.media_box.x0 == 0.0
        assert page.media_box.y0 == 0.0
        assert page.media_box.x1 > 0

    def test_coordinates_preserved_as_points(self, test_pdf_path, processor):
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.media_box.width < 10000
        assert page.media_box.height < 10000

    def test_page_rotation_reflected(self, test_pdf_path, processor):
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        assert page.rotation in [0, 90, 180, 270]

    def test_rectangle_coordinates_structure(self, test_pdf_path, processor):
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        for rect in page.get_rectangles():
            assert rect.x0 < rect.x1
            assert rect.y0 < rect.y1

    def test_line_coordinates_structure(self, test_pdf_path, processor):
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        for line in page.get_lines():
            assert isinstance(line.start, Point)
            assert isinstance(line.end, Point)

    def test_text_bounding_box_structure(self, test_pdf_path, processor):
        result = processor.process_file(test_pdf_path)
        page = result.get_page(0)
        for text in page.text_elements:
            assert text.bbox.x0 < text.bbox.x1
            assert text.bbox.y0 < text.bbox.y1


class TestRotationHandling:
    def test_rotated_page_dimensions_swap(self):
        doc = pymupdf.open()
        page = doc.new_page()
        rect_0 = page.rect
        page.set_rotation(90)
        rect_90 = page.rect
        assert abs(rect_90.width - rect_0.height) < 0.001
        doc.close()
