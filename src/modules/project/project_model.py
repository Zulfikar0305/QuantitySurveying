from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ProjectDrawing:
    drawing_id: str
    name: str
    pdf_path: str
    page_index: int = 0
    description: str = ""
    active: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectDrawing":
        return cls(
            drawing_id=str(data.get("drawing_id") or data.get("id") or f"drawing-{int(datetime.utcnow().timestamp() * 1000)}"),
            name=str(data.get("name") or "Drawing"),
            pdf_path=str(data.get("pdf_path") or data.get("path") or ""),
            page_index=int(data.get("page_index", 0) or 0),
            description=str(data.get("description") or ""),
            active=bool(data.get("active", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drawing_id": self.drawing_id,
            "name": self.name,
            "pdf_path": self.pdf_path,
            "page_index": self.page_index,
            "description": self.description,
            "active": self.active,
        }


@dataclass
class TakeoffItem:
    item_id: str
    code: str
    description: str
    quantity: float
    unit: str
    drawing: str
    page_index: int
    source_measurement: str = ""
    measurement_id: Optional[str] = None
    category: str = "general"
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TakeoffItem":
        return cls(
            item_id=str(data.get("item_id") or data.get("id") or f"takeoff-{int(datetime.utcnow().timestamp() * 1000)}"),
            code=str(data.get("code") or "TAKEOFF-001"),
            description=str(data.get("description") or ""),
            quantity=float(data.get("quantity", 0.0) or 0.0),
            unit=str(data.get("unit") or "m"),
            drawing=str(data.get("drawing") or data.get("drawing_name") or ""),
            page_index=int(data.get("page_index", 0) or 0),
            source_measurement=str(data.get("source_measurement") or data.get("source") or ""),
            measurement_id=str(data.get("measurement_id") or data.get("source_measurement_id") or None),
            category=str(data.get("category") or "general"),
            notes=str(data.get("notes") or ""),
            created_at=str(data.get("created_at") or datetime.utcnow().isoformat(timespec="seconds")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "code": self.code,
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "drawing": self.drawing,
            "page_index": self.page_index,
            "source_measurement": self.source_measurement,
            "measurement_id": self.measurement_id,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at,
        }


@dataclass
class ProjectState:
    project_id: str
    name: str
    description: str = ""
    active_pdf: Optional[str] = None
    drawings: List[ProjectDrawing] = field(default_factory=list)
    takeoff_items: List[TakeoffItem] = field(default_factory=list)
    calibration: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectState":
        drawings = [ProjectDrawing.from_dict(item) for item in data.get("drawings", [])]
        takeoff_items = [TakeoffItem.from_dict(item) for item in data.get("takeoff_items", [])]
        return cls(
            project_id=str(data.get("project_id") or ""),
            name=str(data.get("name") or "Untitled Project"),
            description=str(data.get("description") or ""),
            active_pdf=data.get("active_pdf"),
            drawings=drawings,
            takeoff_items=takeoff_items,
            calibration=data.get("calibration"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "active_pdf": self.active_pdf,
            "drawings": [drawing.to_dict() for drawing in self.drawings],
            "takeoff_items": [item.to_dict() for item in self.takeoff_items],
            "calibration": self.calibration,
        }
