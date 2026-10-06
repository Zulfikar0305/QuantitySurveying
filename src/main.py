from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from src.modules.export import MeasurementExporter
from src.modules.measurement import CalibrationPanel, MeasurementRecord, MeasurementSessionManager
from src.modules.pdf_processing import PdfProcessor
from src.modules.project import ProjectDatabase, ProjectDrawing, ProjectManager, ProjectState, TakeoffItem
from src.modules.viewer import PDFViewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantity Surveying")
        self.resize(1500, 920)
        self.setMinimumSize(1100, 700)

        self.session_manager = MeasurementSessionManager()
        self.project_db = ProjectDatabase()
        self.project_manager = ProjectManager(self.project_db)
        self.project_id = self.project_manager.create_new("Untitled Project")

        self.pdf_viewer = PDFViewer()
        self.pdf_viewer.set_measurement_session_manager(self.session_manager)
        self.pdf_viewer.measurement_changed.connect(self._refresh_measurements)

        self._build_toolbar()
        self._build_workspace()
        self._setup_status_bar()
        self._refresh_measurements()

    def _build_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.new_project_button = QPushButton("New Project")
        self.new_project_button.clicked.connect(self._on_new_project)
        toolbar.addWidget(self.new_project_button)

        self.open_project_button = QPushButton("Open Project")
        self.open_project_button.clicked.connect(self._on_open_project)
        toolbar.addWidget(self.open_project_button)

        self.save_project_button = QPushButton("Save Project")
        self.save_project_button.clicked.connect(self._on_save_project)
        toolbar.addWidget(self.save_project_button)

        self.save_as_button = QPushButton("Save As")
        self.save_as_button.clicked.connect(self._on_save_as)
        toolbar.addWidget(self.save_as_button)

        self.close_project_button = QPushButton("Close Project")
        self.close_project_button.clicked.connect(self._on_close_project)
        toolbar.addWidget(self.close_project_button)

        toolbar.addSeparator()

        self.open_pdf_button = QPushButton("Open PDF")
        self.open_pdf_button.clicked.connect(self._on_open_file)
        toolbar.addWidget(self.open_pdf_button)

        toolbar.addSeparator()

        self.distance_button = QPushButton("Distance")
        self.distance_button.clicked.connect(self._on_activate_distance)
        toolbar.addWidget(self.distance_button)

        self.polyline_button = QPushButton("Polyline")
        self.polyline_button.clicked.connect(self._on_activate_polyline)
        toolbar.addWidget(self.polyline_button)

        self.area_button = QPushButton("Area")
        self.area_button.clicked.connect(self._on_activate_area)
        toolbar.addWidget(self.area_button)

        self.perimeter_button = QPushButton("Perimeter")
        self.perimeter_button.clicked.connect(self._on_activate_perimeter)
        toolbar.addWidget(self.perimeter_button)

        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.clicked.connect(self._on_calibrate)
        toolbar.addWidget(self.calibrate_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel_measurement)
        self.cancel_button.setEnabled(False)
        toolbar.addWidget(self.cancel_button)

        toolbar.addSeparator()

        self.fit_button = QPushButton("Fit Page")
        self.fit_button.clicked.connect(self.pdf_viewer.fit_to_page)
        toolbar.addWidget(self.fit_button)

        self.zoom_in_button = QPushButton("Zoom +")
        self.zoom_in_button.clicked.connect(self.pdf_viewer.zoom_in)
        toolbar.addWidget(self.zoom_in_button)

        self.zoom_out_button = QPushButton("Zoom -")
        self.zoom_out_button.clicked.connect(self.pdf_viewer.zoom_out)
        toolbar.addWidget(self.zoom_out_button)

    def _build_workspace(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        left_panel = self._create_tool_panel()
        right_panel = self._create_measurement_panel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.pdf_viewer)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([220, 900, 360])

        root_layout.addWidget(splitter)

    def _create_tool_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(180)
        panel.setMaximumWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        project_group = QGroupBox("Project")
        project_layout = QVBoxLayout(project_group)

        self.project_name_label = QLabel("Project: Untitled")
        self.project_name_label.setWordWrap(True)
        self.project_name_label.setStyleSheet("font-weight: bold;")
        project_layout.addWidget(self.project_name_label)

        self.drawing_name_label = QLabel("Drawing: none")
        self.drawing_name_label.setWordWrap(True)
        project_layout.addWidget(self.drawing_name_label)

        self.page_status_label = QLabel("Page: none")
        self.page_status_label.setWordWrap(True)
        project_layout.addWidget(self.page_status_label)

        self.snap_status_label = QLabel("Snapping: endpoint / vertex / midpoint")
        self.snap_status_label.setWordWrap(True)
        project_layout.addWidget(self.snap_status_label)

        layout.addWidget(project_group)

        tools_group = QGroupBox("Tools")
        tools_layout = QVBoxLayout(tools_group)
        tools_layout.setSpacing(6)

        self.tool_buttons = {
            "distance": QPushButton("Distance"),
            "polyline": QPushButton("Polyline"),
            "area": QPushButton("Area"),
            "perimeter": QPushButton("Perimeter"),
            "calibrate": QPushButton("Calibrate"),
        }

        for name, button in self.tool_buttons.items():
            button.clicked.connect(getattr(self, f"_on_activate_{name}"))
            tools_layout.addWidget(button)

        layout.addWidget(tools_group)

        snapping_group = QGroupBox("Snapping")
        snapping_layout = QVBoxLayout(snapping_group)

        self.snap_endpoint_check = QCheckBox("Endpoint")
        self.snap_endpoint_check.setChecked(True)
        self.snap_vertex_check = QCheckBox("Vertex")
        self.snap_vertex_check.setChecked(True)
        self.snap_intersection_check = QCheckBox("Intersection")
        self.snap_intersection_check.setChecked(True)
        self.snap_midpoint_check = QCheckBox("Midpoint")
        self.snap_midpoint_check.setChecked(True)
        self.snap_nearest_check = QCheckBox("Nearest point")
        self.snap_nearest_check.setChecked(True)

        for checkbox in (
            self.snap_endpoint_check,
            self.snap_vertex_check,
            self.snap_intersection_check,
            self.snap_midpoint_check,
            self.snap_nearest_check,
        ):
            checkbox.stateChanged.connect(self._on_snap_setting_changed)
            snapping_layout.addWidget(checkbox)

        layout.addWidget(snapping_group)

        self.calibration_panel = CalibrationPanel()
        self.calibration_panel.clear_calibration_requested.connect(self._on_clear_calibration)
        layout.addWidget(self.calibration_panel)

        view_group = QGroupBox("View")
        view_layout = QVBoxLayout(view_group)
        self.page_info_label = QLabel("No PDF loaded")
        self.page_info_label.setWordWrap(True)
        view_layout.addWidget(self.page_info_label)

        self.project_status_label = QLabel(f"Project: {self.project_id[:8]}")
        self.project_status_label.setWordWrap(True)
        view_layout.addWidget(self.project_status_label)
        layout.addWidget(view_group)

        layout.addStretch()
        return panel

    def _create_measurement_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel.setMaximumWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        measurement_header = QLabel("Measurements")
        measurement_header.setStyleSheet("font-weight: bold;")
        layout.addWidget(measurement_header)

        self.measurement_list = QListWidget()
        self.measurement_list.itemSelectionChanged.connect(self._on_measurement_selected)
        layout.addWidget(self.measurement_list)

        buttons = QHBoxLayout()
        self.add_to_takeoff_button = QPushButton("Add to Takeoff")
        self.add_to_takeoff_button.clicked.connect(self._on_add_selected_measurement_to_takeoff)
        self.add_to_takeoff_button.setEnabled(False)
        buttons.addWidget(self.add_to_takeoff_button)

        self.remove_measurement_button = QPushButton("Remove")
        self.remove_measurement_button.clicked.connect(self._on_remove_measurement)
        self.remove_measurement_button.setEnabled(False)
        buttons.addWidget(self.remove_measurement_button)

        self.clear_measurements_button = QPushButton("Clear")
        self.clear_measurements_button.clicked.connect(self._on_clear_measurements)
        buttons.addWidget(self.clear_measurements_button)

        layout.addLayout(buttons)

        takeoff_header = QLabel("Takeoff")
        takeoff_header.setStyleSheet("font-weight: bold;")
        layout.addWidget(takeoff_header)

        self.takeoff_list = QListWidget()
        self.takeoff_list.itemSelectionChanged.connect(self._on_takeoff_selected)
        layout.addWidget(self.takeoff_list)

        return panel

    def _setup_status_bar(self):
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("QStatusBar { background: #f5f5f5; }")

    def _on_new_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name", text="Untitled Project")
        if not ok:
            return
        self.session_manager.clear_all_sessions()
        self.pdf_viewer.close_pdf()
        self.project_id = self.project_manager.create_new(name.strip() or "Untitled Project")
        self._update_project_labels()
        self._refresh_measurements()
        self.statusBar().showMessage(f"Created project: {self.project_manager.state.name}")

    def _on_open_project(self):
        projects = self.project_db.list_projects()
        if not projects:
            QMessageBox.information(self, "Open Project", "No saved projects found.")
            return
        choices = [f"{project['name']} ({project['id'][:8]})" for project in projects]
        selection, ok = QInputDialog.getItem(self, "Open Project", "Select project", choices, 0, False)
        if not ok or not selection:
            return
        project_id = next(item["id"] for item in projects if f"{item['name']} ({item['id'][:8]})" == selection)
        self._load_project(project_id)

    def _load_project(self, project_id: str):
        state = self.project_db.get_project(project_id)
        if state is None:
            QMessageBox.critical(self, "Project Load", "Unable to load the selected project.")
            return

        self.project_id = project_id
        self.project_manager.project_id = project_id
        self.project_manager.state = state
        self.session_manager.clear_all_sessions()
        self.pdf_viewer.close_pdf()

        for measurement in self.project_db.load_measurements(project_id):
            try:
                record = MeasurementRecord.from_dict(measurement)
            except Exception:
                continue
            if not record.pdf_file:
                continue
            session = self.session_manager.get_session(record.pdf_file)
            session.page_measurements.setdefault(record.page_index, []).append(record)
            if record.measurement_id.isdigit():
                try:
                    session.measurement_counter = max(session.measurement_counter, int(record.measurement_id))
                except ValueError:
                    pass

        active_pdf = state.active_pdf or (state.drawings[0].pdf_path if state.drawings else None)
        if active_pdf and Path(active_pdf).exists():
            try:
                self.pdf_viewer.open_pdf(active_pdf)
                self._load_pdf_geometry(active_pdf)
                self.statusBar().showMessage(f"Opened project: {state.name}")
            except Exception as exc:  # pragma: no cover - UI feedback path
                QMessageBox.warning(self, "Project Load", f"Project reopened, but the drawing could not be opened: {exc}")
        self._update_project_labels()
        self._refresh_measurements()

    def _on_save_project(self):
        if self.project_id is None:
            return
        self.project_manager.state = self.project_db.get_project(self.project_id) or self.project_manager.state
        if self.project_manager.state is not None:
            self.project_manager.state.name = self.project_name_label.text().replace("Project: ", "") or "Untitled Project"
            self.project_manager.state.active_pdf = self.pdf_viewer._current_pdf_path
            self.project_manager.save()
        if self.pdf_viewer._current_pdf_path:
            self.project_db.update_project_pdf(self.project_id, self.pdf_viewer._current_pdf_path)
            session = self.pdf_viewer._measurement_session_manager.get_session(self.pdf_viewer._current_pdf_path)
            self.project_db.save_session_measurements(self.project_id, session.get_measurements(), self.pdf_viewer._current_pdf_path)
        self.statusBar().showMessage("Project saved locally")

    def _on_save_as(self):
        project_name, ok = QInputDialog.getText(self, "Save As", "Project name", text=self.project_manager.state.name if self.project_manager.state else "Untitled Project")
        if not ok:
            return
        new_id = self.project_db.create_project(project_name.strip() or "Untitled Project")
        state = self.project_db.get_project(new_id)
        if state is None:
            return
        if self.project_manager.state:
            state.name = project_name.strip() or self.project_manager.state.name
            state.description = self.project_manager.state.description
            state.drawings = list(self.project_manager.state.drawings)
            state.takeoff_items = list(self.project_manager.state.takeoff_items)
            state.calibration = self.project_manager.state.calibration
            state.active_pdf = self.project_manager.state.active_pdf
            self.project_db.save_project_state(new_id, state)
        self.project_id = new_id
        self.project_manager.project_id = new_id
        self.project_manager.state = state
        self._update_project_labels()
        self.statusBar().showMessage(f"Saved copy as: {state.name}")

    def _on_close_project(self):
        self.project_manager.close()
        self.project_id = None
        self.session_manager.clear_all_sessions()
        self.pdf_viewer.close_pdf()
        self.project_name_label.setText("Project: none")
        self.drawing_name_label.setText("Drawing: none")
        self.page_status_label.setText("Page: none")
        self._refresh_measurements()
        self.statusBar().showMessage("Project closed")

    def _update_project_labels(self):
        state = self.project_manager.state
        project_name = state.name if state else "Untitled Project"
        self.project_name_label.setText(f"Project: {project_name}")
        self.project_status_label.setText(f"Project: {project_name[:8]}")

        active_drawing = self.project_manager.get_active_drawing() if state else None
        if active_drawing:
            self.drawing_name_label.setText(f"Drawing: {active_drawing.name}")
        else:
            self.drawing_name_label.setText("Drawing: none")

        if self.pdf_viewer.doc is not None:
            self.page_status_label.setText(f"Page: {self.pdf_viewer.current_page_index + 1} / {self.pdf_viewer.total_pages}")
        else:
            self.page_status_label.setText("Page: none")

        self._update_calibration_status()

    def _on_measurement_selected(self):
        selected = self.measurement_list.currentItem()
        if selected is None:
            return
        measurement_id = selected.data(Qt.ItemDataRole.UserRole)
        self.pdf_viewer.select_measurement(measurement_id)
        self.add_to_takeoff_button.setEnabled(True)

    def _on_remove_measurement(self):
        selected = self.measurement_list.currentItem()
        if selected is None:
            return
        measurement_id = selected.data(Qt.ItemDataRole.UserRole)
        self.pdf_viewer.remove_measurement(measurement_id)
        self._refresh_measurements()

    def _on_clear_measurements(self):
        self.pdf_viewer.clear_measurements()
        self._refresh_measurements()

    def _on_snap_setting_changed(self):
        self.pdf_viewer.update_snap_settings(
            endpoint=self.snap_endpoint_check.isChecked(),
            vertex=self.snap_vertex_check.isChecked(),
            intersection=self.snap_intersection_check.isChecked(),
            midpoint=self.snap_midpoint_check.isChecked(),
            nearest=self.snap_nearest_check.isChecked(),
        )
        self.snap_status_label.setText(
            "Snapping: "
            + ", ".join(
                name for name, checkbox in {
                    "endpoint": self.snap_endpoint_check,
                    "vertex": self.snap_vertex_check,
                    "intersection": self.snap_intersection_check,
                    "midpoint": self.snap_midpoint_check,
                    "nearest": self.snap_nearest_check,
                }.items() if checkbox.isChecked()
            )
            or "off"
        )

    def _on_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF Files (*.pdf);;All Files (*.*)",
        )
        if not filepath:
            return

        try:
            self.pdf_viewer.open_pdf(filepath)
            self._load_pdf_geometry(filepath)
            self.project_manager.set_active_pdf(filepath)

            active_drawing = self.project_manager.get_active_drawing()
            if active_drawing is None or active_drawing.pdf_path != filepath:
                self.project_manager.add_drawing(filepath, name=Path(filepath).stem)
            self._update_project_labels()
            self._refresh_measurements()
            self.statusBar().showMessage(f"Loaded drawing: {filepath}")
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {exc}")

    def _load_pdf_geometry(self, filepath: str):
        try:
            processor = PdfProcessor()
            page_geometry = processor.process_file(filepath).get_page(0)
            self.pdf_viewer.set_page_geometry(page_geometry)
        except Exception as exc:  # pragma: no cover - UI feedback path
            self.statusBar().showMessage(f"Geometry warning: {exc}")

    def _on_export_csv(self):
        target, _ = QFileDialog.getSaveFileName(self, "Export measurements", "measurements.csv", "CSV Files (*.csv)")
        if not target:
            return
        session = self.pdf_viewer._measurement_session_manager.get_session(self.pdf_viewer._current_pdf_path or "unknown.pdf")
        measurements = session.get_measurements()
        export_path = MeasurementExporter.export_csv(measurements, target)
        self.statusBar().showMessage(f"Exported to {export_path}")

    def _on_takeoff_selected(self):
        selected = self.takeoff_list.currentItem()
        if selected is None:
            return
        item = selected.data(Qt.ItemDataRole.UserRole)
        if not isinstance(item, dict):
            return
        page_index = int(item.get("page_index", 0) or 0)
        drawing = item.get("drawing") or ""
        if self.pdf_viewer._current_pdf_path and drawing in (Path(self.pdf_viewer._current_pdf_path).stem, drawing):
            self.pdf_viewer.go_to_page(page_index + 1)
            self.statusBar().showMessage(f"Navigated to {drawing} / page {page_index + 1}")
        else:
            self.statusBar().showMessage(f"Takeoff item: {item.get('description', '')} (page {page_index + 1})")

    def _on_add_selected_measurement_to_takeoff(self):
        selected = self.measurement_list.currentItem()
        if selected is None:
            return
        measurement_id = selected.data(Qt.ItemDataRole.UserRole)
        session = self.session_manager.get_session(self.pdf_viewer._current_pdf_path or "unknown.pdf")
        record = next((item for item in session.get_measurements() if item.measurement_id == measurement_id), None)
        if record is None:
            QMessageBox.warning(self, "Takeoff", "Selected measurement could not be found in the current session.")
            return

        code, ok_code = QInputDialog.getText(self, "Takeoff Item", "Code:", text=f"ITEM-{len(self.project_manager.state.takeoff_items) + 1:03d}")
        if not ok_code:
            return
        description, ok_desc = QInputDialog.getText(self, "Takeoff Item", "Description:", text=record.measurement_type.value.replace("_", " ").title())
        if not ok_desc:
            return

        active_drawing = self.project_manager.get_active_drawing() or ProjectDrawing(
            drawing_id="drawing-001",
            name=Path(self.pdf_viewer._current_pdf_path).stem if self.pdf_viewer._current_pdf_path else "Drawing",
            pdf_path=self.pdf_viewer._current_pdf_path or "",
            page_index=record.page_index,
            active=True,
        )

        item = self.project_manager.add_takeoff_item(
            record,
            code=(code or f"ITEM-{len(self.project_manager.state.takeoff_items) + 1:03d}"),
            description=description or "Takeoff item",
            quantity=record.real_world_value if record.real_world_value is not None else record.pdf_value,
            unit=record.unit or "m",
            drawing=active_drawing.name,
            page_index=record.page_index,
            notes=f"Source: Measurement #{record.measurement_id}",
            category="general",
        )
        if item is not None:
            self._refresh_takeoff_list()
            self.statusBar().showMessage(f"Added takeoff item: {item.code}")

    def _refresh_takeoff_list(self):
        self.takeoff_list.clear()
        state = self.project_manager.state
        if state is None:
            return
        for item in state.takeoff_items:
            entry = QListWidgetItem(f"{item.code} | {item.description} | {item.quantity:.2f} {item.unit} | {item.drawing}")
            entry.setData(Qt.ItemDataRole.UserRole, item.to_dict())
            self.takeoff_list.addItem(entry)

    def _refresh_measurements(self):
        self.measurement_list.clear()
        self.add_to_takeoff_button.setEnabled(False)
        if self.pdf_viewer._measurement_session_manager is None:
            self._update_project_labels()
            return

        session = self.pdf_viewer._measurement_session_manager.get_session(self.pdf_viewer._current_pdf_path or "unknown.pdf")
        measurements = session.get_measurements()
        for record in measurements:
            item = QListWidgetItem(f"#{record.measurement_id} | {record.measurement_type.value} | {record.formatted_real_value if record.real_world_value is not None else record.formatted_pdf_value}")
            item.setData(Qt.ItemDataRole.UserRole, record.measurement_id)
            self.measurement_list.addItem(item)

        if self.project_id:
            self.project_db.save_session_measurements(self.project_id, measurements, self.pdf_viewer._current_pdf_path)

        self.remove_measurement_button.setEnabled(self.measurement_list.count() > 0)
        self.clear_measurements_button.setEnabled(self.measurement_list.count() > 0)

        if self.pdf_viewer.doc is not None:
            page_info = f"Page {self.pdf_viewer.current_page_index + 1} / {self.pdf_viewer.total_pages}"
            self.page_info_label.setText(page_info)
            self.project_status_label.setText(f"Project: {self.project_manager.state.name[:8] if self.project_manager.state else 'project'}\nActive PDF: {self.pdf_viewer._current_pdf_path}")
        else:
            self.page_info_label.setText("No PDF loaded")

        self._update_project_labels()
        self._refresh_takeoff_list()

    def _set_active_tool(self, tool_name: str):
        for name, button in self.tool_buttons.items():
            button.setStyleSheet(
                "background-color: #e6e6e6; color: #202124;"
                if name == tool_name
                else "background-color: #f2f2f2; color: #202124;"
            )

    def _on_activate_distance(self):
        if not self.pdf_viewer.doc:
            QMessageBox.warning(self, "No document", "Please open a PDF first.")
            return
        self.pdf_viewer.activate_distance_tool()
        self._set_active_tool("distance")
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Distance tool active")

    def _on_activate_polyline(self):
        if not self.pdf_viewer.doc:
            QMessageBox.warning(self, "No document", "Please open a PDF first.")
            return
        self.pdf_viewer.activate_polyline_tool()
        self._set_active_tool("polyline")
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Polyline tool active")

    def _on_activate_area(self):
        if not self.pdf_viewer.doc:
            QMessageBox.warning(self, "No document", "Please open a PDF first.")
            return
        self.pdf_viewer.activate_area_tool()
        self._set_active_tool("area")
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Area tool active")

    def _on_activate_perimeter(self):
        if not self.pdf_viewer.doc:
            QMessageBox.warning(self, "No document", "Please open a PDF first.")
            return
        self.pdf_viewer.activate_perimeter_tool()
        self._set_active_tool("perimeter")
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Perimeter tool active")

    def _on_activate_calibrate(self):
        self._on_calibrate()

    def _on_calibrate(self):
        if not self.pdf_viewer.doc:
            QMessageBox.warning(self, "No document", "Please open a PDF first.")
            return
        self.pdf_viewer.activate_calibration_tool()
        self._set_active_tool("calibrate")
        self.cancel_button.setEnabled(True)
        self._update_calibration_status()
        self.statusBar().showMessage(self.pdf_viewer.get_calibration_status_message())

    def _update_calibration_status(self):
        calibration_status = self.pdf_viewer.get_calibration_status_message()
        self.calibration_panel.set_status(
            calibration_status,
            is_calibrated=self.pdf_viewer.get_active_calibration() is not None,
            calibration_text=calibration_status,
        )

    def _on_clear_calibration(self):
        self.pdf_viewer.clear_calibration()
        self._update_calibration_status()
        self.statusBar().showMessage("Calibration cleared")

    def _on_cancel_measurement(self):
        self.pdf_viewer.cancel_measurement()
        self._set_active_tool("")
        self.cancel_button.setEnabled(False)
        self.statusBar().showMessage("Cancelled")


if __name__ == "__main__":
    app = QApplication()
    window = MainWindow()
    window.show()
    app.exec()
