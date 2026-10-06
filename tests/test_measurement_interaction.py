# Tests for Measurement Interaction Module

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from modules.measurement import (
    Calibration, Unit,
    MeasurementState, SnappedPoint,
    MeasurementInteraction, DistanceTool,
    MeasurementEngine
)
from modules.viewer import CoordinateMapper
from modules.pdf_processing import Point


# Fixtures
@pytest.fixture
def coordinate_mapper():
    return CoordinateMapper(
        zoom=2.0,
        offset_x=50.0,
        offset_y=100.0,
        page_width=595.0,
        page_height=842.0,
        page_rotation=0
    )


@pytest.fixture
def calibration():
    return Calibration(
        pdf_reference_distance=250.0,
        real_world_reference_distance=5000.0,
        unit=Unit.MILLIMETRES
    )


@pytest.fixture
def measurement_engine(calibration):
    return MeasurementEngine(calibration=calibration)


@pytest.fixture
def interaction(coordinate_mapper, measurement_engine):
    interaction = MeasurementInteraction(
        coordinate_mapper=coordinate_mapper,
        measurement_engine=measurement_engine
    )
    interaction.set_page_info(0, "Sheet 1")
    return interaction


class TestMeasurementState:
    def test_state_enum_values(self):
        assert MeasurementState.IDLE.value == "idle"
        assert MeasurementState.WAITING_FOR_END.value == "waiting_for_end"
        assert MeasurementState.COMPLETED.value == "completed"


class TestSnappedPoint:
    def test_unsnapped_point(self):
        point = SnappedPoint(
            snapped=False,
            original_page_point=(100.0, 200.0),
            final_page_point=(100.0, 200.0),
            snap_type=None,
            source_geometry_id=None
        )
        assert point.snapped is False
        assert point.snap_type is None
    
    def test_snapped_point(self):
        point = SnappedPoint(
            snapped=True,
            original_page_point=(100.5, 200.3),
            final_page_point=(100.0, 200.0),
            snap_type="endpoint",
            source_geometry_id="line_1"
        )
        assert point.snapped is True
        assert point.snap_type == "endpoint"


class TestMeasurementInteraction:
    def test_initial_state_is_idle(self, interaction):
        assert interaction.state == MeasurementState.IDLE
    
    def test_first_click_moves_to_waiting_for_end(self, interaction):
        # First click should set state to WAITING_FOR_END
        result = interaction.handle_click(100, 100)
        assert interaction.state == MeasurementState.WAITING_FOR_END
        assert result is None
    
    def test_second_click_completes_measurement(self, interaction):
        # First click - start
        interaction.handle_click(100, 100)
        assert interaction.state == MeasurementState.WAITING_FOR_END
        
        # Second click - complete
        result = interaction.handle_click(200, 100)
        assert interaction.state == MeasurementState.COMPLETED
        assert result is not None
        assert result.measurement_type.value == "distance"
    
    def test_completed_measurement_resets_on_new_click(self, interaction):
        # Complete a measurement
        interaction.handle_click(100, 100)
        interaction.handle_click(200, 100)
        assert interaction.state == MeasurementState.COMPLETED
        
        # Another click starts new measurement
        result = interaction.handle_click(300, 100)
        assert interaction.state == MeasurementState.WAITING_FOR_END
        assert result is None
    
    def test_cancel_returns_to_idle(self, interaction):
        # Start measurement
        interaction.handle_click(100, 100)
        assert interaction.state == MeasurementState.WAITING_FOR_END
        
        # Cancel
        interaction.cancel()
        assert interaction.state == MeasurementState.IDLE
    
    def test_reset_returns_to_idle(self, interaction):
        # Start measurement
        interaction.handle_click(100, 100)
        assert interaction.state == MeasurementState.WAITING_FOR_END
        
        # Reset
        interaction.reset()
        assert interaction.state == MeasurementState.IDLE
    
    def test_measurement_without_engine_returns_none(self, coordinate_mapper):
        interaction = MeasurementInteraction(coordinate_mapper=coordinate_mapper)
        result = interaction.handle_click(100, 100)
        assert result is None
    
    def test_measurement_without_mapper_returns_none(self, measurement_engine):
        interaction = MeasurementInteraction(measurement_engine=measurement_engine)
        result = interaction.handle_click(100, 100)
        assert result is None


