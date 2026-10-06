with open(r"c:\Users\moh09\QuantitySurveying\src\modules\measurement\snapping.py", "r") as f:
    content = f.read()

old_find_intersections_end = """                    intersections.append((intersection_x, intersection_y, 0.0))

        return intersections

    def snap_to_geometry"""

new_find_intersections_end = """                    intersections.append((intersection_x, intersection_y, 0.0))

        return intersections

    def find_midpoints(self, vector_elements) -> List[Tuple[float, float, float]]:
        \"\"\"Find midpoint points on line segments.\"\"\"
        midpoints = []
        
        for element in vector_elements:
            line = None
            if hasattr(element, "to_line_segment"):
                line = element.to_line_segment()
            elif hasattr(element, "start") and hasattr(element, "end"):
                line = LineSegment(start=element.start, end=element.end)
            if line:
                mid_x = (line.start.x + line.end.x) / 2.0
                mid_y = (line.start.y + line.end.y) / 2.0
                midpoints.append((mid_x, mid_y, 0.0))
        
        return midpoints

    def snap_to_geometry"""

content = content.replace(old_find_intersections_end, new_find_intersections_end)

with open(r"c:\Users\moh09\QuantitySurveying\src\modules\measurement\snapping.py", "w") as f:
    f.write(content)

print("Added find_midpoints")
