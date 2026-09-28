"""
Calibration module for scale and unit handling in measurement calculations.

This module provides explicit scale calibration for converting PDF-space
measurements to real-world dimensions.

Coordinate System:
- PDF coordinates are in points (1/72 inch) with PyMuPDF coordinate system
- Real-world units are explicit and must be specified
- No implicit scale assumptions (e.g., no hardcoded 1:100)
"""

from dataclasses import dataclass
from typing import Union
from enum import Enum
import math


class Unit(Enum):
    """Real-world units for measurements."""
    MILLIMETRES = "mm"
    CENTIMETRES = "cm"
    METRES = "m"
    
    def __repr__(self) -> str:
        return self.value


class UnitSystem(Enum):
    """Unit systems for measurement."""
    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass(frozen=True)
class Calibration:
    """
    Scale calibration for converting PDF measurements to real-world dimensions.
    
    The calibration is established using a known reference measurement:
    - A known distance in the real world (e.g., 5000 mm)
    - The corresponding distance in PDF points
    
    From this, we derive the conversion factor:
    - real_world_units_per_pdf_point = real_world_distance / pdf_distance
    
    Example:
        A drawing has a known dimension of 5000 mm.
        The corresponding PDF geometry distance is 250 points.
        
        calibration = Calibration(
            pdf_reference_distance=250.0,
            real_world_reference_distance=5000.0,
            unit=Unit.MILLIMETRES
        )
        
        # Convert PDF distance to real-world distance
        pdf_distance = 100.0  # points
        real_world = calibration.pdf_to_real_world(pdf_distance)  # 2000.0 mm
    
    Validation:
        - pdf_reference_distance must be > 0
        - real_world_reference_distance must be > 0
        - No division by zero in calculations
    """
    
    pdf_reference_distance: float
    """Distance in PDF points for the reference measurement."""
    
    real_world_reference_distance: float
    """Actual real-world distance corresponding to the PDF reference."""
    
    unit: Unit
    """Unit of the real-world reference distance."""
    
    def __post_init__(self):
        """Validate calibration parameters."""
        if self.pdf_reference_distance <= 0:
            raise ValueError(
                f"PDF reference distance must be positive, got {self.pdf_reference_distance}"
            )
        
        if self.real_world_reference_distance <= 0:
            raise ValueError(
                f"Real-world reference distance must be positive, got {self.real_world_reference_distance}"
            )
        
        if self.unit is None:
            raise ValueError("Unit must be specified")
    
    @property
    def units_per_pdf_point(self) -> float:
        """
        Conversion factor: real-world units per PDF point.
        
        This is the key scaling factor derived from the calibration.
        """
        return self.real_world_reference_distance / self.pdf_reference_distance
    
    @property
    def pdf_points_per_unit(self) -> float:
        """
        Reverse conversion: PDF points per real-world unit.
        
        This allows converting from real-world to PDF measurements.
        """
        return self.pdf_reference_distance / self.real_world_reference_distance
    
    def pdf_to_real_world(self, pdf_distance: float) -> float:
        """
        Convert a PDF distance to real-world distance.
        
        Args:
            pdf_distance: Distance in PDF points
            
        Returns:
            Distance in real-world units
            
        Example:
            >>> cal = Calibration(250.0, 5000.0, Unit.MILLIMETRES)
            >>> cal.pdf_to_real_world(100.0)  # 100 points -> 2000.0 mm
        """
        if pdf_distance < 0:
            raise ValueError(f"PDF distance must be non-negative, got {pdf_distance}")
        
        return pdf_distance * self.units_per_pdf_point
    
    def real_world_to_pdf(self, real_world_distance: float) -> float:
        """
        Convert a real-world distance to PDF distance.
        
        Args:
            real_world_distance: Distance in real-world units
            
        Returns:
            Distance in PDF points
            
        Example:
            >>> cal = Calibration(250.0, 5000.0, Unit.MILLIMETRES)
            >>> cal.real_world_to_pdf(2000.0)  # 2000 mm -> 100 points
        """
        if real_world_distance < 0:
            raise ValueError(
                f"Real-world distance must be non-negative, got {real_world_distance}"
            )
        
        return real_world_distance * self.pdf_points_per_unit
    
    def convert_area(self, pdf_area: float) -> float:
        """
        Convert a PDF area to real-world area.
        
        IMPORTANT: Area conversion uses the SQUARE of the linear factor.
        If linear scale is k (units per point), then area scale is k² (units² per point²).
        
        Args:
            pdf_area: Area in PDF points²
            
        Returns:
            Area in real-world units² (e.g., mm², cm², m²)
            
        Example:
            >>> cal = Calibration(250.0, 5000.0, Unit.MILLIMETRES)
            >>> # Linear factor: 5000/250 = 20 mm per point
            >>> # Area factor: 20² = 400 mm² per point²
            >>> cal.convert_area(100.0)  # 100 points² -> 40000 mm²
        """
        if pdf_area < 0:
            raise ValueError(f"PDF area must be non-negative, got {pdf_area}")
        
        linear_factor = self.units_per_pdf_point
        area_factor = linear_factor * linear_factor
        
        return pdf_area * area_factor
    
    def __repr__(self) -> str:
        units_symbol = self.unit.value
        factor = self.units_per_pdf_point
        return f"Calibration({factor:.4f} {units_symbol}/point)"