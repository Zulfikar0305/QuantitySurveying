import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from src.modules.viewer.viewport import Viewport
from src.modules.viewer.coordinate_mapper import CoordinateMapper
from src.modules.viewer.rendering import PDFRenderer


@pytest.fixture
def viewport_params():
    return {
        "zoom": 1.0,
        "offset_x": 0.0,
        "offset_y": 0.0,
        "viewport_width": 800,
        "viewport_height": 600,
        "rendered_page_width": 595,
        "rendered_page_height": 842,
        "page_rotation": 0
    }


@pytest.fixture
def mapper_params():
    return {
        "zoom": 2.0,
        "offset_x": 100.0,
        "offset_y": 50.0,
        "page_width": 595.0,
        "page_height": 842.0,
        "page_rotation": 0
    }


class TestViewport:
    def test_creation_with_valid_params(self, viewport_params):
        vp = Viewport(**viewport_params)
        assert vp.zoom == 1.0

    def test_creation_with_rotation(self, viewport_params):
        vp = Viewport(**{**viewport_params, "page_rotation": 90})
        assert vp.page_rotation == 90

    def test_creation_with_zero_zoom_raises_error(self, viewport_params):
        params = {**viewport_params, "zoom": 0}
        with pytest.raises(ValueError, match="must be positive"):
            Viewport(**params)

    def test_creation_with_negative_zoom_raises_error(self, viewport_params):
        params = {**viewport_params, "zoom": -1.0}
        with pytest.raises(ValueError, match="must be positive"):
            Viewport(**params)

    def test_creation_with_invalid_rotation_raises_error(self, viewport_params):
        params = {**viewport_params, "page_rotation": 45}
        with pytest.raises(ValueError, match="must be 0, 90, 180, or 270"):
            Viewport(**params)

    def test_zoom_in(self, viewport_params):
        vp = Viewport(**viewport_params)
        new_vp = vp.zoom_in(1.5)
        assert new_vp.zoom == 1.5

    def test_zoom_out(self, viewport_params):
        vp = Viewport(**viewport_params)
        new_vp = vp.zoom_out(2.0)
        assert new_vp.zoom == 0.5

    def test_zoom_to(self, viewport_params):
        vp = Viewport(**viewport_params)
        new_vp = vp.zoom_to(2.5)
        assert new_vp.zoom == 2.5

    def test_pan(self, viewport_params):
        vp = Viewport(**viewport_params)
        new_vp = vp.pan(50.0, 100.0)
        assert new_vp.offset_x == 50.0

    def test_fit_to_viewport(self, viewport_params):
        vp = Viewport(**viewport_params)
        new_vp = vp.fit_to_viewport(595, 842)
        assert new_vp.zoom < 1.0

    def test_to_dict(self, viewport_params):
        vp = Viewport(**viewport_params)
        d = vp.to_dict()
        assert d["zoom"] == 1.0

    def test_from_dict(self, viewport_params):
        d = Viewport(**viewport_params).to_dict()
        vp = Viewport.from_dict(d)
        assert vp.zoom == 1.0


class TestCoordinateMapper:
    def test_creation(self, mapper_params):
        cm = CoordinateMapper(**mapper_params)
        assert cm.zoom == 2.0

    def test_zero_zoom_raises_error(self, mapper_params):
        params = {**mapper_params, "zoom": 0}
        with pytest.raises(ValueError, match="must be positive"):
            CoordinateMapper(**params)

    def test_page_to_screen_identity(self, mapper_params):
        params = {**mapper_params, "zoom": 1.0, "offset_x": 0.0, "offset_y": 0.0}
        cm = CoordinateMapper(**params)
        screen = cm.page_to_screen((100, 200))
        assert screen[0] == 100.0
        assert screen[1] == 200.0

    def test_page_to_screen_zoom(self, mapper_params):
        params = {**mapper_params, "zoom": 2.0, "offset_x": 0.0, "offset_y": 0.0}
        cm = CoordinateMapper(**params)
        screen = cm.page_to_screen((100, 200))
        assert screen[0] == 200.0
        assert screen[1] == 400.0

    def test_page_to_screen_translation(self, mapper_params):
        params = {**mapper_params, "zoom": 1.0, "offset_x": 50.0, "offset_y": 100.0}
        cm = CoordinateMapper(**params)
        screen = cm.page_to_screen((100, 200))
        assert screen[0] == 150.0
        assert screen[1] == 300.0

    def test_page_to_screen_zoom_translation(self, mapper_params):
        params = {**mapper_params, "zoom": 2.0, "offset_x": 50.0, "offset_y": 100.0}
        cm = CoordinateMapper(**params)
        screen = cm.page_to_screen((100, 200))
        assert screen[0] == 250.0
        assert screen[1] == 500.0

    def test_screen_to_page(self, mapper_params):
        params = {**mapper_params, "zoom": 2.0, "offset_x": 50.0, "offset_y": 100.0}
        cm = CoordinateMapper(**params)
        page = cm.screen_to_page((250, 500))
        assert page[0] == 100.0
        assert page[1] == 200.0

    def test_round_trip(self, mapper_params):
        params = {**mapper_params, "zoom": 2.0, "offset_x": 50.0, "offset_y": 100.0}
        cm = CoordinateMapper(**params)
        original = (100.0, 200.0)
        screen = cm.page_to_screen(original)
        recovered = cm.screen_to_page(screen)
        assert abs(recovered[0] - original[0]) < 0.001
        assert abs(recovered[1] - original[1]) < 0.001

    def test_to_dict(self, mapper_params):
        cm = CoordinateMapper(**mapper_params)
        d = cm.to_dict()
        assert d["zoom"] == 2.0


class TestCoordinateMapperRotation:
    def test_90_degree_rotation(self):
        cm = CoordinateMapper(zoom=1.0, offset_x=100.0, offset_y=50.0,
                             page_width=595.0, page_height=842.0, page_rotation=90)
        screen = cm.page_to_screen((0, 0))
        assert screen[0] == 100.0

    def test_180_degree_rotation(self):
        cm = CoordinateMapper(zoom=1.0, offset_x=100.0, offset_y=50.0,
                             page_width=595.0, page_height=842.0, page_rotation=180)
        screen = cm.page_to_screen((0, 0))
        assert screen[0] == 695.0

    def test_270_degree_rotation(self):
        cm = CoordinateMapper(zoom=1.0, offset_x=100.0, offset_y=50.0,
                             page_width=595.0, page_height=842.0, page_rotation=270)
        screen = cm.page_to_screen((0, 0))
        assert screen[0] == 942.0


class TestPDFRenderer:
    @pytest.fixture
    def test_pdf_path(self):
        return os.path.join(os.path.dirname(__file__), "fixtures", "generated", "test_house.pdf")

    def test_creation_default_dpi(self):
        renderer = PDFRenderer()
        assert renderer.default_dpi == 150

    def test_creation_custom_default_dpi(self):
        renderer = PDFRenderer(default_dpi=200)
        assert renderer.default_dpi == 200

    def test_invalid_min_dpi_raises_error(self):
        with pytest.raises(ValueError, match="must be between"):
            PDFRenderer(default_dpi=36)

    def test_invalid_max_dpi_raises_error(self):
        with pytest.raises(ValueError, match="must be between"):
            PDFRenderer(default_dpi=700)
