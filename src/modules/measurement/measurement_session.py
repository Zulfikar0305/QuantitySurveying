"""
Measurement session for managing in-memory measurement records.

This module provides:
- In-memory storage of completed measurements
- Page and document isolation
- Measurement lifecycle management
- Traceability preservation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import uuid

from .measurement_record import MeasurementRecord, MeasurementStatus
from .measurement_models import MeasurementResult, MeasurementType


@dataclass
class MeasurementSession:
    """
    Manages measurements for a single PDF document session.
    
    This class provides:
    - In-memory storage of completed measurements
    - Page-specific measurement organization
    - Document isolation (measurements are tied to a specific PDF)
    - Unique measurement ID generation
    
    Note: This is for Phase 3 Task 5 only. Persistent storage will be
    implemented in a future phase using SQLite.
    """
    
    pdf_file: str
    """Path to the PDF file being measured."""
    
    page_measurements: Dict[int, List[MeasurementRecord]] = field(default_factory=dict)
    """Measurements organized by page index."""
    
    measurement_counter: int = 0
    """Counter for generating unique measurement IDs."""
    
    def _generate_measurement_id(self) -> str:
        """Generate a unique measurement ID."""
        self.measurement_counter += 1
        return f"{self.measurement_counter:03d}"
    
    def add_measurement(self, result: MeasurementResult, page_index: int, 
                        page_label: Optional[str] = None) -> MeasurementRecord:
        """
        Add a completed measurement to this session.
        
        Args:
            result: The MeasurementResult from the engine/tool
            page_index: Page index where measurement was created
            page_label: Optional page label
            
        Returns:
            The created MeasurementRecord
        """
        measurement_id = self._generate_measurement_id()
        
        # Get original points from traceability info
        pdf_points = []
        if result.traceability.source_points:
            pdf_points = result.traceability.source_points
        
        # Build calibration info dict
        calibration_used = None
        if result.calibration is not None:
            calibration_used = {
                "pdf_reference_distance": result.calibration.pdf_reference_distance,
                "real_world_reference_distance": result.calibration.real_world_reference_distance,
                "unit": result.calibration.unit.value,
            }
        
        record = MeasurementRecord(
            measurement_id=measurement_id,
            measurement_type=result.measurement_type,
            page_index=page_index,
            page_label=page_label,
            pdf_file=self.pdf_file,
            pdf_points=pdf_points,
            pdf_value=result.pdf_value,
            calibration_used=calibration_used,
            real_world_value=result.real_world_value,
            unit=result.unit.value if result.unit else None,
            status=MeasurementStatus(result.status) if result.status in ("valid", "uncalibrated") else MeasurementStatus.VALID,
            calculation_method=result.traceability.calculation_method,
        )
        
        # Add to page's measurement list
        if page_index not in self.page_measurements:
            self.page_measurements[page_index] = []
        self.page_measurements[page_index].append(record)
        
        return record
    
    def get_measurements(self, page_index: Optional[int] = None) -> List[MeasurementRecord]:
        """
        Get measurements, optionally filtered by page.
        
        Args:
            page_index: Optional page index to filter by
            
        Returns:
            List of measurement records
        """
        if page_index is None:
            # Return all measurements across all pages
            all_measurements = []
            for measurements in self.page_measurements.values():
                all_measurements.extend(measurements)
            return all_measurements
        
        return self.page_measurements.get(page_index, [])
    
    def get_measurement_by_id(self, measurement_id: str) -> Optional[MeasurementRecord]:
        """
        Find a measurement by its ID.
        
        Args:
            measurement_id: The measurement ID to find
            
        Returns:
            The MeasurementRecord if found, None otherwise
        """
        for measurements in self.page_measurements.values():
            for record in measurements:
                if record.measurement_id == measurement_id:
                    return record
        return None
    
    def remove_measurement(self, measurement_id: str) -> bool:
        """
        Remove a measurement from the session.
        
        Args:
            measurement_id: ID of the measurement to remove
            
        Returns:
            True if found and removed, False otherwise
        """
        for measurements in self.page_measurements.values():
            for i, record in enumerate(measurements):
                if record.measurement_id == measurement_id:
                    record.status = MeasurementStatus.DELETED
                    del measurements[i]
                    return True
        return False
    
    def clear_page(self, page_index: int) -> None:
        """
        Clear all measurements for a specific page.
        
        Args:
            page_index: Page index to clear
        """
        if page_index in self.page_measurements:
            for record in self.page_measurements[page_index]:
                record.status = MeasurementStatus.DELETED
            del self.page_measurements[page_index]
    
    def clear_all(self) -> None:
        """Clear all measurements from this session."""
        self.page_measurements.clear()
        self.measurement_counter = 0
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of measurements in this session.
        
        Returns:
            Dictionary with measurement counts by type and calibration status
        """
        summaries = {
            "total_count": 0,
            "calibrated_count": 0,
            "uncalibrated_count": 0,
            "by_type": {},
            "by_page": {},
        }
        
        for page_idx, measurements in self.page_measurements.items():
            summaries["total_count"] += len(measurements)
            summaries["by_page"][str(page_idx)] = len(measurements)
            
            for record in measurements:
                if record.is_calibrated:
                    summaries["calibrated_count"] += 1
                else:
                    summaries["uncalibrated_count"] += 1
                
                type_str = record.measurement_type.value
                summaries["by_type"][type_str] = summaries["by_type"].get(type_str, 0) + 1
        
        return summaries


class MeasurementSessionManager:
    """
    Manages multiple measurement sessions (one per PDF file).
    
    This provides document isolation - measurements from one PDF
    are not mixed with measurements from another.
    """
    
    def __init__(self):
        self._sessions: Dict[str, MeasurementSession] = {}
    
    def get_session(self, pdf_file: str) -> MeasurementSession:
        """
        Get or create a session for a PDF file.
        
        Args:
            pdf_file: Path to the PDF file
            
        Returns:
            The MeasurementSession for this file
        """
        if pdf_file not in self._sessions:
            self._sessions[pdf_file] = MeasurementSession(pdf_file=pdf_file)
        return self._sessions[pdf_file]
    
    def remove_session(self, pdf_file: str) -> None:
        """
        Remove a session when a PDF is closed.
        
        Args:
            pdf_file: Path to the PDF file
        """
        if pdf_file in self._sessions:
            del self._sessions[pdf_file]
    
    def clear_all_sessions(self) -> None:
        """Clear all measurement sessions."""
        self._sessions.clear()
    
    def get_active_sessions(self) -> List[str]:
        """Get list of PDF files with active sessions."""
        return list(self._sessions.keys())
