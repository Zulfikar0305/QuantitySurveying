from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QInputDialog, QFrame, QListWidget, QListWidgetItem, QGroupBox, QCheckBox
from PySide6.QtCore import Qt

# Import the PDF viewer
from src.modules.viewer import PDFViewer
from src.modules.measurement import Calibration, Unit, UnitSystem, CalibrationTool, DistanceTool
from src.modules.pdf_processing import PdfProcessor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Quantity Surveying - Phase 3 Task 3')
        self.resize(1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Measurement List Panel and Snapping Controls (horizontal layout)
        tools_layout = QHBoxLayout()
        
        # Measurement List Panel
        measurement_panel = self._create_measurement_panel()
        tools_layout.addWidget(measurement_panel)
        
        # Snapping Controls
        snapping_panel = self._create_snapping_panel()
        tools_layout.addWidget(snapping_panel)
        
        main_layout.addLayout(tools_layout)
        
        # PDF Viewer
        self.pdf_viewer = PDFViewer()
        main_layout.addWidget(self.pdf_viewer)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px; background-color: #e0e0e0;")
        main_layout.addWidget(self.status_label)
        
        # Set minimum size
        self.setMinimumSize(800, 600)
    

    def _create_measurement_panel(self):
        """Create the measurement list panel."""
        panel = QWidget()
        panel.setWindowTitle("Measurements")
        panel.setMaximumWidth(250)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        label = QLabel("Completed Measurements")
        label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(label)
        
        # List widget for measurements
        self.measurement_list = QListWidget()
        self.measurement_list.itemSelectionChanged.connect(self._on_measurement_selected)
        layout.addWidget(self.measurement_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.remove_measurement_button = QPushButton("Remove")
        self.remove_measurement_button.clicked.connect(self._on_remove_measurement)
        self.remove_measurement_button.setEnabled(False)
        button_layout.addWidget(self.remove_measurement_button)
        
        self.clear_measurements_button = QPushButton("Clear All")
        self.clear_measurements_button.clicked.connect(self._on_clear_measurements)
        button_layout.addWidget(self.clear_measurements_button)
        
        layout.addLayout(button_layout)
        
        return panel

    def _create_snapping_panel(self):
        """Create the snapping controls panel."""
        panel = QWidget()
        panel.setWindowTitle("Snapping")
        panel.setMaximumWidth(200)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        label = QLabel("Snapping")
        label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(label)
        
        # Snap type checkboxes
        self.snap_endpoint_check = QCheckBox("Endpoint")
        self.snap_endpoint_check.setChecked(True)
        self.snap_endpoint_check.stateChanged.connect(self._on_snap_setting_changed)
        layout.addWidget(self.snap_endpoint_check)
        
        self.snap_vertex_check = QCheckBox("Vertex")
        self.snap_vertex_check.setChecked(True)
        self.snap_vertex_check.stateChanged.connect(self._on_snap_setting_changed)
        layout.addWidget(self.snap_vertex_check)
        
        self.snap_intersection_check = QCheckBox("Intersection")
        self.snap_intersection_check.setChecked(True)
        self.snap_intersection_check.stateChanged.connect(self._on_snap_setting_changed)
        layout.addWidget(self.snap_intersection_check)
        
        self.snap_midpoint_check = QCheckBox("Midpoint")
        self.snap_midpoint_check.setChecked(True)
        self.snap_midpoint_check.stateChanged.connect(self._on_snap_setting_changed)
        layout.addWidget(self.snap_midpoint_check)
        
        self.snap_nearest_check = QCheckBox("Nearest Point")
        self.snap_nearest_check.setChecked(True)
        self.snap_nearest_check.stateChanged.connect(self._on_snap_setting_changed)
        layout.addWidget(self.snap_nearest_check)
        
        return panel
    def _create_toolbar(self):
        """Create the main toolbar with measurement tools."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # File button
        self.open_button = QPushButton("Open PDF...")
        self.open_button.clicked.connect(self._on_open_file)
        layout.addWidget(self.open_button)
        
        layout.addStretch()
        
        # Measurement tools
        layout.addWidget(QLabel("Measurements:"))
        
        self.distance_button = QPushButton("Distance")
        self.distance_button.clicked.connect(self._on_activate_distance)
        self.distance_button.setStyleSheet("background-color: #4CAF50; color: white;")
        layout.addWidget(self.distance_button)
        
        self.polyline_button = QPushButton("Polyline")
        self.polyline_button.clicked.connect(self._on_activate_polyline)
        self.polyline_button.setStyleSheet("background-color: #2196F3; color: white;")
        layout.addWidget(self.polyline_button)
        
        self.area_button = QPushButton("Area")
        self.area_button.clicked.connect(self._on_activate_area)
        self.area_button.setStyleSheet("background-color: #FF9800; color: white;")
        layout.addWidget(self.area_button)
        
        self.perimeter_button = QPushButton("Perimeter")
        self.perimeter_button.clicked.connect(self._on_activate_perimeter)
        self.perimeter_button.setStyleSheet("background-color: #9C27B0; color: white;")
        layout.addWidget(self.perimeter_button)
        
        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.clicked.connect(self._on_calibrate)
        self.calibrate_button.setStyleSheet("background-color: #2196F3; color: white;")
        layout.addWidget(self.calibrate_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_measurement)
        self.cancel_button.setEnabled(False)
        layout.addWidget(self.cancel_button)
        
        layout.addStretch()
        
        return toolbar
    

    def _on_measurement_selected(self):
        """Handle measurement selection."""
        selected = self.measurement_list.currentItem()
        if selected:
            measurement_id = selected.data(Qt.UserRole)
            self.pdf_viewer.select_measurement(measurement_id)
    
    def _on_remove_measurement(self):
        """Remove selected measurement."""
        selected = self.measurement_list.currentItem()
        if selected:
            measurement_id = selected.data(Qt.UserRole)
            self.pdf_viewer.remove_measurement(measurement_id)
            row = self.measurement_list.currentRow()
            self.measurement_list.takeItem(row)
            self.remove_measurement_button.setEnabled(False)
    
    def _on_clear_measurements(self):
        """Clear all measurements."""
        self.pdf_viewer.clear_measurements()
        self.measurement_list.clear()
    
    def _on_snap_setting_changed(self):
        """Handle snapping setting changes."""
        self.pdf_viewer.update_snap_settings(
            endpoint=self.snap_endpoint_check.isChecked(),
            vertex=self.snap_vertex_check.isChecked(),
            intersection=self.snap_intersection_check.isChecked(),
            midpoint=self.snap_midpoint_check.isChecked(),
            nearest=self.snap_nearest_check.isChecked()
        )
    def _on_open_file(self):
        """Handle open file button click."""
        from PySide6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF Files (*.pdf);;All Files (*.*)"
        )
        
        if filepath:
            try:
                self.pdf_viewer.open_pdf(filepath)
                
                # Load page geometry for snapping
                processor = PdfProcessor()
                doc = processor.process_file(filepath)
                page_geom = doc.get_page(0)
                self.pdf_viewer.set_page_geometry(page_geom)
                
                self.status_label.setText(f"Loaded: {filepath} - Page {self.pdf_viewer.current_page_index + 1}")
                
                # Initialize measurement session manager if needed
                if hasattr(self.pdf_viewer, '_measurement_session_manager') and self.pdf_viewer._measurement_session_manager is None:
                    from src.modules.measurement import MeasurementSessionManager
                    self.pdf_viewer._measurement_session_manager = MeasurementSessionManager()
                    
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to open PDF: {e}")
    
    def _on_activate_distance(self):
        """Activate distance measurement tool."""
        if not self.pdf_viewer.doc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Document", "Please open a PDF first")
            return
        
        self.pdf_viewer.activate_distance_tool()
        self.distance_button.setStyleSheet("background-color: #45a049; color: white;")
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Distance tool active - Click two points to measure")
    
    def _on_cancel_measurement(self):
        """Cancel current measurement or calibration."""
        self.pdf_viewer.cancel_measurement()
        self.distance_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.calibrate_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Measurement cancelled")
    
    def _on_calibrate(self):
        """Activate calibration tool."""
        if not self.pdf_viewer.doc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Document", "Please open a PDF first")
            return
        
        self.pdf_viewer.activate_calibration_tool()
        self.calibrate_button.setStyleSheet("background-color: #1976D2; color: white;")
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Calibration tool active - Click two reference points")
    
    def _on_activate_polyline(self):
        """Activate polyline distance measurement tool."""
        if not self.pdf_viewer.doc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Document", "Please open a PDF first")
            return
        
        self.pdf_viewer.activate_polyline_tool()
        self.distance_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.polyline_button.setStyleSheet("background-color: #1976D2; color: white;")
        self.area_button.setStyleSheet("background-color: #FF9800; color: white;")
        self.perimeter_button.setStyleSheet("background-color: #9C27B0; color: white;")
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Polyline tool active - Click multiple points to measure continuous distance")
    
    def _on_activate_area(self):
        """Activate area measurement tool."""
        if not self.pdf_viewer.doc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Document", "Please open a PDF first")
            return
        
        self.pdf_viewer.activate_area_tool()
        self.distance_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.polyline_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.area_button.setStyleSheet("background-color: #F57C00; color: white;")
        self.perimeter_button.setStyleSheet("background-color: #9C27B0; color: white;")
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Area tool active - Click polygon vertices (click first point to close)")
    
    def _on_activate_perimeter(self):
        """Activate perimeter measurement tool."""
        if not self.pdf_viewer.doc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Document", "Please open a PDF first")
            return
        
        self.pdf_viewer.activate_perimeter_tool()
        self.distance_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.polyline_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.area_button.setStyleSheet("background-color: #FF9800; color: white;")
        self.perimeter_button.setStyleSheet("background-color: #7B1FA2; color: white;")
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Perimeter tool active - Click polygon vertices (click first point to close)")


if __name__ == '__main__':
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()
