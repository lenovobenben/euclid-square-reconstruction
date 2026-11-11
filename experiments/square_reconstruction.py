"""Exact replay of the cross construction in docs/ANSWER.md."""

from dataclasses import dataclass

from sage.all import AA

from verify_classification import (
    add, convex_hull, cross, dot, geometric_count, subtract,
)


@dataclass(frozen=True)
class Line:
    a: object
    b: object
    c: object

    @classmethod
    def through(cls, first, second):
        if first == second:
            raise ValueError("a line needs two different points")
        dx, dy = subtract(second, first)
        return cls(-dy, dx, dy * first[0] - dx * first[1])

    def value(self, point):
        return self.a * point[0] + self.b * point[1] + self.c

    def perpendicular(self, point):
        return Line(-self.b, self.a, self.b * point[0] - self.a * point[1])

    def parallel(self, point):
        return Line(self.a, self.b, -self.a * point[0] - self.b * point[1])


@dataclass(frozen=True)
class Circle:
    center: tuple
    radius_squared: object

    def value(self, point):
        offset = subtract(point, self.center)
        return dot(offset, offset) - self.radius_squared


def intersect_lines(first, second):
    determinant = first.a * second.b - second.a * first.b
    if determinant == 0:
        raise ValueError("lines have no unique intersection")
    return ((first.b * second.c - second.b * first.c) / determinant,
            (first.c * second.a - second.c * first.a) / determinant)


def intersect_line_circle(line, circle):
    norm_squared = line.a ** 2 + line.b ** 2
    offset = line.value(circle.center)
    foot = (circle.center[0] - line.a * offset / norm_squared,
            circle.center[1] - line.b * offset / norm_squared)
    height_squared = circle.radius_squared - offset ** 2 / norm_squared
    if height_squared < 0:
        return ()
    if height_squared == 0:
        return (foot,)
    factor = (height_squared / norm_squared).sqrt()
    displacement = (-line.b * factor, line.a * factor)
    return (add(foot, displacement), subtract(foot, displacement))


def construct_square(coordinates):
    """Return four vertices, four side lines, and the named construction replay.

    The input is four unordered real algebraic points with exactly one legal
    square under the strict side-interior convention. Names A, B, C, D follow
    the canonical counterclockwise convex hull used by the classification.
    """
    if len(coordinates) != 4 or any(len(point) != 2 for point in coordinates):
        raise ValueError("exactly four plane points are required")
    given = [tuple(AA(value) for value in point) for point in coordinates]
    hull = convex_hull(given)
    if len(hull) != 4:
        raise ValueError("four strictly convex points are required")
    count = geometric_count(hull)
    if count == "infinite":
        raise ValueError("this input belongs to the continuous solution family")
    if count == 0:
        raise ValueError("there is no square with the points in strict side interiors")

    points = dict(zip("ABCD", hull))
    lines = {}
    circles = {}
    steps = []

    def record(operation, inputs, outputs):
        steps.append({"operation": operation, "inputs": inputs, "outputs": outputs})

    lines["AC"] = Line.through(points["A"], points["C"])
    record("line", ["A", "C"], ["AC"])
    lines["l"] = lines["AC"].perpendicular(points["B"])
    record("perpendicular", ["B", "AC"], ["l"])

    diagonal = subtract(points["C"], points["A"])
    circles["omega"] = Circle(points["B"], dot(diagonal, diagonal))
    record("circle", ["B", "A", "C"], ["omega"])
    intersections = intersect_line_circle(lines["l"], circles["omega"])
    if len(intersections) != 2:
        raise ArithmeticError("the diameter construction must have two intersections")
    points["E0"], points["E1"] = intersections
    record("intersect_line_circle", ["l", "omega"], ["E0", "E1"])

    b_side = cross(diagonal, subtract(points["B"], points["A"]))
    choices = [name for name in ("E0", "E1")
               if b_side * cross(diagonal, subtract(points[name], points["A"])) < 0]
    if len(choices) != 1:
        raise ArithmeticError("the opposite-side point must be unique")
    points["E"] = points[choices[0]]
    record("select_opposite_side", ["E0", "E1", "AC", "B"], ["E"])

    lines["d"] = Line.through(points["D"], points["E"])
    record("line", ["D", "E"], ["d"])
    lines["a"] = lines["d"].perpendicular(points["A"])
    record("perpendicular", ["A", "d"], ["a"])
    lines["c"] = lines["d"].perpendicular(points["C"])
    record("perpendicular", ["C", "d"], ["c"])
    lines["b"] = lines["d"].parallel(points["B"])
    record("parallel", ["B", "d"], ["b"])

    for name, first, second in (("P", "a", "d"), ("Q", "a", "b"),
                                ("R", "c", "b"), ("S", "c", "d")):
        points[name] = intersect_lines(lines[first], lines[second])
        record("intersect_lines", [first, second], [name])

    return {
        "points": points,
        "lines": lines,
        "circles": circles,
        "steps": steps,
        "vertices": tuple(points[name] for name in "PQRS"),
        "side_names": ("a", "b", "c", "d"),
    }
