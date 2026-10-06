"""
Calibration UI components for the interactive calibration workflow.

This module provides PySide6 widgets for:
- CalibrationPanel: Status display and controls
- CalibrationDialog: Dialog for entering reference distance
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDialog, QDialogButtonBox, QComboBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal


class CalibrationDialog(QDialog):
    """
    Dialog for entering reference distance during calibration.
    
    Allows user to:
    - Enter the known real-world distance
    - Select the unit (mm, cm, m)
    """
    
    accepted = Signal(float, str)  # distance, unit
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Reference Distance")
        self.setModal(True)
        self.setMinimumWidth(300)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Enter the known real-world distance between the two selected points:")
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(instructions)
        
        # Distance input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Distance:"))
        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("Enter distance")
        self.distance_input.returnPressed.connect(self._on_accepted)
        input_layout.addWidget(self.distance_input)
        layout.addLayout(input_layout)
        
        # Unit selection
        unit_layout = QHBoxLayout()
        unit_layout.addWidget(QLabel("Unit:"))
        self.unit_combo = QComboBox()
        self.unit_combo.addItem("mm", "mm")
        self.unit_combo.addItem("cm", "cm")
        self.unit_combo.addItem("m", "m")
        self.unit_combo.setCurrentIndex(0)  # Default to mm
        unit_layout.addWidget(self.unit_combo)
        layout.addLayout(unit_layout)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accepted)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_accepted(self):
        """Handle OK button click."""
        try:
            distance_str = self.distance_input.text().strip()
            
            if not distance_str:
                self.error_label.setText("Please enter a distance value")
                return
            
            distance = float(distance_str)
            
            if distance <= 0:
                self.error_label.setText("Distance must be positive")
                return
            
            if not self._is_finite(distance):
                self.error_label.setText("Distance must be a finite number")
                return
            
            unit = self.unit_combo.currentData()
            self.accepted.emit(distance, unit)
            self.accept()
            
        except ValueError:
            self.error_label.setText("Invalid number format")
    
    def _is_finite(self, value):
        """Check if value is finite (not NaN or infinity)."""
        import math
        return math.isfinite(value)
    
    def set_error(self, message):
        """Set an error message."""
        self.error_label.setText(message)
    
    def get_distance(self):
        """Get the entered distance."""
        try:
            return float(self.distance_input.text().strip())
        except ValueError:
            return None
    
    def get_unit(self):
        """Get the selected unit."""
        return self.unit_combo.currentData()


class CalibrationPanel(QWidget):
    """
    Panel for displaying calibration status and controls.
    
    Shows:
    - Current calibration status
    - Calibration details when active
    - Clear/reset buttons
    """
    
    calibration_changed = Signal()
    clear_calibration_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Status group
        status_group = QGroupBox("Calibration")
        status_layout = QVBoxLayout(status_group)
        
        # Status label
        self.status_label = QLabel("No calibration active")
        self.status_label.setStyleSheet("color: #666;")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        # Calibration info (hidden when not calibrated)
        info_layout = QHBoxLayout()
        self.calibration_info_label = QLabel()
        self.calibration_info_label.setStyleSheet("color: #006600; font-weight: bold;")
        self.calibration_info_label.hide()
        info_layout.addWidget(self.calibration_info_label)
        status_layout.addLayout(info_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear Calibration")
        self.clear_button.clicked.connect(self._on_clear)
        self.clear_button.setEnabled(False)
        button_layout.addWidget(self.clear_button)
        
        status_layout.addLayout(button_layout)
        
        layout.addWidget(status_group)
    
    def _on_clear(self):
        """Handle clear button click."""
        self.clear_calibration_requested.emit()
    
    def set_status(self, status: str, is_calibrated: bool = False, calibration_text: str = None):
        """Update the calibration status display."""
        self.status_label.setText(status)
        
        if is_calibrated:
            self.status_label.setStyleSheet("color: #006600; font-weight: bold;")
            self.calibration_info_label.setText(calibration_text or "")
            self.calibration_info_label.show()
            self.clear_button.setEnabled(True)
        else:
            self.status_label.setStyleSheet("color: #666;")
            self.calibration_info_label.hide()
            self.clear_button.setEnabled(False)
    
    def clear(self):
        """Clear all calibration info."""
        self.set_status("No calibration active", is_calibrated=False)
