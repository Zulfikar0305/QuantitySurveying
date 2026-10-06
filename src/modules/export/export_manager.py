from __future__ import annotations

import csv
import json
from enum import Enum
from pathlib import Path
from typing import Iterable, Any, List


class ExportFormat(Enum):
    CSV = "csv"
    JSON = "json"


class MeasurementExporter:
    """Structured export layer for measurement and takeoff data."""

    @staticmethod
    def export_csv(records: Iterable[Any], output_path: str | Path) -> str:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        rows: List[dict] = []
        for record in records:
            item = record.to_dict() if hasattr(record, "to_dict") else dict(record)
            rows.append(item)

        fieldnames = [
            "measurement_id",
            "measurement_type",
            "page_index",
            "page_label",
            "pdf_file",
            "pdf_value",
            "real_world_value",
            "unit",
            "status",
            "calculation_method",
        ]

        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in fieldnames})
        return str(output)

    @staticmethod
    def export_json(records: Iterable[Any], output_path: str | Path) -> str:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for record in records:
            rows.append(record.to_dict() if hasattr(record, "to_dict") else dict(record))
        with output.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, sort_keys=True)
        return str(output)
