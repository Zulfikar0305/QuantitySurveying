from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .project_model import ProjectDrawing, ProjectState, TakeoffItem


class ProjectDatabase:
    """Minimal SQLite-backed project and measurement persistence layer."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else Path.cwd() / "data" / "qs_projects.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active_pdf TEXT,
                    description TEXT,
                    drawings TEXT DEFAULT '[]',
                    calibration TEXT DEFAULT '{}',
                    takeoff_items TEXT DEFAULT '[]'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS measurements (
                    project_id TEXT NOT NULL,
                    measurement_id TEXT NOT NULL,
                    measurement_type TEXT NOT NULL,
                    page_index INTEGER NOT NULL,
                    page_label TEXT,
                    pdf_file TEXT,
                    pdf_points TEXT,
                    pdf_value REAL NOT NULL,
                    real_world_value REAL,
                    unit TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    calculation_method TEXT,
                    calibration_used TEXT,
                    PRIMARY KEY(project_id, measurement_id),
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS takeoff_items (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    measurement_id TEXT,
                    quantity REAL NOT NULL,
                    unit TEXT,
                    category TEXT,
                    note TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calibrations (
                    project_id TEXT NOT NULL,
                    pdf_reference_distance REAL NOT NULL,
                    real_world_reference_distance REAL NOT NULL,
                    unit TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(project_id)
                )
                """
            )
            conn.commit()

    def create_project(self, name: str, description: str = "") -> str:
        from datetime import datetime

        project_id = f"project-{int(datetime.utcnow().timestamp() * 1000)}"
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, created_at, updated_at, active_pdf, description, drawings, calibration, takeoff_items)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, name, timestamp, timestamp, None, description, "[]", "{}", "[]"),
            )
            conn.commit()
        return project_id

    def save_project_state(self, project_id: str, state: ProjectState) -> None:
        from datetime import datetime

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE projects
                SET name = ?, updated_at = ?, active_pdf = ?, description = ?, drawings = ?, calibration = ?, takeoff_items = ?
                WHERE id = ?
                """,
                (
                    state.name,
                    datetime.utcnow().isoformat(timespec="seconds"),
                    state.active_pdf,
                    state.description,
                    json.dumps([drawing.to_dict() for drawing in state.drawings], sort_keys=True),
                    json.dumps(state.calibration or {}, sort_keys=True),
                    json.dumps([item.to_dict() for item in state.takeoff_items], sort_keys=True),
                    project_id,
                ),
            )
            conn.commit()

    def get_project(self, project_id: str) -> Optional[ProjectState]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        row_dict = dict(row)
        return ProjectState(
            project_id=row_dict["id"],
            name=row_dict["name"],
            description=row_dict.get("description") or "",
            active_pdf=row_dict.get("active_pdf"),
            drawings=[ProjectDrawing.from_dict(item) for item in json.loads(row_dict.get("drawings") or "[]")],
            calibration=json.loads(row_dict.get("calibration") or "{}"),
            takeoff_items=[TakeoffItem.from_dict(item) for item in json.loads(row_dict.get("takeoff_items") or "[]")],
        )

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, active_pdf, description, updated_at FROM projects ORDER BY updated_at DESC",
            ).fetchall()
        return [dict(row) for row in rows]

    def update_project_pdf(self, project_id: str, pdf_path: str) -> None:
        from datetime import datetime

        with self._connect() as conn:
            conn.execute(
                "UPDATE projects SET active_pdf = ?, updated_at = ? WHERE id = ?",
                (pdf_path, datetime.utcnow().isoformat(timespec="seconds"), project_id),
            )
            conn.commit()

    def save_session_measurements(self, project_id: str, measurements: Iterable[Any], pdf_file: str | None = None) -> None:
        from datetime import datetime

        if pdf_file:
            self.update_project_pdf(project_id, pdf_file)

        with self._connect() as conn:
            for measurement in measurements:
                as_dict = measurement.to_dict() if hasattr(measurement, "to_dict") else dict(measurement)
                conn.execute(
                    """
                    INSERT INTO measurements (
                        project_id, measurement_id, measurement_type, page_index, page_label,
                        pdf_file, pdf_points, pdf_value, real_world_value, unit, status,
                        created_at, calculation_method, calibration_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id, measurement_id) DO UPDATE SET
                        measurement_type = excluded.measurement_type,
                        page_index = excluded.page_index,
                        page_label = excluded.page_label,
                        pdf_file = excluded.pdf_file,
                        pdf_points = excluded.pdf_points,
                        pdf_value = excluded.pdf_value,
                        real_world_value = excluded.real_world_value,
                        unit = excluded.unit,
                        status = excluded.status,
                        created_at = excluded.created_at,
                        calculation_method = excluded.calculation_method,
                        calibration_used = excluded.calibration_used
                    """,
                    (
                        project_id,
                        str(as_dict.get("measurement_id") or as_dict.get("id") or ""),
                        as_dict.get("measurement_type") or "distance",
                        int(as_dict.get("page_index", 0) or 0),
                        as_dict.get("page_label"),
                        as_dict.get("pdf_file"),
                        json.dumps(as_dict.get("pdf_points", []), sort_keys=True),
                        float(as_dict.get("pdf_value", 0.0) or 0.0),
                        as_dict.get("real_world_value"),
                        as_dict.get("unit"),
                        as_dict.get("status") or "valid",
                        as_dict.get("created_at") or datetime.utcnow().isoformat(timespec="seconds"),
                        as_dict.get("calculation_method"),
                        json.dumps(as_dict.get("calibration_used"), sort_keys=True) if as_dict.get("calibration_used") is not None else None,
                    ),
                )
            conn.commit()

    def load_measurements(self, project_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM measurements WHERE project_id = ? ORDER BY page_index, measurement_id",
                (project_id,),
            ).fetchall()
        records = []
        for row in rows:
            item = dict(row)
            item["pdf_points"] = json.loads(item["pdf_points"] or "[]")
            item["calibration_used"] = json.loads(item["calibration_used"]) if item["calibration_used"] else None
            records.append(item)
        return records

    def add_takeoff_item(
        self,
        project_id: str,
        description: str,
        quantity: float,
        unit: str,
        measurement_id: Optional[str] = None,
        category: str = "general",
        note: str = "",
        code: str = "ITEM-001",
        drawing: str = "",
        page_index: int = 0,
        source_measurement: str = "",
    ) -> str:
        from datetime import datetime

        item_id = f"takeoff-{int(datetime.utcnow().timestamp() * 1000)}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO takeoff_items (id, project_id, description, measurement_id, quantity, unit, category, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, project_id, description, measurement_id, float(quantity), unit, category, note, datetime.utcnow().isoformat(timespec="seconds")),
            )
            conn.commit()
        return item_id

    def add_takeoff_item_full(
        self,
        project_id: str,
        item: TakeoffItem,
    ) -> str:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO takeoff_items (id, project_id, description, measurement_id, quantity, unit, category, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    description = excluded.description,
                    measurement_id = excluded.measurement_id,
                    quantity = excluded.quantity,
                    unit = excluded.unit,
                    category = excluded.category,
                    note = excluded.note,
                    created_at = excluded.created_at
                """,
                (
                    item.item_id,
                    project_id,
                    item.description,
                    item.measurement_id,
                    float(item.quantity),
                    item.unit,
                    item.category,
                    item.notes,
                    item.created_at,
                ),
            )
            conn.commit()
        return item.item_id

    def list_takeoff_items(self, project_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM takeoff_items WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_drawing(self, project_id: str, drawing: ProjectDrawing) -> None:
        current = self.get_project(project_id)
        if current is None:
            return
        existing = {item.drawing_id: item for item in current.drawings}
        existing[drawing.drawing_id] = drawing
        current.drawings = list(existing.values())
        self.save_project_state(project_id, current)

    def upsert_project_drawings(self, project_id: str, drawings: Iterable[ProjectDrawing]) -> None:
        current = self.get_project(project_id)
        if current is None:
            return
        current.drawings = list(drawings)
        self.save_project_state(project_id, current)

    def set_active_drawing(self, project_id: str, drawing_id: str) -> None:
        current = self.get_project(project_id)
        if current is None:
            return
        for drawing in current.drawings:
            drawing.active = drawing.drawing_id == drawing_id
        self.save_project_state(project_id, current)

    def export_measurements_csv(self, project_id: str, output_path: str | Path) -> str:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        measurements = self.load_measurements(project_id)

        with output.open("w", encoding="utf-8", newline="") as handle:
            handle.write("measurement_id,measurement_type,page_index,page_label,pdf_file,pdf_value,real_world_value,unit,status,calculation_method\n")
            for item in measurements:
                handle.write(
                    f"{item.get('measurement_id','')},{item.get('measurement_type','')},{item.get('page_index','')},{item.get('page_label','')},{item.get('pdf_file','')},{item.get('pdf_value','')},{item.get('real_world_value','')},{item.get('unit','')},{item.get('status','')},{item.get('calculation_method','')}\n"
                )
        return str(output)
