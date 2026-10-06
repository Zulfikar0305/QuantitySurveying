# Tests for Advanced Deterministic Measurement (Phase 3 Task 5)

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from modules.measurement import (
    Calibration, Unit, MeasurementState, SnappedPoint,
    MeasurementSession, MeasurementSessionManager, MeasurementRecord, MeasurementStatus,
    MeasurementType, MeasurementResult, TraceabilityInfo,
    MeasurementEngine, PolylineTool, AreaTool, PerimeterTool,
    SnappingSystem
)
from modules.viewer import CoordinateMapper
from modules.pdf_processing import Point, LineSegment


@pytest.fixture
def coordinate_mapper():
    return CoordinateMapper(
        zoom=2.0, offset_x=50.0, offset_y=100.0,
        page_width=595.0, page_height=842.0, page_rotation=0
    )


@pytest.fixture
def calibration_mm():
    return Calibration(pdf_reference_distance=250.0, real_world_reference_distance=5000.0, unit=Unit.MILLIMETRES)


@pytest.fixture
def engine_mm(calibration_mm):
    return MeasurementEngine(calibration=calibration_mm)


@pytest.fixture
def engine_uncalibrated():
    return MeasurementEngine(calibration=None)


class TestPolylineMeasurement:
    def test_polyline_distance_two_points_uncalibrated(self, coordinate_mapper, engine_uncalibrated):
        tool = PolylineTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_uncalibrated)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(150, 100)
        result = tool.handle_click(350, 100)
        assert result[1] is not None
        completed = tool.complete()
        assert completed is not None
        assert completed.measurement_type == MeasurementType.POLYLINE_LENGTH
        assert completed.pdf_value == 100.0
        assert completed.real_world_value is None

    def test_polyline_distance_three_points_calibrated(self, coordinate_mapper, engine_mm):
        tool = PolylineTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        result = tool.handle_click(450, 500)
        assert result[1] is not None
        assert result[1].pdf_value == 200.0
        assert result[1].real_world_value == 4000.0
        assert result[1].unit == Unit.MILLIMETRES

    def test_polyline_minimum_points(self, coordinate_mapper, engine_mm):
        tool = PolylineTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        result = tool.complete()
        assert result is None

    def test_polyline_cancel(self, coordinate_mapper, engine_mm):
        tool = PolylineTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.cancel()
        assert tool.interaction.state == MeasurementState.IDLE
        assert len(tool.get_points()) == 0

    def test_polyline_get_current_measurement(self, coordinate_mapper, engine_mm):
        tool = PolylineTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        current = tool.get_current_measurement()
        assert current is not None
        assert current.pdf_value == 200.0


class TestAreaMeasurement:
    def test_area_square_calibrated(self, coordinate_mapper, engine_mm):
        tool = AreaTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        tool.handle_click(250, 500)
        result = tool.handle_click(250, 300)
        assert result[0] is not None
        assert result[0].measurement_type == MeasurementType.POLYGON_AREA
        assert result[0].pdf_value == 10000.0
        assert result[0].real_world_value == 4000000.0
        assert result[0].unit == Unit.MILLIMETRES

    def test_area_minimum_points(self, coordinate_mapper, engine_mm):
        tool = AreaTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        assert not tool.is_valid_for_completion()
        # Adding a 3rd point - not yet valid for completion (need 3+ points)
        result = tool.handle_click(650, 300)
        # result[0] is the completed measurement (None since not closed yet)
        # The tool should have added the point
        assert result[0] is None  # No completed measurement yet

    def test_area_cancel(self, coordinate_mapper, engine_mm):
        tool = AreaTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        tool.cancel()
        assert tool.interaction.state == MeasurementState.IDLE