class TestDistanceTool:
    def test_activation(self, coordinate_mapper, measurement_engine):
        tool = DistanceTool(coordinate_mapper, measurement_engine)
        tool.activate(0, "Sheet 1")
        assert tool.interaction.state == MeasurementState.IDLE
    
    def test_handle_click(self, coordinate_mapper, measurement_engine):
        tool = DistanceTool(coordinate_mapper, measurement_engine)
        tool.activate(0, "Sheet 1")
        
        # First click
        result1 = tool.handle_click(100, 100)
        assert result1 is None
        assert tool.interaction.state == MeasurementState.WAITING_FOR_END
        
        # Second click
        result2 = tool.handle_click(200, 100)
        assert result2 is not None
        assert tool.interaction.state == MeasurementState.COMPLETED
        assert result2.measurement_type.value == "distance"
    
    def test_cancel(self, coordinate_mapper, measurement_engine):
        tool = DistanceTool(coordinate_mapper, measurement_engine)
        tool.activate(0, "Sheet 1")
        
        tool.handle_click(100, 100)
        tool.cancel()
        assert tool.interaction.state == MeasurementState.IDLE


class TestUncalibratedMeasurement:
    """Tests for measurements without calibration (PDF-space only)."""
    
    @pytest.fixture
    def uncalibrated_interaction(self, coordinate_mapper):
        """Create an interaction without calibration."""
        engine = MeasurementEngine(calibration=None)
        interaction = MeasurementInteraction(
            coordinate_mapper=coordinate_mapper,
            measurement_engine=engine
        )
        interaction.set_page_info(0, "Sheet 1")
        return interaction
    
    def test_distance_measurement_without_calibration(self, uncalibrated_interaction):
        """Test that distance measurement works without calibration."""
        # First click - start measurement
        result1 = uncalibrated_interaction.handle_click(50, 100)
        assert result1 is None
        assert uncalibrated_interaction.state == MeasurementState.WAITING_FOR_END
        
        # Second click - complete measurement
        # page(0,0) -> screen(50, 100) with zoom=2, offset=(50, 100)
        # page(100,0) -> screen(250, 100)
        result2 = uncalibrated_interaction.handle_click(250, 100)
        assert result2 is not None
        assert uncalibrated_interaction.state == MeasurementState.COMPLETED
        assert result2.measurement_type.value == "distance"
        assert result2.pdf_value == 100.0  # Should still get PDF distance
    
    def test_uncalibrated_result_has_no_real_world_value(self, uncalibrated_interaction):
        """Test that uncalibrated result doesn't claim real-world units."""
        uncalibrated_interaction.handle_click(50, 100)
        result = uncalibrated_interaction.handle_click(250, 100)
        
        assert result.real_world_value is None
        assert result.unit is None
        assert result.calibration is None
    
    def test_uncalibrated_result_has_correct_status(self, uncalibrated_interaction):
        """Test that uncalibrated result has 'uncalibrated' status."""
        uncalibrated_interaction.handle_click(50, 100)
        result = uncalibrated_interaction.handle_click(250, 100)
        
        assert result.status == "uncalibrated"
    
    def test_uncalibrated_measurement_engine(self, coordinate_mapper):
        """Test that MeasurementEngine can be created without calibration."""
        engine = MeasurementEngine(calibration=None)
        assert engine.calibration is None
        
        # Should be able to create distance tool with uncalibrated engine
        tool = DistanceTool(coordinate_mapper, engine)
        assert tool.interaction.measurement_engine == engine
    
    def test_distance_tool_without_calibration(self, coordinate_mapper):
        """Test that DistanceTool works without calibration."""
        engine = MeasurementEngine(calibration=None)
        tool = DistanceTool(coordinate_mapper, engine)
        tool.activate(0, "Sheet 1")
        
        # First click at page(0,0) -> screen(50, 100)
        result1 = tool.handle_click(50, 100)
        assert result1 is None
        
        # Second click at page(100,0) -> screen(250, 100)
        result2 = tool.handle_click(250, 100)
        assert result2 is not None
        assert result2.pdf_value == 100.0
        assert result2.real_world_value is None
        assert result2.unit is None
    
    def test_uncalibrated_result_to_dict(self, uncalibrated_interaction):
        """Test that uncalibrated result to_dict handles None values correctly."""
        uncalibrated_interaction.handle_click(50, 100)
        result = uncalibrated_interaction.handle_click(250, 100)
        
        result_dict = result.to_dict()
        assert result_dict["pdf_value"] == 100.0
        assert result_dict["calibration"] is None
        assert result_dict["unit"] is None
        assert result_dict["real_world_value"] is None
        assert result_dict["status"] == "uncalibrated"
    
    def test_uncalibrated_result_repr(self, uncalibrated_interaction):
        """Test that uncalibrated result repr shows Uncalibrated."""
        uncalibrated_interaction.handle_click(50, 100)
        result = uncalibrated_interaction.handle_click(250, 100)
        
        repr_str = repr(result)
        assert "Uncalibrated" in repr_str
        assert "pdf=100.00pt" in repr_str
    
    def test_uncalibrated_real_world_in_returns_none(self, uncalibrated_interaction):
        """Test that real_world_in returns None for uncalibrated measurements."""
        uncalibrated_interaction.handle_click(50, 100)
        result = uncalibrated_interaction.handle_click(250, 100)
        
        assert result.real_world_in(Unit.MILLIMETRES) is None
        assert result.real_world_in(Unit.CENTIMETRES) is None
        assert result.real_world_in(Unit.METRES) is None


