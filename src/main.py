from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QInputDialog
from PySide6.QtCore import Qt

# Import the PDF viewer
from src.modules.viewer import PDFViewer
from src.modules.measurement import Calibration, Unit, UnitSystem, CalibrationTool
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
        
        # PDF Viewer
        self.pdf_viewer = PDFViewer()
        main_layout.addWidget(self.pdf_viewer)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px; background-color: #e0e0e0;")
        main_layout.addWidget(self.status_label)
        
        # Set minimum size
        self.setMinimumSize(800, 600)
    
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


if __name__ == '__main__':
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()