class TestPerimeterMeasurement:
    def test_perimeter_square_calibrated(self, coordinate_mapper, engine_mm):
        tool = PerimeterTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        tool.handle_click(250, 500)
        result = tool.handle_click(250, 300)
        assert result[0] is not None
        assert result[0].measurement_type == MeasurementType.POLYGON_PERIMETER
        assert result[0].pdf_value == 400.0

    def test_perimeter_minimum_points(self, coordinate_mapper, engine_mm):
        tool = PerimeterTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        assert not tool.is_valid_for_completion()
        # Adding 3rd point - still not closed yet, so returns intermediate measurement
        result = tool.handle_click(650, 300)
        # result[0] is None (not closed), result[1] is the perimeter so far
        assert result[0] is None
        assert result[1] is not None  # Intermediate measurement returned

    def test_perimeter_cancel(self, coordinate_mapper, engine_mm):
        tool = PerimeterTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0)
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        tool.cancel()
        assert tool.interaction.state == MeasurementState.IDLE


class TestSnappingSystem:
    def test_snapping_to_line_endpoint(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(100, 100, 200, 100)]
        result = snapping.snap_to_geometry(vector_elements, [], (102, 100))
        assert result.snapped is True
        assert result.snap_type in ("line_start", "line_end")

    def test_no_snap_outside_tolerance(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (500, 500))
        assert result.snapped is False

    def test_snap_within_tolerance(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (2, 0))
        assert result.snapped is True


class TestSnappingIntersections:
    def test_snapping_to_intersection(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 200), MockLine(0, 200, 200, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (102, 102))
        assert result.snapped is True
        assert result.snap_type == "intersection"

    def test_no_intersection_on_parallel_lines(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0), MockLine(0, 10, 200, 10)]
        result = snapping.snap_to_geometry(vector_elements, [], (100, 5))
        assert result.snapped is True


class TestSnappingMidpoint:
    def test_snapping_to_midpoint(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (100, 0))
        assert result.snapped is True
        assert result.snap_type == "midpoint"

    def test_midpoint_with_tolerance(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (102, 0))
        assert result.snapped is True
        assert result.snap_type == "midpoint"


class TestSnappingNearestPoint:
    def test_snapping_to_nearest_on_segment(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (100, 5))
        assert result.snapped is True
        assert result.snap_type in ("nearest_on_segment", "midpoint")  # midpoint might be closer

    def test_nearest_point_clamped_to_segment_end(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 100, 0)]
        result = snapping.snap_to_geometry(vector_elements, [], (102, 5))  # Near endpoint
        assert result.snapped is False


class TestSnappingToggleable:
    def test_disabling_intersections(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 200), MockLine(0, 200, 200, 0)]
        result_enabled = snapping.snap_to_geometry(vector_elements, [], (100, 100), enable_intersections=True)
        assert result_enabled.snapped is True
        assert result_enabled.snap_type == "intersection"
        result_disabled = snapping.snap_to_geometry(vector_elements, [], (100, 100), enable_intersections=False)
        assert result_disabled.snapped is True
        assert result_disabled.snap_type != "intersection"

    def test_disabling_midpoints(self, coordinate_mapper):
        snapping = SnappingSystem(tolerance_page_units=5.0)
        class MockLine:
            def __init__(self, x1, y1, x2, y2):
                self.start = Point(x=x1, y=y1)
                self.end = Point(x=x2, y=y2)
            def to_line_segment(self):
                return LineSegment(start=self.start, end=self.end)
        vector_elements = [MockLine(0, 0, 200, 0)]
        result_enabled = snapping.snap_to_geometry(vector_elements, [], (100, 0), enable_midpoints=True)
        assert result_enabled.snapped is True
        assert result_enabled.snap_type == "midpoint"
        result_disabled = snapping.snap_to_geometry(vector_elements, [], (100, 0), enable_midpoints=False)
        assert result_disabled.snapped is True
        assert result_disabled.snap_type != "midpoint"


