"""
Measurement record model for the measurement list/schedule.

This module provides a persistent representation of completed measurements
with full traceability and enough information for auditability.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .measurement_models import MeasurementType, MeasurementResult
from ..pdf_processing.geometry_models import Point


class MeasurementStatus(Enum):
    """Status of a measurement record."""
    VALID = "valid"
    UNCALIBRATED = "uncalibrated"
    CANCELLED = "cancelled"
    DELETED = "deleted"


@dataclass
class MeasurementRecord:
    """
    A complete measurement record for the measurement list.
    
    This preserves all information needed to:
    - Display the measurement in the UI
    - Trace the measurement back to its source
    - Verify or recalculate the measurement
    - Export the measurement for reporting
    """
    
    measurement_id: str
    """Unique identifier for this measurement record."""
    
    measurement_type: MeasurementType
    """The type of measurement that was performed."""
    
    page_index: int
    """Index of the PDF page where the measurement was created."""
    
    page_label: Optional[str]
    """Label of the PDF page (e.g., 'Sheet 1')."""
    
    pdf_file: str
    """Path to the PDF file containing this measurement."""
    
    pdf_points: List[Dict[str, float]]
    """Original PDF-space points that formed the measurement."""
    
    pdf_value: float
    """The raw measurement in PDF points (or points² for areas)."""
    
    calibration_used: Optional[Dict[str, Any]]
    """Calibration information used (None for uncalibrated measurements)."""
    
    real_world_value: Optional[float]
    """The measurement converted to real-world units."""
    
    unit: Optional[str]
    """The unit of the real-world value."""
    
    status: MeasurementStatus = MeasurementStatus.VALID
    """Status of the measurement record."""
    
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    """Timestamp when this record was created."""
    
    calculation_method: Optional[str] = None
    """Description of the calculation method used."""
    
    @property
    def is_calibrated(self) -> bool:
        """Check if this measurement is calibrated."""
        return self.calibration_used is not None
    
    @property
    def formatted_pdf_value(self) -> str:
        """Format PDF value for display."""
        if self.measurement_type == MeasurementType.POLYGON_AREA:
            return f"{self.pdf_value:.2f} sq pt"
        return f"{self.pdf_value:.2f} pt"
    
    @property
    def formatted_real_value(self) -> str:
        """Format real-world value for display."""
        if self.real_world_value is None:
            return "N/A"
        if self.measurement_type == MeasurementType.POLYGON_AREA:
            return f"{self.real_world_value:.2f} {self.unit}²" if self.unit else "N/A"
        return f"{self.real_world_value:.2f} {self.unit}" if self.unit else "N/A"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "measurement_id": self.measurement_id,
            "measurement_type": self.measurement_type.value,
            "page_index": self.page_index,
            "page_label": self.page_label,
            "pdf_file": self.pdf_file,
            "pdf_points": self.pdf_points,
            "pdf_value": self.pdf_value,
            "calibration_used": self.calibration_used,
            "real_world_value": self.real_world_value,
            "unit": self.unit,
            "status": self.status.value,
            "created_at": self.created_at,
            "calculation_method": self.calculation_method,
        }
    
    def __repr__(self) -> str:
        status_str = self.status.value
        type_str = self.measurement_type.value
        
        if self.is_calibrated:
            real_str = f"{self.real_world_value:.2f} {self.unit}"
            return f"Measurement #{self.measurement_id} ({type_str}): {self.pdf_value:.2f} pt → {real_str} [{status_str}]"
        else:
            return f"Measurement #{self.measurement_id} ({type_str}): {self.pdf_value:.2f} pt [uncalibrated, {status_str}]"