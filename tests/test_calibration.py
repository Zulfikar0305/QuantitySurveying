# Tests for Calibration Module

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from modules.measurement import (
    Calibration, Unit, CalibrationInteraction, CalibrationTool, CalibrationState,
    CalibratedPoint
)
from modules.viewer import CoordinateMapper
import math


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
def calibration_mm():
    return Calibration(
        pdf_reference_distance=250.0,
        real_world_reference_distance=5000.0,
        unit=Unit.MILLIMETRES
    )


class TestCalibrationInteraction:
    """Tests for the CalibrationInteraction class."""
    
    def test_initial_state_is_idle(self, coordinate_mapper):
        """Test that initial state is IDLE."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        assert interaction.state == CalibrationState.IDLE
    
    def test_activate_starts_selecting_first_point(self, coordinate_mapper):
        """Test that activate changes state to SELECTING_FIRST_POINT."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        assert interaction.state == CalibrationState.SELECTING_FIRST_POINT
    
    def test_activate_with_previous_calibration(self, coordinate_mapper, calibration_mm):
        """Test that activate stores previous calibration."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate(previous_calibration=calibration_mm)
        assert interaction.state == CalibrationState.SELECTING_FIRST_POINT
        
        # Cancel should restore the previous calibration
        restored = interaction.cancel()
        assert restored == calibration_mm
    
    def test_handle_click_first_point(self, coordinate_mapper):
        """Test handling first point click."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        success, message = interaction.handle_click(100, 200)
        
        assert success is True
        assert interaction.state == CalibrationState.SELECTING_SECOND_POINT
        assert interaction.first_point is not None
        assert interaction.first_point.screen_x == 100
        assert interaction.first_point.screen_y == 200
    
    def test_handle_click_second_point(self, coordinate_mapper):
        """Test handling second point click."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # First point
        interaction.handle_click(100, 200)
        
        # Second point - should calculate PDF distance
        success, message = interaction.handle_click(350, 200)
        
        assert success is True
        assert interaction.state == CalibrationState.PROMPTING_REFERENCE
        assert interaction.second_point is not None
        assert "PDF distance" in message
    
    def test_cancel_returns_previous_calibration(self, coordinate_mapper, calibration_mm):
        """Test that cancel restores previous calibration."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate(previous_calibration=calibration_mm)
        
        # Do some work
        interaction.handle_click(100, 200)
        interaction.handle_click(350, 200)
        
        # Cancel should restore previous calibration
        restored = interaction.cancel()
        assert restored == calibration_mm
        assert interaction.state == CalibrationState.CANCELLED
    
    def test_set_reference_distance_valid(self, coordinate_mapper):
        """Test setting valid reference distance."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Set two points - calculate the actual distance based on screen->page conversion
        # Screen (250, 300) -> page: ((250-50)/2, (300-100)/2) = (100, 100)
        # Screen (750, 300) -> page: ((750-50)/2, (300-100)/2) = (350, 100)
        # Distance = 350 - 100 = 250 points
        interaction.handle_click(250, 300)
        interaction.handle_click(750, 300)  # 250 points apart in page space
        
        # Set reference distance
        success, message, calibration = interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        assert success is True
        assert interaction.state == CalibrationState.COMPLETED
        assert calibration is not None
        assert calibration.pdf_reference_distance == 250.0
        assert calibration.real_world_reference_distance == 5000.0
        assert calibration.unit == Unit.MILLIMETRES
        assert "5000.0" in message
    
    def test_set_reference_distance_zero_raises_error(self, coordinate_mapper):
        """Test that zero distance is rejected."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Set two points
        interaction.handle_click(100, 200)
        interaction.handle_click(350, 200)
        
        success, message, calibration = interaction.set_reference_distance(0.0, Unit.MILLIMETRES)
        
        assert success is False
        assert "must be positive" in message
        assert calibration is None
    
    def test_set_reference_distance_negative_raises_error(self, coordinate_mapper):
        """Test that negative distance is rejected."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Set two points
        interaction.handle_click(100, 200)
        interaction.handle_click(350, 200)
        
        success, message, calibration = interaction.set_reference_distance(-5000.0, Unit.MILLIMETRES)
        
        assert success is False
        assert "must be positive" in message
        assert calibration is None
    
    def test_set_reference_distance_nan_raises_error(self, coordinate_mapper):
        """Test that NaN distance is rejected."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Set two points
        interaction.handle_click(100, 200)
        interaction.handle_click(350, 200)
        
        success, message, calibration = interaction.set_reference_distance(float("nan"), Unit.MILLIMETRES)
        
        assert success is False
        assert "finite" in message.lower()
        assert calibration is None
    
    def test_set_reference_distance_inf_raises_error(self, coordinate_mapper):
        """Test that infinity distance is rejected."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Set two points
        interaction.handle_click(100, 200)
        interaction.handle_click(350, 200)
        
        success, message, calibration = interaction.set_reference_distance(float("inf"), Unit.MILLIMETRES)
        
        assert success is False
        assert "finite" in message
        assert calibration is None
    
    def test_get_status_message(self, coordinate_mapper):
        """Test status messages for different states."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        
        # Idle
        assert interaction.get_status_message() == "Calibration inactive"
        
        # Selecting first point
        interaction.activate()
        assert "first reference point" in interaction.get_status_message().lower()
        
        # Selecting second point
        interaction.handle_click(100, 200)
        assert "second reference point" in interaction.get_status_message().lower()
        
        # Prompting reference
        interaction.handle_click(350, 200)
        assert "known distance" in interaction.get_status_message().lower()
        
        # Completed
        interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        assert "calibration:" in interaction.get_status_message().lower()
        
        # Cancelled
        interaction2 = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction2.activate()
        interaction2.cancel()
        assert "cancelled" in interaction2.get_status_message().lower()
    
    def test_get_calibration(self, coordinate_mapper):
        """Test get_calibration method."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        
        # No calibration yet
        assert interaction.get_calibration() is None
        
        # After setting reference distance
        interaction.activate()
        interaction.handle_click(250, 300)  # page (100, 100)
        interaction.handle_click(750, 300)  # page (350, 100)
        interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        calibration = interaction.get_calibration()
        assert calibration is not None
        # Distance is 250 points (350 - 100 = 250)
        assert calibration.pdf_reference_distance == 250.0
        assert calibration.real_world_reference_distance == 5000.0


class TestCalibrationTool:
    """Tests for the CalibrationTool class."""
    
    def test_activate(self, coordinate_mapper):
        """Test tool activation."""
        tool = CalibrationTool(coordinate_mapper=coordinate_mapper)
        tool.activate()
        
        assert tool.interaction.state == CalibrationState.SELECTING_FIRST_POINT
    
    def test_handle_click(self, coordinate_mapper):
        """Test click handling."""
        tool = CalibrationTool(coordinate_mapper=coordinate_mapper)
        tool.activate()
        
        success, message = tool.handle_click(100, 200)
        
        assert success is True
        assert "first point selected" in message.lower()
    
    def test_set_reference_distance(self, coordinate_mapper):
        """Test setting reference distance."""
        tool = CalibrationTool(coordinate_mapper=coordinate_mapper)
        tool.activate()
        
        # Set points
        tool.handle_click(250, 300)
        tool.handle_click(750, 300)
        
        # Set reference distance
        success, message, calibration = tool.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        assert success is True
        assert calibration is not None
    
    def test_cancel(self, coordinate_mapper, calibration_mm):
        """Test tool cancellation."""
        tool = CalibrationTool(coordinate_mapper=coordinate_mapper)
        tool.activate(previous_calibration=calibration_mm)
        
        # Do some work
        tool.handle_click(250, 300)
        
        # Cancel
        restored = tool.cancel()
        
        assert restored == calibration_mm
    
    def test_get_calibration(self, coordinate_mapper):
        """Test get_calibration method."""
        tool = CalibrationTool(coordinate_mapper=coordinate_mapper)
        tool.activate()
        
        assert tool.get_calibration() is None
        
        # Set up calibration
        tool.handle_click(250, 300)
        tool.handle_click(750, 300)
        tool.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        calibration = tool.get_calibration()
        assert calibration is not None


class TestCalibrationCoordinateMapping:
    """Tests for calibration with coordinate mapping."""
    
    def test_screen_to_page_conversion(self, coordinate_mapper):
        """Test that screen coordinates are converted to page correctly."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Click at screen (250, 300) which should be page (100, 100) with zoom=2, offset=(50, 100)
        success, _ = interaction.handle_click(250, 300)
        
        assert success is True
        assert interaction.first_point is not None
        assert abs(interaction.first_point.page_x - 100.0) < 0.001
        assert abs(interaction.first_point.page_y - 100.0) < 0.001
    
    def test_calibration_with_zoom(self, coordinate_mapper):
        """Test that calibration works correctly with zoom."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # Click two points that are 250 points apart in page space
        interaction.handle_click(250, 300)  # page (100, 100)
        interaction.handle_click(750, 300)  # page (350, 100)
        
        # 250 points apart
        success, message, calibration = interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        assert success is True
        assert calibration.pdf_reference_distance == 250.0
    
    def test_calibration_with_rotation(self):
        """Test that calibration works with rotated pages."""
        mapper = CoordinateMapper(
            zoom=2.0,
            offset_x=50.0,
            offset_y=100.0,
            page_width=842.0,  # Swapped for 90-degree rotation
            page_height=595.0,
            page_rotation=90
        )
        
        interaction = CalibrationInteraction(coordinate_mapper=mapper)
        interaction.activate()
        
        # Click points - they will be mapped correctly due to rotation
        interaction.handle_click(250, 300)
        interaction.handle_click(750, 300)
        
        success, message, calibration = interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        assert success is True


class TestCalibrationConversion:
    """Tests for PDF-to-real-world conversion using calibration."""
    
    def test_pdf_to_real_world_conversion(self, coordinate_mapper):
        """Test converting PDF distances to real-world units."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        # 250 points = 5000 mm
        interaction.handle_click(250, 300)  # page (100, 100)
        interaction.handle_click(750, 300)  # page (350, 100)
        interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        calibration = interaction.get_calibration()
        
        # Convert 100 points to mm
        # Linear factor: 5000/250 = 20 mm per point
        assert calibration.pdf_to_real_world(100.0) == 2000.0
        assert calibration.pdf_to_real_world(250.0) == 5000.0
        assert calibration.pdf_to_real_world(50.0) == 1000.0
    
    def test_real_world_to_pdf_conversion(self, coordinate_mapper):
        """Test converting real-world distances to PDF points."""
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        
        interaction.handle_click(250, 300)
        interaction.handle_click(750, 300)
        interaction.set_reference_distance(5000.0, Unit.MILLIMETRES)
        
        calibration = interaction.get_calibration()
        
        # Convert mm to points
        # PDF points per mm = 250/5000 = 0.05
        assert calibration.real_world_to_pdf(2000.0) == 100.0
        assert calibration.real_world_to_pdf(5000.0) == 250.0
        assert calibration.real_world_to_pdf(1000.0) == 50.0
    
    def test_unit_conversions(self, coordinate_mapper):
        """Test calibration with different units."""
        # Test with cm
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        interaction.handle_click(250, 300)
        interaction.handle_click(750, 300)
        interaction.set_reference_distance(500.0, Unit.CENTIMETRES)
        
        cal_cm = interaction.get_calibration()
        assert cal_cm.pdf_reference_distance == 250.0
        assert cal_cm.real_world_reference_distance == 500.0
        assert cal_cm.unit == Unit.CENTIMETRES
        
        # Test with m
        interaction2 = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction2.activate()
        interaction2.handle_click(250, 300)
        interaction2.handle_click(750, 300)
        interaction2.set_reference_distance(5.0, Unit.METRES)
        
        cal_m = interaction2.get_calibration()
        assert cal_m.pdf_reference_distance == 250.0
        assert cal_m.real_world_reference_distance == 5.0
        assert cal_m.unit == Unit.METRES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
