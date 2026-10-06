from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

from .project_model import ProjectDrawing, ProjectState, TakeoffItem
from .project_store import ProjectDatabase


class ProjectManager:
    """High-level project lifecycle manager for the desktop QS application."""

    def __init__(self, database: Optional[ProjectDatabase] = None):
        self.database = database or ProjectDatabase()
        self.project_id: Optional[str] = None
        self.state: Optional[ProjectState] = None

    def list_projects(self):
        return self.database.list_projects()

    def create_new(self, name: str = "Untitled Project", description: str = "") -> str:
        self.project_id = self.database.create_project(name, description)
        self.state = self.database.get_project(self.project_id)
        return self.project_id

    def load(self, project_id: str) -> Optional[ProjectState]:
        state = self.database.get_project(project_id)
        if state is None:
            return None
        self.project_id = project_id
        self.state = state
        return state

    def save(self) -> bool:
        if self.project_id is None or self.state is None:
            return False
        self.database.save_project_state(self.project_id, self.state)
        return True

    def close(self) -> None:
        self.project_id = None
        self.state = None

    def set_active_pdf(self, pdf_path: str) -> Optional[str]:
        if self.project_id is None or self.state is None:
            return None
        self.state.active_pdf = pdf_path
        self.database.update_project_pdf(self.project_id, pdf_path)
        return pdf_path

    def add_drawing(self, pdf_path: str, name: Optional[str] = None, description: str = "", page_index: int = 0) -> Optional[ProjectDrawing]:
        if self.project_id is None:
            return None
        if self.state is None:
            self.state = self.database.get_project(self.project_id)
        if self.state is None:
            return None

        drawing = ProjectDrawing(
            drawing_id=f"drawing-{len(self.state.drawings) + 1:03d}",
            name=name or Path(pdf_path).stem,
            pdf_path=pdf_path,
            page_index=page_index,
            description=description,
            active=True,
        )

        existing = {item.pdf_path: item for item in self.state.drawings}
        existing[pdf_path] = drawing
        for item in self.state.drawings:
            item.active = False
        self.state.drawings = list(existing.values())
        for item in self.state.drawings:
            item.active = item.pdf_path == pdf_path
        self.state.active_pdf = pdf_path
        self.database.upsert_project_drawings(self.project_id, self.state.drawings)
        self.save()
        return drawing

    def add_takeoff_item(
        self,
        measurement: Any,
        *,
        code: str,
        description: str,
        quantity: Optional[float] = None,
        unit: str,
        drawing: str,
        page_index: int,
        notes: str = "",
        category: str = "general",
    ) -> Optional[TakeoffItem]:
        if self.project_id is None or self.state is None:
            return None

        measurement_id = None
        source_measurement = ""
        if hasattr(measurement, "measurement_id"):
            measurement_id = str(measurement.measurement_id)
            source_measurement = f"Measurement #{measurement.measurement_id}"
        elif isinstance(measurement, dict):
            measurement_id = str(measurement.get("measurement_id") or measurement.get("id") or "")
            source_measurement = f"Measurement #{measurement_id}" if measurement_id else "Manual entry"

        final_quantity = quantity
        if final_quantity is None:
            if hasattr(measurement, "real_world_value"):
                final_quantity = measurement.real_world_value or measurement.pdf_value
            elif isinstance(measurement, dict):
                final_quantity = measurement.get("real_world_value") or measurement.get("pdf_value") or 0.0

        item = TakeoffItem(
            item_id=f"takeoff-{len(self.state.takeoff_items) + 1:03d}",
            code=code,
            description=description,
            quantity=float(final_quantity or 0.0),
            unit=unit,
            drawing=drawing,
            page_index=int(page_index or 0),
            source_measurement=source_measurement,
            measurement_id=measurement_id,
            category=category,
            notes=notes,
        )
        self.state.takeoff_items.append(item)
        self.database.add_takeoff_item_full(self.project_id, item)
        return item

    def get_active_drawing(self) -> Optional[ProjectDrawing]:
        if self.state is None:
            return None
        for drawing in self.state.drawings:
            if drawing.active:
                return drawing
        return self.state.drawings[0] if self.state.drawings else None