class TestCoordinateMapping:
    def test_screen_to_page_conversion(self, interaction):
        # Click at screen position
        result = interaction.handle_click(250, 300)
        
        # Verify coordinate mapping
        page_x, page_y = interaction.coordinate_mapper.screen_to_page((250, 300))
        assert abs(page_x - 100.0) < 0.001
        assert abs(page_y - 100.0) < 0.001


class TestSnapping:
    @pytest.fixture
    def vector_elements(self):
        # Create mock vector elements with lines
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
        
        return [MockLine(100, 100, 200, 100)]
    
    @pytest.fixture
    def polyline_elements(self):
        class MockPolyline:
            def __init__(self, points):
                self.points = points
        
        points = [
            Point(x=300, y=300),
            Point(x=400, y=300),
            Point(x=400, y=400)
        ]
        return [MockPolyline(points)]
    
    def test_snapping_to_line_endpoint(self, interaction, vector_elements):
        interaction.set_geometry(vector_elements, [])
        
        # The vector_elements fixture creates a line from page (100, 100) to (200, 100)
        # With zoom=2, offset=(50, 100), screen coords for page(100,100) = (250, 300)
        # Click at screen (245, 295) which is near (250, 300)
        result = interaction._apply_snapping(245, 295)
        assert result.snapped is True
        # Snapped point should be close to the line endpoint in page coordinates
    
    def test_no_snap_outside_tolerance(self, interaction, vector_elements):
        interaction.set_geometry(vector_elements, [])
        
        # Click far from any geometry
        result = interaction._apply_snapping(1000, 1000)
        assert result.snapped is False
        assert result.snap_type is None


class TestMeasurementCalculation:
    def test_horizontal_distance_calculation(self, interaction, calibration):
        # Points: (0, 0) to (100, 0) in page coordinates
        # With zoom=2, offset=(50, 100), screen coords:
        # page(0,0) -> screen(50, 100)
        # page(100,0) -> screen(250, 100)
        interaction.handle_click(50, 100)  # First click
        result = interaction.handle_click(250, 100)  # Second click
        
        assert result.pdf_value == 100.0
        assert abs(result.real_world_value - 2000.0) < 0.001
    
    def test_vertical_distance_calculation(self, interaction):
        # page(0,0) -> screen(50, 100)
        # page(0,100) -> screen(50, 300)
        interaction.handle_click(50, 100)
        result = interaction.handle_click(50, 300)
        
        assert result.pdf_value == 100.0
    
    def test_diagonal_distance_calculation(self, interaction):
        # page(0,0) -> screen(50, 100)
        # page(300,400) -> screen(650, 900)
        interaction.handle_click(50, 100)
        result = interaction.handle_click(650, 900)
        
        # Distance = sqrt(300^2 + 400^2) = 500
        assert result.pdf_value == 500.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
