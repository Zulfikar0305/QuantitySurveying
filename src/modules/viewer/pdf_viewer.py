"""
PDF Viewer widget for PySide6.

This module provides a complete PDF viewer with:
- Page navigation
- Zoom controls
- Pan/scroll
- Fit-to-page
- Coordinate mapping

Architecture:
- PDFRenderer handles rendering to images
- Viewport tracks current view state (zoom, pan)
- CoordinateMapper transforms between page and screen coordinates
- PDFViewer coordinates everything and provides UI interface
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSpinBox, QSlider, QGroupBox, QLineEdit, QFileDialog
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QWheelEvent
import pymupdf

from .viewport import Viewport
from .coordinate_mapper import CoordinateMapper
from .rendering import PDFRenderer, RenderError, InvalidPageError, RenderedImage

from ..pdf_processing.geometry_models import Point


class ViewerError(Exception):
    """Base exception for viewer errors."""
    pass


class ViewerStateError(Exception):
    """Raised when viewer is in an invalid state."""
    pass


class PDFViewer(QWidget):
    """
    PDF Viewer widget with navigation and coordinate mapping.
    
    This widget provides a professional PDF viewing experience:
    - Open and display PDF files
    - Navigate between pages
    - Zoom in/out/reset
    - Fit page to viewport
    - Pan/scroll
    - Map between screen and page coordinates
    
    Example:
        viewer = PDFViewer()
        viewer.open_pdf("plan.pdf")
        
        # Get coordinate mapper for page-to-screen conversion
        mapper = viewer.coordinate_mapper
        screen_point = mapper.page_to_screen((100, 200))
    """
    
    # Signals
    page_changed = Signal(int)
    zoom_changed = Signal(float)
    file_loaded = Signal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._doc: Optional[pymupdf.Document] = None
        self._current_page_index: int = 0
        self._current_pdf_path: Optional[str] = None
        self._renderer = PDFRenderer()
        self._viewport: Optional[Viewport] = None
        self._mapper: Optional[CoordinateMapper] = None
        self._measurement_overlay = None
        self._calibration_tool = None
        self._measurement_session_manager: Optional[MeasurementSessionManager] = None
        
        self._setup_ui()
        self._apply_styles()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Viewer area
        viewer_layout = QHBoxLayout()
        
        # Scroll area for panning
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Image label
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background-color: #f0f0f0;")
        self._image_label.setMinimumSize(100, 100)
        
        self._scroll_area.setWidget(self._image_label)
        viewer_layout.addWidget(self._scroll_area)
        
        # Page info
        page_info_layout = QVBoxLayout()
        page_info_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        page_info_group = QGroupBox("Page Info")
        page_info_group.setLayout(page_info_layout)
        
        self._page_label = QLabel()
        self._page_label.setStyleSheet("font-weight: bold;")
        page_info_layout.addWidget(self._page_label)
        
        self._dimensions_label = QLabel()
        page_info_layout.addWidget(self._dimensions_label)
        
        self._rotation_label = QLabel()
        page_info_layout.addWidget(self._rotation_label)
        
        viewer_layout.addWidget(page_info_group)
        
        main_layout.addLayout(viewer_layout)
        
        # Bottom toolbar
        bottom_toolbar = self._create_bottom_toolbar()
        main_layout.addWidget(bottom_toolbar)
    
    def _create_toolbar(self) -> QWidget:
        """Create the main toolbar."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # File open button
        self._open_button = QPushButton("Open PDF...")
        self._open_button.clicked.connect(self._on_open_file)
        layout.addWidget(self._open_button)
        
        layout.addStretch()
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)
        
        zoom_layout.addWidget(QLabel("Zoom:"))
        
        self._zoom_spinbox = QSpinBox()
        self._zoom_spinbox.setRange(10, 500)
        self._zoom_spinbox.setValue(100)
        self._zoom_spinbox.setSuffix("%")
        self._zoom_spinbox.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self._zoom_spinbox)
        
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 500)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        zoom_layout.addWidget(self._zoom_slider)
        
        # Zoom buttons
        self._zoom_in_button = QPushButton("+")
        self._zoom_in_button.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self._zoom_in_button)
        
        self._zoom_out_button = QPushButton("-")
        self._zoom_out_button.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self._zoom_out_button)
        
        self._zoom_reset_button = QPushButton("Reset")
        self._zoom_reset_button.clicked.connect(self.reset_zoom)
        zoom_layout.addWidget(self._zoom_reset_button)
        
        self._fit_button = QPushButton("Fit Page")
        self._fit_button.clicked.connect(self.fit_to_page)
        zoom_layout.addWidget(self._fit_button)
        
        layout.addLayout(zoom_layout)
        
        return toolbar
    
    def _create_bottom_toolbar(self) -> QWidget:
        """Create the page navigation toolbar."""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Navigation buttons
        self._first_button = QPushButton("|<")
        self._first_button.clicked.connect(self._on_first_page)
        layout.addWidget(self._first_button)
        
        self._prev_button = QPushButton("<")
        self._prev_button.clicked.connect(self._on_prev_page)
        layout.addWidget(self._prev_button)
        
        # Page indicator
        self._page_spinbox = QSpinBox()
        self._page_spinbox.setRange(1, 1)
        self._page_spinbox.setValue(1)
        self._page_spinbox.valueChanged.connect(self._on_page_changed)
        layout.addWidget(self._page_spinbox)
        
        self._total_pages_label = QLabel("/ 1")
        layout.addWidget(self._total_pages_label)
        
        self._next_button = QPushButton(">")
        self._next_button.clicked.connect(self._on_next_page)
        layout.addWidget(self._next_button)
        
        self._last_button = QPushButton(">|")
        self._last_button.clicked.connect(self._on_last_page)
        layout.addWidget(self._last_button)
        
        layout.addStretch()
        
        return toolbar
    
    def _apply_styles(self):
        """Apply stylesheet styles."""
        self.setStyleSheet("""
            PDFViewer {
                background-color: #e0e0e0;
            }
            QPushButton {
                padding: 5px 10px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QSpinBox, QSlider {
                margin: 0 5px;
            }
            QGroupBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
    
    # Properties
    
    @property
    def doc(self) -> Optional[pymupdf.Document]:
        """Get the loaded PDF document."""
        return self._doc
    
    @property
    def current_page_index(self) -> int:
        """Get the current page index (0-based)."""
        return self._current_page_index
    
    @property
    def total_pages(self) -> int:
        """Get the total number of pages."""
        if self._doc is None:
            return 0
        return len(self._doc)
    
    @property
    def viewport(self) -> Optional[Viewport]:
        """Get the current viewport state."""
        return self._viewport
    
    @property
    def coordinate_mapper(self) -> Optional[CoordinateMapper]:
        """Get the coordinate mapper for page-to-screen conversion."""
        return self._mapper
    
    @property
    def is_rotated(self) -> bool:
        """Check if current page is rotated."""
        if self._doc is None or self._current_page_index >= len(self._doc):
            return False
        return self._doc[self._current_page_index].rotation != 0
    
    # Public API
    
    def open_pdf(self, filepath: str) -> None:
        """
        Open a PDF file for viewing.
        
        Args:
            filepath: Path to the PDF file
            
        Raises:
            ViewerError: If file cannot be opened
        """
        try:
            # Close existing document
            if self._doc is not None:
                self._doc.close()
            
            # Open new document
            self._doc = pymupdf.open(filepath)
            
            # Reset state
            self._current_page_index = 0
            self._current_pdf_path = filepath
            
            # Reset calibration when opening new PDF
            self._calibration_tool = None
            
            # Reset measurement session for new document
            if self._measurement_session_manager is not None:
                self._measurement_session_manager.remove_session(self._current_pdf_path)
            
            # Update UI
            self._update_page_controls()
            self._load_page()
            
            # Emit signal
            self.file_loaded.emit(filepath)
            
        except Exception as e:
            raise ViewerError(f"Failed to open PDF: {e}") from e
    
    def close_pdf(self) -> None:
        """Close the current PDF file."""
        if self._doc is not None:
            self._doc.close()
            self._doc = None
            self._current_page_index = 0
            self._current_pdf_path = None
            self._viewport = None
            self._mapper = None
            self._calibration_tool = None
            self._measurement_tool = None
            self._measurement_overlay = None
            self._image_label.clear()
            self._update_page_labels()
    
    def next_page(self) -> None:
        """Navigate to the next page."""
        if self._current_page_index < self.total_pages - 1:
            self.go_to_page(self._current_page_index + 1)
    
    def prev_page(self) -> None:
        """Navigate to the previous page."""
        if self._current_page_index > 0:
            self.go_to_page(self._current_page_index - 1)
    
    def go_to_page(self, page_number: int) -> None:
        """
        Go to a specific page.
        
        Args:
            page_number: Page number (1-based)
        """
        if self._doc is None:
            raise ViewerStateError("No PDF loaded")
        
        index = page_number - 1
        if 0 <= index < self.total_pages:
            self._current_page_index = index
            self._update_page_controls()
            self._load_page()
            self.page_changed.emit(index)
    
    def zoom_in(self) -> None:
        """Zoom in by 20%."""
        if self._viewport is None:
            return
        self._viewport = self._viewport.zoom_in()
        self._apply_viewport()
        self._update_zoom_display()
    
    def zoom_out(self) -> None:
        """Zoom out by 20%."""
        if self._viewport is None:
            return
        self._viewport = self._viewport.zoom_out()
        self._apply_viewport()
        self._update_zoom_display()
    
    def zoom_to(self, zoom: float) -> None:
        """
        Set zoom level.
        
        Args:
            zoom: Zoom factor (e.g., 1.0 = 100%)
        """
        if self._viewport is None:
            return
        self._viewport = self._viewport.zoom_to(zoom)
        self._apply_viewport()
        self._update_zoom_display()
    
    def reset_zoom(self) -> None:
        """Reset zoom to fit page."""
        if self._doc is None or self._viewport is None:
            return
        page = self._doc[self._current_page_index]
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
        
        self._viewport = self._viewport.reset_transform(page_width, page_height)
        self._apply_viewport()
        self._update_zoom_display()
    
    def fit_to_page(self) -> None:
        """Fit the page to the viewport."""
        self.reset_zoom()
    
    def pan(self, dx: float, dy: float) -> None:
        """
        Pan the view.
        
        Args:
            dx: Horizontal pan in pixels
            dy: Vertical pan in pixels
        """
        if self._viewport is None:
            return
        self._viewport = self._viewport.pan(dx, dy)
        self._apply_viewport()
    
    # Private methods
    
    def _load_page(self) -> None:
        """Load and render the current page."""
        if self._doc is None:
            return
        
        try:
            page = self._doc[self._current_page_index]
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            rotation = page.rotation
            
            # Create initial viewport
            viewport = Viewport(
                zoom=1.0,
                offset_x=0.0,
                offset_y=0.0,
                viewport_width=self.width() or 800,
                viewport_height=self.height() or 600,
                rendered_page_width=page_width,
                rendered_page_height=page_height,
                page_rotation=rotation
            )
            
            # Fit to viewport initially
            self._viewport = viewport.fit_to_viewport(page_width, page_height)
            
            # Create coordinate mapper
            self._mapper = CoordinateMapper(
                zoom=self._viewport.zoom,
                offset_x=self._viewport.offset_x,
                offset_y=self._viewport.offset_y,
                page_width=page_width,
                page_height=page_height,
                page_rotation=rotation
            )
            
            # Render the page
            self._render_current_page()
            
            # Update page info labels
            self._update_page_labels()
            
        except Exception as e:
            raise ViewerError(f"Failed to load page {self._current_page_index}: {e}") from e
    
    def _render_current_page(self) -> None:
        """Render the current page to display."""
        if self._doc is None or self._mapper is None:
            return
        
        try:
            page = self._doc[self._current_page_index]
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            
            # Get render size from viewport
            render_width = int(page_width * self._mapper.zoom)
            render_height = int(page_height * self._mapper.zoom)
            
            # Render at appropriate DPI
            # DPI = render_width / page_width * 72
            dpi = render_width / page_width * 72 if render_width > 0 else 150
            # Clamp DPI to valid range
            dpi = max(self._renderer.MIN_DPI, min(dpi, self._renderer.MAX_DPI))
            
            image_data = self._renderer.render_page(
                self._doc,
                self._current_page_index,
                dpi=dpi,
                rotation=page.rotation
            )
            
            # Convert to QPixmap
            from PySide6.QtGui import QImage
            image = QImage.fromData(image_data, 'PNG')
            pixmap = QPixmap.fromImage(image)
            
            self._image_label.setPixmap(pixmap)
            
        except Exception as e:
            raise ViewerError(f"Failed to render page: {e}") from e
    
    def _apply_viewport(self) -> None:
        """Apply the current viewport to the renderer and mapper."""
        if self._doc is None or self._viewport is None:
            return
        
        # Update mapper with current viewport state
        page = self._doc[self._current_page_index]
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
        
        self._mapper = CoordinateMapper(
            zoom=self._viewport.zoom,
            offset_x=self._viewport.offset_x,
            offset_y=self._viewport.offset_y,
            page_width=page_width,
            page_height=page_height,
            page_rotation=self._viewport.page_rotation
        )
        
        # Re-render with new viewport
        self._render_current_page()
        
        # Update zoom display
        self._update_zoom_display()
    
    def _update_zoom_display(self) -> None:
        """Update zoom UI controls to match current state."""
        if self._viewport is None:
            return
        
        zoom_percent = int(self._viewport.zoom * 100)
        self._zoom_spinbox.setValue(zoom_percent)
        self._zoom_slider.setValue(zoom_percent)
        
        self.zoom_changed.emit(self._viewport.zoom)
    
    def _update_page_labels(self) -> None:
        """Update page info labels."""
        if self._doc is None:
            self._page_label.setText("No PDF loaded")
            self._dimensions_label.setText("")
            self._rotation_label.setText("")
            return
        
        page = self._doc[self._current_page_index]
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
        rotation = page.rotation
        
        # Convert points to mm (1 point = 1/72 inch, 1 inch = 25.4 mm)
        width_mm = page_width * 25.4 / 72
        height_mm = page_height * 25.4 / 72
        
        self._page_label.setText(f"Page {self._current_page_index + 1} / {self.total_pages}")
        self._dimensions_label.setText(f"Dimensions: {width_mm:.0f} x {height_mm:.0f} mm")
        self._rotation_label.setText(f"Rotation: {rotation}°")
    
    def _update_page_controls(self) -> None:
        """Update page navigation controls."""
        self._page_spinbox.setValue(self._current_page_index + 1)
        self._page_spinbox.setMaximum(self.total_pages)
        self._total_pages_label.setText(f"/ {self.total_pages}")
        
        # Enable/disable buttons
        self._first_button.setEnabled(self._current_page_index > 0)
        self._prev_button.setEnabled(self._current_page_index > 0)
        self._next_button.setEnabled(self._current_page_index < self.total_pages - 1)
        self._last_button.setEnabled(self._current_page_index < self.total_pages - 1)
    
    # UI Event Handlers
    
    def _on_open_file(self) -> None:
        """Handle open file button click."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF Files (*.pdf);;All Files (*.*)"
        )
        
        if filepath:
            try:
                self.open_pdf(filepath)
            except ViewerError as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", str(e))
    
    def _on_first_page(self) -> None:
        """Go to first page."""
        if self._current_page_index > 0:
            self.go_to_page(1)
    
    def _on_prev_page(self) -> None:
        """Go to previous page."""
        self.prev_page()
    
    def _on_next_page(self) -> None:
        """Go to next page."""
        self.next_page()
    
    def _on_last_page(self) -> None:
        """Go to last page."""
        if self._doc is not None:
            self.go_to_page(self.total_pages)
    
    def _on_page_changed(self, value: int) -> None:
        """Handle page number spinbox change."""
        self.go_to_page(value)
    
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom spinbox change."""
        zoom = value / 100.0
        self.zoom_to(zoom)
    
    def _on_zoom_slider_changed(self, value: int) -> None:
        """Handle zoom slider change."""
        zoom = value / 100.0
        self.zoom_to(zoom)
    
    # Measurement methods
    
    def set_page_geometry(self, page_geometry):
        """Set the page geometry for snapping."""
        self._current_page_geometry = page_geometry
    
    def activate_distance_tool(self):
        """Activate the distance measurement tool."""
        if self._mapper is None or self._doc is None:
            return
        
        # Create measurement engine with optional calibration
        from ..measurement import MeasurementEngine, PolylineTool, AreaTool, PerimeterTool
        from ..measurement.measurement_session import MeasurementSessionManager
        
        # Use active calibration if available
        calibration = self.get_active_calibration()
        
        engine = MeasurementEngine(calibration=calibration)
        
        self._measurement_tool = DistanceTool(
            coordinate_mapper=self._mapper,
            measurement_engine=engine
        )
        
        # Get geometry for snapping
        if self._current_page_geometry:
            vector_elements = self._current_page_geometry.vector_elements
            polyline_elements = self._current_page_geometry.get_polylines()
            self._measurement_tool.set_geometry(vector_elements, polyline_elements)
        
        self._measurement_overlay = MeasurementOverlay(self._mapper)
        
        # Initialize session manager for measurement persistence
        if not hasattr(self, '_measurement_session_manager'):
            self._measurement_session_manager = MeasurementSessionManager()
    
    def activate_polyline_tool(self):
        """Activate the polyline distance measurement tool."""
        if self._mapper is None or self._doc is None:
            return
        
        from ..measurement import MeasurementEngine, PolylineTool
        
        calibration = self.get_active_calibration()
        engine = MeasurementEngine(calibration=calibration)
        
        self._measurement_tool = PolylineTool(
            coordinate_mapper=self._mapper,
            measurement_engine=engine
        )
        
        if self._current_page_geometry:
            vector_elements = self._current_page_geometry.vector_elements
            polyline_elements = self._current_page_geometry.get_polylines()
            self._measurement_tool.set_geometry(vector_elements, polyline_elements)
        
        self._measurement_overlay = MeasurementOverlay(self._mapper)
    
    def activate_area_tool(self):
        """Activate the polygon area measurement tool."""
        if self._mapper is None or self._doc is None:
            return
        
        from ..measurement import MeasurementEngine, AreaTool
        
        calibration = self.get_active_calibration()
        engine = MeasurementEngine(calibration=calibration)
        
        self._measurement_tool = AreaTool(
            coordinate_mapper=self._mapper,
            measurement_engine=engine
        )
        
        if self._current_page_geometry:
            vector_elements = self._current_page_geometry.vector_elements
            polyline_elements = self._current_page_geometry.get_polylines()
            self._measurement_tool.set_geometry(vector_elements, polyline_elements)
        
        self._measurement_overlay = MeasurementOverlay(self._mapper)
    
    def activate_perimeter_tool(self):
        """Activate the polygon perimeter measurement tool."""
        if self._mapper is None or self._doc is None:
            return
        
        from ..measurement import MeasurementEngine, PerimeterTool
        
        calibration = self.get_active_calibration()
        engine = MeasurementEngine(calibration=calibration)
        
        self._measurement_tool = PerimeterTool(
            coordinate_mapper=self._mapper,
            measurement_engine=engine
        )
        
        if self._current_page_geometry:
            vector_elements = self._current_page_geometry.vector_elements
            polyline_elements = self._current_page_geometry.get_polylines()
            self._measurement_tool.set_geometry(vector_elements, polyline_elements)
        
        self._measurement_overlay = MeasurementOverlay(self._mapper)
    
    def deactivate_measurement_tool(self):
        """Deactivate the measurement tool."""
        self._measurement_tool = None
        self._measurement_overlay = None
    
    def is_measurement_active(self) -> bool:
        """Check if measurement tool is active."""
        return self._measurement_tool is not None
    
    def get_measurement_state(self) -> Optional[str]:
        """Get current measurement state."""
        if self._measurement_tool is None:
            return None
        return self._measurement_tool.interaction.state.value
    
    def cancel_measurement(self):
        """Cancel current measurement or calibration."""
        if self._measurement_tool:
            self._measurement_tool.cancel()
        if self._measurement_overlay:
            self._measurement_overlay.clear()
        if self._calibration_tool:
            # Restore previous calibration if cancelled
            previous_calibration = self._calibration_tool.cancel()
            # Don't update measurement engine here - it's done on next activate
            self._calibration_tool = None
    
    def get_measurement_overlays(self):
        """Get the current measurement overlay."""
        return self._measurement_overlay
    
    def get_last_measurement_result(self):
        """Get the last completed measurement result."""
        if self._measurement_tool and self._measurement_tool.interaction.state == MeasurementState.COMPLETED:
            return getattr(self._measurement_tool.interaction, "_last_result", None)
        return None
    
    def complete_current_measurement(self):
        """Complete the current measurement and save to session."""
        if self._measurement_tool is None:
            return None
        
        from ..measurement import MeasurementState
        
        # Try to complete based on tool type
        result = None
        
        # Check if it's a PolylineTool, AreaTool, or PerimeterTool
        from ..measurement.interaction import PolylineTool, AreaTool, PerimeterTool
        
        if isinstance(self._measurement_tool, (PolylineTool, AreaTool, PerimeterTool)):
            # For continuous tools, try to complete
            if hasattr(self._measurement_tool, 'complete'):
                result = self._measurement_tool.complete()
        elif isinstance(self._measurement_tool, DistanceTool):
            # Distance tool completes on second click, check state
            if self._measurement_tool.interaction.state == MeasurementState.COMPLETED:
                # Get the last result from the interaction
                result = getattr(self._measurement_tool.interaction, "_last_result", None)
        
        # Save to session if we have a result
        if result is not None and self._measurement_session_manager is not None:
            session = self._measurement_session_manager.get_session(self._current_pdf_path or "unknown.pdf")
            session.add_measurement(
                result,
                page_index=self._current_page_index or 0,
                page_label=None
            )
        
        # Deactivate tool after completion
        self.deactivate_measurement_tool()
        
        return result
    
    def get_measurement_records(self, page_index: Optional[int] = None):
        """Get measurement records, optionally filtered by page."""
        if self._measurement_session_manager is None:
            return []
        
        session = self._measurement_session_manager.get_session(self._current_pdf_path or "unknown.pdf")
        return session.get_measurements(page_index)
    
    def remove_measurement_record(self, measurement_id: str) -> bool:
        """Remove a measurement record by ID."""
        if self._measurement_session_manager is None:
            return False
        
        session = self._measurement_session_manager.get_session(self._current_pdf_path or "unknown.pdf")
        return session.remove_measurement(measurement_id)
    
    def clear_measurements(self):
        """Clear all measurements for the current document."""
        if self._measurement_session_manager is None:
            return
        
        session = self._measurement_session_manager.get_session(self._current_pdf_path or "unknown.pdf")
        session.clear_all()
    
    # Calibration methods

    def activate_calibration_tool(self):
        """Activate the calibration tool."""
        if self._mapper is None or self._doc is None:
            return

        # Get existing calibration if any
        existing_calibration = None
        if self._calibration_tool:
            existing_calibration = self._calibration_tool.get_calibration()

        # Create calibration tool
        from ..measurement import CalibrationTool
        self._calibration_tool = CalibrationTool(coordinate_mapper=self._mapper)
        self._calibration_tool.activate(previous_calibration=existing_calibration)

    def clear_calibration(self):
        """Clear the active calibration."""
        self._calibration_tool = None

    def is_calibration_active(self) -> bool:
        """Check if calibration tool is active."""
        return self._calibration_tool is not None

    def get_calibration_status_message(self) -> str:
        """Get calibration status message."""
        if self._calibration_tool is None:
            return "No calibration active"
        return self._calibration_tool.get_status_message()

    def get_active_calibration(self):
        """Get the active calibration if available."""
        if self._calibration_tool:
            return self._calibration_tool.get_calibration()
        return None

    # Mouse event handlers
    
    def mousePressEvent(self, event):
        """Handle mouse press events for measurement and calibration."""
        if event.button() == Qt.MouseButton.LeftButton:
            screen_x = event.position().x()
            screen_y = event.position().y()
            
            # Try calibration tool first (it has priority)
            if self._calibration_tool:
                success, message = self._calibration_tool.handle_click(screen_x, screen_y)
                if success:
                    # Trigger repaint to show any overlays
                    self.update()
                return  # Don't process as measurement click
            
            # Then handle measurement tool
            if self._measurement_tool:
                # Get result if measurement completed
                result = self._measurement_tool.handle_click(screen_x, screen_y)
                
                if result:
                    # Store last result for retrieval
                    self._measurement_tool.interaction._last_result = result
                    
                    # Update overlay
                    if self._measurement_overlay:
                        start_point = self._measurement_tool.interaction.start_point
                        # We need to track the end point
                        # For now, just clear and show the completed measurement
                        self._measurement_overlay.clear()
                
                # Trigger repaint to show overlays
                self.update()

        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for hover effects."""
        if self._measurement_tool and self._measurement_tool.interaction.state == MeasurementState.WAITING_FOR_END:
            # Preview mode - store current mouse position for preview line
            pass
        super().mouseMoveEvent(event)
    
    def keyPressEvent(self, event):
        """Handle key press events for canceling measurements."""
        if event.key() == Qt.Key.Key_Escape:
            if self._measurement_tool and self._measurement_tool.interaction.state != MeasurementState.IDLE:
                self.cancel_measurement()
                event.accept()
                return
        super().keyPressEvent(event)
    
        # Coordinate mapping helper methods
    
    def page_to_screen(self, page_x: float, page_y: float) -> Tuple[float, float]:
        """
        Convert page coordinates to screen coordinates.
        
        Args:
            page_x: X coordinate in page space (points)
            page_y: Y coordinate in page space (points)
            
        Returns:
            (screen_x, screen_y) in screen coordinates (pixels)
        """
        if self._mapper is None:
            raise ViewerStateError("No PDF loaded - coordinate mapper not available")
        return self._mapper.page_to_screen((page_x, page_y))
    
    def screen_to_page(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        Convert screen coordinates to page coordinates.
        
        Args:
            screen_x: X coordinate in screen space (pixels)
            screen_y: Y coordinate in screen space (pixels)
            
        Returns:
            (page_x, page_y) in page coordinates (points)
        """
        if self._mapper is None:
            raise ViewerStateError("No PDF loaded - coordinate mapper not available")
        return self._mapper.screen_to_page((screen_x, screen_y))
    
    def page_rect_to_screen(
        self, x0: float, y0: float, x1: float, y1: float
    ) -> Tuple[float, float, float, float]:
        """
        Convert a page rectangle to screen coordinates.
        
        Args:
            x0, y0: Top-left corner in page space
            x1, y1: Bottom-right corner in page space
            
        Returns:
            (x0, y0, x1, y1) in screen coordinates
        """
        if self._mapper is None:
            raise ViewerStateError("No PDF loaded - coordinate mapper not available")
        return self._mapper.page_rect_to_screen(x0, y0, x1, y1)
    
    def screen_rect_to_page(
        self, x0: float, y0: float, x1: float, y1: float
    ) -> Tuple[float, float, float, float]:
        """
        Convert a screen rectangle to page coordinates.
        
        Args:
            x0, y0: Top-left corner in screen space
            x1, y1: Bottom-right corner in screen space
            
        Returns:
            (x0, y0, x1, y1) in page coordinates
        """
        if self._mapper is None:
            raise ViewerStateError("No PDF loaded - coordinate mapper not available")
        return self._mapper.screen_rect_to_page(x0, y0, x1, y1)
    
    def paintEvent(self, event):
        """Paint event handler to draw measurement overlays."""
        super().paintEvent(event)
        
        if not self._measurement_overlay:
            return
        
        # Get screen overlays
        screen_overlays = self._measurement_overlay.get_screen_overlays()
        
        if not screen_overlays:
            return
        
        # Create a painter to draw on the image label
        from PySide6.QtGui import QPainter, QPen, QBrush, QColor
        from PySide6.QtCore import Qt
        
        pixmap = self._image_label.pixmap()
        if pixmap is None:
            return
        
        # Create a copy of the pixmap for drawing
        painter = QPainter(pixmap)
        
        # Draw overlays
        for overlay in screen_overlays:
            if overlay["type"] == "point":
                painter.setPen(QPen(QColor(overlay["color"]), overlay["line_width"]))
                painter.setBrush(QBrush(QColor(overlay["color"]), Qt.BrushStyle.SolidPattern))
                
                radius = overlay["radius"]
                x = overlay["x"] - radius
                y = overlay["y"] - radius
                painter.drawEllipse(int(x), int(y), int(radius * 2), int(radius * 2))
            
            elif overlay["type"] == "line":
                painter.setPen(QPen(QColor(overlay["color"]), overlay["line_width"]))
                painter.drawLine(
                    int(overlay["x1"]), int(overlay["y1"]),
                    int(overlay["x2"]), int(overlay["y2"])
                )
        
        painter.end()
        
        # Update the image label with the modified pixmap
        self._image_label.setPixmap(pixmap)
