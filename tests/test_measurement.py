# Tests for Measurement Module

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from modules.measurement import (
    Calibration, Unit, UnitSystem,
    MeasurementType, MeasurementResult, TraceabilityInfo,
    MeasurementEngine
)
from src.modules.pdf_processing.geometry_models import Point


# Fixtures
@pytest.fixture
def calibration_mm():
    return Calibration(
        pdf_reference_distance=250.0,
        real_world_reference_distance=5000.0,
        unit=Unit.MILLIMETRES
    )


@pytest.fixture
def calibration_cm():
    return Calibration(
        pdf_reference_distance=100.0,
        real_world_reference_distance=1000.0,
        unit=Unit.CENTIMETRES
    )


@pytest.fixture
def calibration_m():
    return Calibration(
        pdf_reference_distance=1000.0,
        real_world_reference_distance=10.0,
        unit=Unit.METRES
    )


@pytest.fixture
def engine_mm(calibration_mm):
    return MeasurementEngine(calibration=calibration_mm)


@pytest.fixture
def engine_cm(calibration_cm):
    return MeasurementEngine(calibration=calibration_cm)


class TestCalibration:
    def test_valid_calibration(self, calibration_mm):
        assert calibration_mm.pdf_reference_distance == 250.0
        assert calibration_mm.real_world_reference_distance == 5000.0
        assert calibration_mm.unit == Unit.MILLIMETRES
    
    def test_zero_pdf_reference_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            Calibration(
                pdf_reference_distance=0.0,
                real_world_reference_distance=5000.0,
                unit=Unit.MILLIMETRES
            )
    
    def test_negative_pdf_reference_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            Calibration(
                pdf_reference_distance=-100.0,
                real_world_reference_distance=5000.0,
                unit=Unit.MILLIMETRES
            )
    
    def test_zero_real_world_reference_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            Calibration(
                pdf_reference_distance=250.0,
                real_world_reference_distance=0.0,
                unit=Unit.MILLIMETRES
            )
    
    def test_negative_real_world_reference_raises_error(self):
        with pytest.raises(ValueError, match="must be positive"):
            Calibration(
                pdf_reference_distance=250.0,
                real_world_reference_distance=-5000.0,
                unit=Unit.MILLIMETRES
            )
    
    def test_units_per_pdf_point(self, calibration_mm):
        assert calibration_mm.units_per_pdf_point == 20.0
    
    def test_pdf_points_per_unit(self, calibration_mm):
        assert calibration_mm.pdf_points_per_unit == 0.05
    
    def test_pdf_to_real_world_mm(self, calibration_mm):
        assert calibration_mm.pdf_to_real_world(100.0) == 2000.0
        assert calibration_mm.pdf_to_real_world(250.0) == 5000.0
    
    def test_pdf_to_real_world_cm(self, calibration_cm):
        assert calibration_cm.pdf_to_real_world(100.0) == 1000.0
        assert calibration_cm.pdf_to_real_world(50.0) == 500.0
    
    def test_convert_area_squared_factor(self, calibration_mm):
        assert calibration_mm.convert_area(100.0) == 40000.0