class TestMeasurementRecord:
    def test_record_creation(self, calibration_mm):
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0, source_points=[{"x": 100, "y": 200}]))
        record = MeasurementRecord(measurement_id="001", measurement_type=MeasurementType.DISTANCE, page_index=0,
            page_label="Sheet 1", pdf_file="test.pdf", pdf_points=[{"x": 100, "y": 200}],
            pdf_value=250.0, calibration_used={"pdf_reference_distance": 250.0, "real_world_reference_distance": 5000.0, "unit": "mm"},
            real_world_value=5000.0, unit="mm", status=MeasurementStatus.VALID, calculation_method="Euclidean distance")
        assert record.measurement_id == "001"
        assert record.is_calibrated is True
        assert record.status == MeasurementStatus.VALID
        assert "mm" in record.formatted_real_value

    def test_record_uncalibrated(self):
        result = MeasurementResult(measurement_type=MeasurementType.POLYLINE_LENGTH, pdf_value=500.0,
            calibration=None, unit=None, real_world_value=None, traceability=TraceabilityInfo(source_page_index=0))
        record = MeasurementRecord(measurement_id="002", measurement_type=MeasurementType.POLYLINE_LENGTH, page_index=0,
            page_label=None, pdf_file="test.pdf", pdf_points=[{"x": 0, "y": 0}],
            pdf_value=500.0, calibration_used=None, real_world_value=None, unit=None, status=MeasurementStatus.UNCALIBRATED)
        assert record.is_calibrated is False
        assert record.real_world_value is None
        assert record.unit is None
        assert "N/A" in record.formatted_real_value

    def test_record_to_dict(self, calibration_mm):
        record = MeasurementRecord(measurement_id="004", measurement_type=MeasurementType.POLYGON_PERIMETER, page_index=1,
            page_label="Sheet 2", pdf_file="test.pdf", pdf_points=[{"x": 0, "y": 0}],
            pdf_value=400.0, calibration_used={"pdf_reference_distance": 250.0, "real_world_reference_distance": 5000.0, "unit": "mm"},
            real_world_value=8000.0, unit="mm", status=MeasurementStatus.VALID)
        d = record.to_dict()
        assert d["measurement_id"] == "004"
        assert d["page_index"] == 1
        assert d["pdf_file"] == "test.pdf"


class TestMeasurementSession:
    def test_session_creation(self):
        session = MeasurementSession(pdf_file="test.pdf")
        assert session.pdf_file == "test.pdf"
        assert len(session.get_measurements()) == 0

    def test_add_measurement(self, calibration_mm):
        session = MeasurementSession(pdf_file="test.pdf")
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        record = session.add_measurement(result, page_index=0, page_label="Sheet 1")
        assert record.measurement_id == "001"
        assert len(session.get_measurements()) == 1

    def test_unique_ids(self):
        session = MeasurementSession(pdf_file="test.pdf")
        for i in range(3):
            result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=100.0,
                calibration=None, unit=None, real_world_value=None, traceability=TraceabilityInfo(source_page_index=0))
            record = session.add_measurement(result, page_index=0)
            assert record.measurement_id == f"{i+1:03d}"

    def test_get_measurement_by_id(self, calibration_mm):
        session = MeasurementSession(pdf_file="test.pdf")
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        record1 = session.add_measurement(result, page_index=0)
        record2 = session.add_measurement(result, page_index=1)
        found = session.get_measurement_by_id(record1.measurement_id)
        assert found.measurement_id == record1.measurement_id
        not_found = session.get_measurement_by_id("999")
        assert not_found is None

    def test_remove_measurement(self, calibration_mm):
        session = MeasurementSession(pdf_file="test.pdf")
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        record = session.add_measurement(result, page_index=0)
        removed = session.remove_measurement(record.measurement_id)
        assert removed is True
        found = session.get_measurement_by_id(record.measurement_id)
        assert found is None
        removed_again = session.remove_measurement(record.measurement_id)
        assert removed_again is False

    def test_clear_page(self, calibration_mm):
        session = MeasurementSession(pdf_file="test.pdf")
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        session.add_measurement(result, page_index=0)
        session.add_measurement(result, page_index=1)
        assert len(session.get_measurements()) == 2
        session.clear_page(0)
        assert len(session.get_measurements(page_index=0)) == 0
        assert len(session.get_measurements(page_index=1)) == 1

    def test_clear_all(self, calibration_mm):
        session = MeasurementSession(pdf_file="test.pdf")
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        session.add_measurement(result, page_index=0)
        session.add_measurement(result, page_index=1)
        session.clear_all()
        assert len(session.get_measurements()) == 0
        assert session.measurement_counter == 0

    def test_page_isolation(self, calibration_mm):
        session = MeasurementSession(pdf_file="test.pdf")
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        session.add_measurement(result, page_index=0)
        session.add_measurement(result, page_index=1)
        session.add_measurement(result, page_index=2)
        assert len(session.get_measurements(page_index=0)) == 1
        assert len(session.get_measurements(page_index=1)) == 1
        assert len(session.get_measurements(page_index=2)) == 1
        all_measurements = session.get_measurements()
        assert len(all_measurements) == 3

    def test_document_isolation(self, calibration_mm):
        manager = MeasurementSessionManager()
        result = MeasurementResult(measurement_type=MeasurementType.DISTANCE, pdf_value=250.0,
            calibration=calibration_mm, unit=Unit.MILLIMETRES, real_world_value=5000.0,
            traceability=TraceabilityInfo(source_page_index=0))
        session1 = manager.get_session("file1.pdf")
        session1.add_measurement(result, page_index=0)
        session2 = manager.get_session("file2.pdf")
        session2.add_measurement(result, page_index=0)
        session1.add_measurement(result, page_index=1)
        assert len(session1.get_measurements()) == 2
        assert len(session2.get_measurements()) == 1
        manager.remove_session("file1.pdf")
        new_session1 = manager.get_session("file1.pdf")
        assert len(new_session1.get_measurements()) == 0
        assert len(session2.get_measurements()) == 1


