"""
Measurement models for traceability and result reporting.

These models preserve the information needed to explain how a measurement
was produced, enabling auditability and verification.
"""

from dataclasses import dataclass
from typing import List, Optional, Union, Dict, Any
from enum import Enum
import math

from .calibration import Calibration, Unit


class MeasurementType(Enum):
    """Types of measurements that can be performed."""
    DISTANCE = "distance"
    POLYLINE_LENGTH = "polyline_length"
    POLYGON_AREA = "polygon_area"
    POLYGON_PERIMETER = "polygon_perimeter"
    
    def __repr__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TraceabilityInfo:
    """
    Information needed to trace a measurement back to its source.
    
    This enables users to understand:
    - Which PDF page and geometry produced the measurement
    - How the measurement was calculated
    - What calibration was used
    """
    
    source_page_index: Optional[int] = None
    """Index of the PDF page where the measurement originated."""
    
    source_page_label: Optional[str] = None
    """Label of the PDF page (e.g., 'Sheet 1')."""
    
    source_geometry_ids: Optional[List[str]] = None
    """IDs of the source geometry elements (if available)."""
    
    source_points: Optional[List[Dict[str, float]]] = None
    """Original point coordinates that formed the measurement."""
    
    calculation_method: Optional[str] = None
    """Description of the calculation method used."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_page_index": self.source_page_index,
            "source_page_label": self.source_page_label,
            "source_geometry_ids": self.source_geometry_ids,
            "source_points": self.source_points,
            "calculation_method": self.calculation_method,
        }


@dataclass(frozen=True)
class MeasurementResult:
    """
    A complete measurement result with full traceability.
    
    This preserves all information needed to explain how a measurement
    was produced, including:
    - The raw PDF-space measurement
    - The calibration used
    - The final real-world measurement
    - Source information for verification
    
    Example:
        # After measuring a distance
        result = MeasurementResult(
            measurement_type=MeasurementType.DISTANCE,
            pdf_value=250.0,  # points
            calibration=calibration,  # 20 mm per point
            real_world_value=5000.0,  # mm
            unit=Unit.MILLIMETRES,
            traceability=TraceabilityInfo(
                source_page_index=0,
                source_points=[{"x": 100, "y": 200}, {"x": 350, "y": 200}]
            )
        )
        
        # Access measurements
        assert result.pdf_value == 250.0
        assert result.real_world_value == 5000.0
        assert result.real_world_in_unit == 5000.0  # in mm
        
        # Convert to other units
        assert result.real_world_in(Unit.METRES) == 5.0
    """
    
    measurement_type: MeasurementType
    """The type of measurement that was performed."""
    
    pdf_value: float
    """The raw measurement in PDF points (or points² for areas)."""
    
    calibration: Optional[Calibration]
    """The calibration used for unit conversion (None for uncalibrated measurements)."""
    
    unit: Optional[Unit]
    """The unit of the real-world value (None for uncalibrated measurements)."""
    
    real_world_value: Optional[float]
    """The measurement converted to real-world units (None for uncalibrated measurements)."""
    
    traceability: TraceabilityInfo
    """Information for tracing the measurement back to its source."""
    
    measurement_id: Optional[str] = None
    """Optional unique identifier for the measurement."""
    
    status: str = "valid"
    """Status of the measurement (e.g., 'valid', 'verified', 'estimated', 'uncalibrated')."""
    
    def real_world_in(self, target_unit: Unit) -> Optional[float]:
        """
        Convert the real-world value to a different unit.
        
        Args:
            target_unit: The target unit for conversion
            
        Returns:
            The value converted to the target unit, or None if uncalibrated
            
        Example:
            >>> result = MeasurementResult(...)
            >>> result.real_world_in(Unit.METRES)
            5.0
        """
        if self.unit is None or self.real_world_value is None:
            return None
            
        if target_unit == self.unit:
            return self.real_world_value
        
        # Conversion factors to base unit (millimetres)
        to_mm = {
            Unit.MILLIMETRES: 1.0,
            Unit.CENTIMETRES: 10.0,
            Unit.METRES: 1000.0,
        }
        
        # Convert to base unit, then to target
        base_value = self.real_world_value * to_mm[self.unit]
        return base_value / to_mm[target_unit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        calibration_dict = None
        if self.calibration is not None:
            calibration_dict = {
                "pdf_reference_distance": self.calibration.pdf_reference_distance,
                "real_world_reference_distance": self.calibration.real_world_reference_distance,
                "unit": self.calibration.unit.value,
                "units_per_pdf_point": self.calibration.units_per_pdf_point,
            }
        
        unit_value = None
        if self.unit is not None:
            unit_value = self.unit.value
            
        return {
            "measurement_type": self.measurement_type.value,
            "pdf_value": self.pdf_value,
            "calibration": calibration_dict,
            "unit": unit_value,
            "real_world_value": self.real_world_value,
            "traceability": self.traceability.to_dict(),
            "measurement_id": self.measurement_id,
            "status": self.status,
        }
    
    def __repr__(self) -> str:
        unit_str = "Uncalibrated"
        real_str = "N/A"
        
        if self.unit is not None and self.real_world_value is not None:
            unit_str = self.unit.value
            real_str = f"{self.real_world_value:.2f}"
        
        return (
            f"MeasurementResult("
            f"type={self.measurement_type.value}, "
            f"pdf={self.pdf_value:.2f}pt, "
            f"real={real_str}{unit_str}, "
            f"status={self.status})"
        )