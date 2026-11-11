"""Verify the actual cross-construction replay and its strict side constraints."""

import json
from collections import Counter
from itertools import combinations, permutations, product

from sage.all import AA, QQ
from sage.version import version as sage_version

from square_reconstruction import construct_square
from verify_classification import (
    add, check_square, classify, dot, rotate, side_memberships, similarity, subtract,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_replay(result):
    points, lines, circles = result["points"], result["lines"], result["circles"]
    available = set("ABCD")
    for step in result["steps"]:
        operation, inputs, outputs = step["operation"], step["inputs"], step["outputs"]
        require(all(name in available for name in inputs), "parent objects already exist")
        require(not any(name in available for name in outputs), "new output names")
        if operation == "line":
            line = lines[outputs[0]]
            require(line.a ** 2 + line.b ** 2 > 0, "nonzero line")
            require(all(line.value(points[name]) == 0 for name in inputs), "line incidence")
        elif operation == "perpendicular":
            point, reference = points[inputs[0]], lines[inputs[1]]
            line = lines[outputs[0]]
            require(line.value(point) == 0, "perpendicular through prescribed point")
            require(line.a * reference.a + line.b * reference.b == 0, "perpendicular lines")
        elif operation == "parallel":
            point, reference = points[inputs[0]], lines[inputs[1]]
            line = lines[outputs[0]]
            require(line.value(point) == 0, "parallel through prescribed point")
            require(line.a * reference.b - line.b * reference.a == 0, "parallel lines")
        elif operation == "circle":
            circle = circles[outputs[0]]
            diagonal = subtract(points[inputs[2]], points[inputs[1]])
            require(circle.center == points[inputs[0]], "prescribed circle center")
            require(circle.radius_squared == dot(diagonal, diagonal) > 0,
                    "prescribed positive squared radius")
        elif operation == "intersect_line_circle":
            line, circle = lines[inputs[0]], circles[inputs[1]]
            require(len(outputs) == 2 and points[outputs[0]] != points[outputs[1]],
                    "two distinct circle intersections")
            for name in outputs:
                require(line.value(points[name]) == circle.value(points[name]) == 0,
                        "point belongs to both parents")
        elif operation == "select_opposite_side":
            line = lines[inputs[2]]
            chosen = points[outputs[0]]
            require(chosen in (points[inputs[0]], points[inputs[1]]), "existing circle point")
            require(line.value(chosen) * line.value(points[inputs[3]]) < 0,
                    "strictly opposite sides of AC")
        elif operation == "intersect_lines":
            require(all(lines[name].value(points[outputs[0]]) == 0 for name in inputs),
                    "vertex belongs to both side lines")
        else:
            raise AssertionError("unrecognized construction operation")
        available.update(outputs)

    expected_operations = {
        "line": 2, "perpendicular": 3, "parallel": 1, "circle": 1,
        "intersect_line_circle": 1, "select_opposite_side": 1, "intersect_lines": 4,
    }
    require(dict(Counter(step["operation"] for step in result["steps"])) == expected_operations,
            "documented macro operation counts")
    a, b, c, d = (points[name] for name in "ABCD")
    diagonal = subtract(c, a)
    require(points["E"] == add(b, rotate(diagonal)), "selected quarter-turn orientation")
    require(points["E"] != d, "unique-solution direction is defined")
    require(lines["AC"].value(b) ** 2
            < dot(diagonal, diagonal) * (lines["AC"].a ** 2 + lines["AC"].b ** 2),
            "distance from B to AC is strictly less than AC")
    check_square(result["vertices"])
    require(all(side_memberships((a, b, c, d), result["vertices"])),
            "each prescribed point lies in its open side segment")


def verify_rejection(points):
    try:
        construct_square(points)
    except ValueError:
        return
    raise AssertionError("input outside the unique-solution domain was accepted")


def run():
    replay_count = 0
    rejection_count = 0
    grid_counts = Counter()
    grid = tuple(product(range(-1, 3), repeat=2))
    for points in combinations(grid, 4):
        classification = classify(points)
        grid_counts[str(classification["count"])] += 1
        if classification["count"] == 1:
            result = construct_square(points)
            verify_replay(result)
            require(result["vertices"] == classification["candidate"],
                    "independent coordinate-classification vertices")
            replay_count += 1
        else:
            verify_rejection(points)
            rejection_count += 1

    known_counts = Counter()
    values = (QQ(1) / 4, QQ(1) / 2, QQ(3) / 4)
    unit_square = tuple((QQ(x), QQ(y)) for x, y in ((0, 0), (1, 0), (1, 1), (0, 1)))
    for a, b, c, d in product(values, repeat=4):
        original = ((a, 0), (1, b), (c, 1), (0, d))
        for transform in range(4):
            points = [similarity(point, transform) for point in original]
            if d - b - c + a == 0:
                verify_rejection(points)
                known_counts["continuous_family"] += 1
                rejection_count += 1
                continue
            result = construct_square(points)
            verify_replay(result)
            expected = {similarity(point, transform) for point in unit_square}
            require(sorted(result["vertices"]) == sorted(expected), "recover known transformed square")
            known_counts["unique"] += 1
            replay_count += 1

    example = ((0, 1), (3, 0), (4, 2), (1, 4))
    for transform in range(4):
        points = [similarity(tuple(QQ(value) for value in point), transform) for point in example]
        expected = {similarity((QQ(x), QQ(y)), transform)
                    for x, y in ((0, 0), (4, 0), (4, 4), (0, 4))}
        for permuted in permutations(points):
            result = construct_square(permuted)
            verify_replay(result)
            require(sorted(result["vertices"]) == sorted(expected), "unordered input and reflection")
            replay_count += 1

    epsilon = QQ(1) / 10 ** 100
    special_inputs = {
        "auxiliary_at_vertex": ((QQ(1) / 4, 0), (1, QQ(1) / 2),
                                (QQ(3) / 4, 1), (0, QQ(1) / 4)),
        "auxiliary_outside_side": ((QQ(9) / 10, 0), (1, QQ(1) / 10),
                                   (QQ(1) / 10, 1), (0, QQ(7) / 10)),
        "near_continuous_family": ((QQ(1) / 2, 0), (1, QQ(1) / 2),
                                   (QQ(1) / 2, 1), (0, QQ(1) / 2 + epsilon)),
        "near_square_vertex": ((epsilon, 0), (1, QQ(1) / 4),
                               (QQ(1) / 2, 1), (0, QQ(3) / 4)),
    }
    for name, points in special_inputs.items():
        result = construct_square(points)
        verify_replay(result)
        require(sorted(result["vertices"]) == sorted(unit_square), name)
        if name == "auxiliary_at_vertex":
            require(result["points"]["E"] in result["vertices"], "auxiliary corner case")
        if name == "auxiliary_outside_side":
            auxiliary = result["points"]["E"]
            require(not all(0 <= value <= 1 for value in auxiliary), "auxiliary extension case")
        replay_count += 1

    root_two, root_three = AA(2).sqrt(), AA(3).sqrt()

    def algebraic_similarity(point):
        x, y = point
        return (root_two * x - root_three * y + QQ(1) / 7,
                root_three * x + root_two * y - QQ(2) / 5)

    result = construct_square([algebraic_similarity(point) for point in example])
    verify_replay(result)
    require(sorted(result["vertices"]) == sorted(
        algebraic_similarity(point) for point in ((0, 0), (4, 0), (4, 4), (0, 4))
    ), "irrational algebraic input")
    replay_count += 1

    for points in ([(0, 0)] * 4, [(0, 0), (0, 0), (1, 0), (0, 1)],
                   [(0, 0), (1, 0), (2, 0), (3, 0)],
                   [(0, 0), (1, 0), (0, 1)],
                   [(0, 0, 0), (1, 0), (1, 1), (0, 1)]):
        verify_rejection(points)
        rejection_count += 1

    example_result = construct_square(example)
    print(json.dumps({
        "valid": True,
        "sage_version": sage_version,
        "construction_replay_count": replay_count,
        "rejected_input_count": rejection_count,
        "grid_input_counts": dict(sorted(grid_counts.items())),
        "known_square_input_counts": dict(sorted(known_counts.items())),
        "permutation_and_similarity_count": 96,
        "special_inputs": list(special_inputs) + ["irrational_algebraic_input"],
        "macro_step_count": len(example_result["steps"]),
        "example_points": {name: [str(QQ(value)) for value in example_result["points"][name]]
                           for name in "ABCDEPQRS"},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