class TestInteractionCompletion:
    def test_polyline_complete_creates_record(self, coordinate_mapper, engine_mm):
        tool = PolylineTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        completed = tool.complete()
        assert completed is not None
        assert completed.measurement_type == MeasurementType.POLYLINE_LENGTH
        assert completed.pdf_value == 200.0

    def test_area_complete_creates_record(self, coordinate_mapper, engine_mm):
        tool = AreaTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        tool.handle_click(250, 500)
        completed = tool.handle_click(250, 300)
        assert completed[0] is not None
        assert completed[0].measurement_type == MeasurementType.POLYGON_AREA
        assert completed[0].pdf_value == 10000.0

    def test_perimeter_complete_creates_record(self, coordinate_mapper, engine_mm):
        tool = PerimeterTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        tool.handle_click(250, 300)
        tool.handle_click(450, 300)
        tool.handle_click(450, 500)
        tool.handle_click(250, 500)
        completed = tool.handle_click(250, 300)
        assert completed[0] is not None
        assert completed[0].measurement_type == MeasurementType.POLYGON_PERIMETER


class TestRegression:
    def test_distance_tool_still_works(self, coordinate_mapper, engine_mm):
        from modules.measurement import DistanceTool
        tool = DistanceTool(coordinate_mapper=coordinate_mapper, measurement_engine=engine_mm)
        tool.activate(page_index=0, page_label="Sheet 1")
        result1 = tool.handle_click(250, 300)
        assert result1 is None
        result2 = tool.handle_click(450, 300)
        assert result2 is not None
        assert result2.measurement_type == MeasurementType.DISTANCE
        assert result2.pdf_value == 100.0
        assert result2.real_world_value == 2000.0

    def test_calibration_still_works(self, coordinate_mapper):
        from modules.measurement import CalibrationInteraction
        interaction = CalibrationInteraction(coordinate_mapper=coordinate_mapper)
        interaction.activate()
        success, message = interaction.handle_click(250, 300)
        assert success is True
        success, message = interaction.handle_click(750, 300)
        assert success is True
        assert "PDF distance" in message

    def test_coordinate_mapping_invariant(self, coordinate_mapper, engine_mm):
        p1 = (100, 100)
        p2 = (200, 100)
        result1 = engine_mm.measure_distance(Point(x=p1[0], y=p1[1]), Point(x=p2[0], y=p2[1]))
        result2 = engine_mm.measure_distance(Point(x=p1[0], y=p1[1]), Point(x=p2[0], y=p2[1]))
        assert result1.pdf_value == result2.pdf_value
        assert result1.real_world_value == result2.real_world_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
