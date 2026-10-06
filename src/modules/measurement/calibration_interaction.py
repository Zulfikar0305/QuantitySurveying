"""
Measurement interaction module for interactive measurement workflows.

This module provides interactive tools for measurements and calibration:
- DistanceTool: Interactive distance measurement
- CalibrationTool: Interactive scale calibration
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum
import math

from ..viewer.coordinate_mapper import CoordinateMapper
from .measurement_engine import MeasurementEngine
from .measurement_models import MeasurementType, MeasurementResult, TraceabilityInfo
from .calibration import Calibration, Unit


class CalibrationState(Enum):
    """States for the calibration workflow."""
    IDLE = "idle"
    SELECTING_FIRST_POINT = "selecting_first_point"
    SELECTING_SECOND_POINT = "selecting_second_point"
    PROMPTING_REFERENCE = "prompting_reference"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class CalibratedPoint:
    """A point that may or may not have been snapped."""
    screen_x: float
    screen_y: float
    page_x: float
    page_y: float
    snapped: bool = False
    snap_type: Optional[str] = None


class CalibrationInteraction:
    """
    Manages the interactive calibration workflow.
    
    The calibration workflow has these states:
    1. IDLE - No calibration in progress
    2. SELECTING_FIRST_POINT - Waiting for user to click first reference point
    3. SELECTING_SECOND_POINT - Waiting for user to click second reference point
    4. PROMPTING_REFERENCE - User entering known real-world distance
    5. COMPLETED - Calibration established
    6. CANCELLED - Calibration cancelled, previous state preserved
    """
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        self.coordinate_mapper = coordinate_mapper
        self.state = CalibrationState.IDLE
        self.first_point: Optional[CalibratedPoint] = None
        self.second_point: Optional[CalibratedPoint] = None
        self.reference_distance: Optional[float] = None
        self.reference_unit: Optional[Unit] = None
        self._previous_calibration: Optional[Calibration] = None
        self._calibration: Optional[Calibration] = None
    
    def activate(self, previous_calibration: Optional[Calibration] = None):
        """Start a new calibration workflow."""
        self._previous_calibration = previous_calibration
        self.state = CalibrationState.SELECTING_FIRST_POINT
        self.first_point = None
        self.second_point = None
        self.reference_distance = None
        self.reference_unit = None
        self._calibration = None
    
    def cancel(self) -> Optional[Calibration]:
        """Cancel calibration and restore previous state."""
        self.state = CalibrationState.CANCELLED
        self.first_point = None
        self.second_point = None
        self.reference_distance = None
        self.reference_unit = None
        return self._previous_calibration
    
    def handle_click(self, screen_x: float, screen_y: float) -> Tuple[bool, str]:
        """
        Handle a click in screen coordinates.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if self.state == CalibrationState.IDLE:
            return (False, "No calibration in progress")
        
        if self.state == CalibrationState.COMPLETED:
            return (False, "Calibration already completed")
        
        if self.state == CalibrationState.CANCELLED:
            return (False, "Calibration was cancelled")
        
        # Convert screen to page coordinates
        page_x, page_y = self.coordinate_mapper.screen_to_page((screen_x, screen_y))
        
        point = CalibratedPoint(
            screen_x=screen_x,
            screen_y=screen_y,
            page_x=page_x,
            page_y=page_y,
            snapped=False
        )
        
        if self.state == CalibrationState.SELECTING_FIRST_POINT:
            self.first_point = point
            self.state = CalibrationState.SELECTING_SECOND_POINT
            return (True, "First point selected. Select second point.")
        
        elif self.state == CalibrationState.SELECTING_SECOND_POINT:
            if self.first_point is None:
                return (False, "First point not set")
            
            self.second_point = point
            self.state = CalibrationState.PROMPTING_REFERENCE
            
            # Calculate PDF distance
            dx = self.second_point.page_x - self.first_point.page_x
            dy = self.second_point.page_y - self.first_point.page_y
            pdf_distance = math.sqrt(dx * dx + dy * dy)
            
            return (True, f"Second point selected. PDF distance: {pdf_distance:.2f} points. Enter known distance.")
        
        return (False, f"Invalid state for click: {self.state.value}")
    
    def set_reference_distance(self, distance: float, unit: Unit) -> Tuple[bool, str, Optional[Calibration]]:
        """
        Set the reference distance entered by the user.
        
        Returns:
            Tuple of (success: bool, message: str, calibration: Optional[Calibration])
        """
        # Validate input
        if distance is None:
            return (False, "Distance cannot be None", None)
        
        # Check for non-finite values
        if not math.isfinite(distance):
            return (False, "Distance must be a finite number", None)
        
        # Check for zero or negative
        if distance <= 0:
            return (False, "Distance must be positive", None)
        
        # Check for NaN
        if math.isnan(distance):
            return (False, "Distance cannot be NaN", None)
        
        # Store reference
        self.reference_distance = distance
        self.reference_unit = unit
        
        # Calculate PDF reference distance
        if self.first_point is None or self.second_point is None:
            return (False, "Points not set", None)
        
        dx = self.second_point.page_x - self.first_point.page_x
        dy = self.second_point.page_y - self.first_point.page_y
        pdf_distance = math.sqrt(dx * dx + dy * dy)
        
        # Create calibration
        try:
            calibration = Calibration(
                pdf_reference_distance=pdf_distance,
                real_world_reference_distance=distance,
                unit=unit
            )
            self._calibration = calibration
            self.state = CalibrationState.COMPLETED
            
            return (True, f"Calibration established: {pdf_distance:.2f} pt = {distance} {unit.value}", calibration)
        
        except ValueError as e:
            return (False, f"Failed to create calibration: {e}", None)
    
    def get_status_message(self) -> str:
        """Get a status message for the current state."""
        if self.state == CalibrationState.IDLE:
            return "Calibration inactive"
        elif self.state == CalibrationState.SELECTING_FIRST_POINT:
            return "Select first reference point"
        elif self.state == CalibrationState.SELECTING_SECOND_POINT:
            return "Select second reference point"
        elif self.state == CalibrationState.PROMPTING_REFERENCE:
            return "Enter known distance"
        elif self.state == CalibrationState.COMPLETED:
            if self._calibration:
                return f"Calibration: {self._calibration.pdf_reference_distance:.2f} pt = {self._calibration.real_world_reference_distance} {self._calibration.unit.value}"
            return "Calibration completed"
        elif self.state == CalibrationState.CANCELLED:
            return "Calibration cancelled"
        return "Unknown state"
    
    def get_calibration(self) -> Optional[Calibration]:
        """Get the current calibration if available."""
        return self._calibration
    
    def reset(self):
        """Reset to idle state."""
        self.state = CalibrationState.IDLE
        self.first_point = None
        self.second_point = None
        self.reference_distance = None
        self.reference_unit = None
        self._calibration = None


class CalibrationTool:
    """
    Tool for interactive calibration workflow.
    """
    
    def __init__(self, coordinate_mapper: CoordinateMapper):
        self.interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
    
    def activate(self, previous_calibration: Optional[Calibration] = None):
        """Activate the calibration tool."""
        self.interaction.activate(previous_calibration=previous_calibration)
    
    def handle_click(self, screen_x: float, screen_y: float) -> Tuple[bool, str]:
        """Handle a click in screen coordinates."""
        return self.interaction.handle_click(screen_x, screen_y)
    
    def set_reference_distance(self, distance: float, unit: Unit) -> Tuple[bool, str, Optional[Calibration]]:
        """Set the reference distance."""
        return self.interaction.set_reference_distance(distance, unit)
    
    def cancel(self) -> Optional[Calibration]:
        """Cancel the calibration."""
        return self.interaction.cancel()
    
    def get_calibration(self) -> Optional[Calibration]:
        """Get the current calibration."""
        return self.interaction.get_calibration()
    
    def reset(self):
        """Reset the tool."""
        self.interaction.reset()
    
    def get_status_message(self) -> str:
        """Get status message."""
        return self.interaction.get_status_message()
