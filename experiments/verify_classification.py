"""Exact checks for docs/CLASSIFICATION.md, using SageMath 10.7."""

import json
from collections import Counter
from itertools import combinations, permutations, product

from sage.all import QQ, PolynomialRing
from sage.version import version as sage_version


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def add(first, second):
    return (first[0] + second[0], first[1] + second[1])


def subtract(first, second):
    return (first[0] - second[0], first[1] - second[1])


def scale(factor, direction):
    return (factor * direction[0], factor * direction[1])


def dot(first, second):
    return first[0] * second[0] + first[1] * second[1]


def cross(first, second):
    return first[0] * second[1] - first[1] * second[0]


def rotate(direction):
    return (-direction[1], direction[0])


def convex_hull(points):
    ordered = sorted(set(points))
    halves = []
    for sequence in (ordered, ordered[::-1]):
        half = []
        for point in sequence:
            while len(half) >= 2 and cross(
                subtract(half[-1], half[-2]), subtract(point, half[-1])
            ) <= 0:
                half.pop()
            half.append(point)
        halves.append(half)
    return halves[0][:-1] + halves[1][:-1]


def geometric_count(points):
    """Use only the cross direction and the four unique coordinate extrema."""
    hull = convex_hull(points)
    if len(hull) != 4:
        return 0
    a, b, c, d = hull
    auxiliary = add(b, rotate(subtract(c, a)))
    vertical = subtract(d, auxiliary)
    if vertical == (0, 0):
        return "infinite"
    horizontal = rotate(vertical)
    heights = [dot(point, vertical) for point in hull]
    positions = [dot(point, horizontal) for point in hull]
    ac_bottom, ac_top = sorted((heights[0], heights[2]))
    bd_left, bd_right = sorted((positions[1], positions[3]))
    ac_extrema = all(ac_bottom < heights[index] < ac_top for index in (1, 3))
    bd_extrema = all(bd_left < positions[index] < bd_right for index in (0, 2))
    return int(ac_extrema and bd_extrema)


def classify(points):
    """Classify four unordered rational points with strict side interiors."""
    if len(points) != 4:
        raise ValueError("exactly four points are required")
    points = [tuple(QQ(coordinate) for coordinate in point) for point in points]
    if any(len(point) != 2 for point in points):
        raise ValueError("each point needs two coordinates")
    hull = convex_hull(points)
    result = {"count": 0, "ordered_points": hull}
    if len(hull) != 4:
        result["reason"] = "not_strictly_convex"
        return result

    a_point, b_point, c_point, d_point = hull
    p = subtract(c_point, a_point)
    q = subtract(d_point, b_point)
    w = subtract(q, rotate(p))
    h = dot(p, q)

    if w == (0, 0):
        offset = subtract(b_point, a_point)
        norm_squared = dot(p, p)
        b = dot(offset, p) / norm_squared
        t = -dot(offset, rotate(p)) / norm_squared
        require(0 < b < 1 and 0 < t < 1, "convex family normalization")
        lower = -min(t / b, (1 - t) / (1 - b), (1 - b) / t, b / (1 - t))
        upper = min((1 - t) / b, t / (1 - b), b / t, (1 - b) / (1 - t))
        result.update(count="infinite", family=(b, t, lower, upper))
        return result

    if h == 0:
        result["reason"] = "perpendicular_unequal_diagonals"
        return result

    u = scale(-1, rotate(w))
    v = w
    parameters = (
        dot(subtract(a_point, d_point), u) / h,
        dot(subtract(b_point, a_point), v) / h,
        dot(subtract(c_point, d_point), u) / h,
        dot(subtract(d_point, a_point), v) / h,
    )
    norm_squared = dot(w, w)

    def inverse(x, y):
        return add(
            scale((h * x + dot(d_point, u)) / norm_squared, u),
            scale((h * y + dot(a_point, v)) / norm_squared, v),
        )

    square = tuple(inverse(x, y) for x, y in ((0, 0), (1, 0), (1, 1), (0, 1)))
    valid = all(0 < value < 1 for value in parameters)
    result.update(
        count=int(valid), parameters=parameters, candidate=square,
        reason="strict_interiors" if valid else "side_parameter_out_of_range",
    )
    return result


def on_segment(point, first, second, strict=True):
    edge = subtract(second, first)
    displacement = subtract(point, first)
    if cross(edge, displacement) != 0:
        return False
    position = dot(displacement, edge)
    length_squared = dot(edge, edge)
    if strict:
        return 0 < position < length_squared
    return 0 <= position <= length_squared


def check_square(square):
    edges = [subtract(square[(index + 1) % 4], square[index]) for index in range(4)]
    lengths = [dot(edge, edge) for edge in edges]
    require(lengths[0] > 0 and len(set(lengths)) == 1, "positive equal sides")
    require(all(dot(edges[index], edges[(index + 1) % 4]) == 0 for index in range(4)),
            "adjacent perpendicular sides")
    require(cross(edges[0], edges[1]) > 0, "counterclockwise square")


def side_memberships(points, square, strict=True):
    return [on_segment(point, square[index], square[(index + 1) % 4], strict)
            for index, point in enumerate(points)]


def family_square(result, parameter):
    a_point, _, c_point, _ = result["ordered_points"]
    p = subtract(c_point, a_point)
    jp = rotate(p)
    b, t, _, _ = result["family"]
    lower = parameter * b + t - 1
    norm_squared = 1 + parameter ** 2
    square = []
    for first, second in ((lower, 0), (lower + 1, 0), (lower + 1, 1), (lower, 1)):
        x = (parameter * first + second) / norm_squared
        y = (-first + parameter * second) / norm_squared
        square.append(add(a_point, add(scale(x, p), scale(y, jp))))
    return tuple(square)


def check_result(result):
    points = result["ordered_points"]
    require(geometric_count(points) == result["count"], "geometric extrema criterion")
    if result["count"] == "infinite":
        _, _, lower, upper = result["family"]
        require(lower < 0 < upper, "nonempty open family interval")
        for parameter in (lower / 2, QQ(0), upper / 2, (3 * lower + upper) / 4,
                          (lower + 3 * upper) / 4):
            square = family_square(result, parameter)
            check_square(square)
            require(all(side_memberships(points, square)), "strict family member")
        for parameter in (lower, upper):
            square = family_square(result, parameter)
            check_square(square)
            require(all(side_memberships(points, square, strict=False)), "closed endpoint")
            require(any(point in square for point in points), "endpoint reaches a vertex")
            require(not all(side_memberships(points, square)), "endpoint excluded")
        for parameter in (lower - 1, upper + 1):
            square = family_square(result, parameter)
            require(not all(side_memberships(points, square)), "outside interval excluded")
    elif "candidate" in result:
        square = result["candidate"]
        check_square(square)
        valid = all(side_memberships(points, square))
        require(valid == bool(result["count"]), "independent open segment membership")


def symbolic_checks():
    ring = PolynomialRing(QQ, names=("px", "py", "qx", "qy"))
    px, py, qx, qy = ring.gens()
    p, q = (px, py), (qx, qy)
    v = subtract(q, rotate(p))
    u = scale(-1, rotate(v))
    h = dot(p, q)
    identities = [dot(p, v) - h, dot(scale(-1, q), u) - h,
                  dot(u, v), dot(u, u) - dot(v, v), cross(u, v) - dot(v, v)]

    ring = PolynomialRing(QQ, names=("s", "alpha", "beta", "gamma", "delta"))
    s, alpha, beta, gamma, delta = ring.gens()
    a_point, b_point = (alpha * s, 0), (s, beta * s)
    c_point, d_point = (gamma * s, s), (0, delta * s)
    p, q = subtract(c_point, a_point), subtract(d_point, b_point)
    w, h = subtract(q, rotate(p)), dot(p, q)
    coefficient = delta - beta - gamma + alpha
    identities.extend([w[0], w[1] - s * coefficient, h - s ** 2 * coefficient])
    u, v = scale(-1, rotate(w)), w
    identities.extend([
        dot(subtract(a_point, d_point), u) - alpha * h,
        dot(subtract(b_point, a_point), v) - beta * h,
        dot(subtract(c_point, d_point), u) - gamma * h,
        dot(subtract(d_point, a_point), v) - delta * h,
    ])
    for identity in identities:
        require(identity == 0, "symbolic polynomial identity")
    return len(identities)


def similarity(point, index):
    x, y = point
    if index == 0:
        return (x, y)
    if index == 1:
        return (3 - 2 * y, -5 + 2 * x)
    if index == 2:
        return (7 + (3 * x - 4 * y) / 5, -11 + (4 * x + 3 * y) / 5)
    return (-2 - x, 3 + y)


def run():
    symbolic_count = symbolic_checks()
    examples = [
        ("repeated", [(0, 0), (0, 0), (1, 0), (0, 1)], 0),
        ("collinear", [(0, 0), (1, 0), (2, 0), (3, 0)], 0),
        ("three_collinear", [(0, 0), (1, 0), (2, 0), (0, 2)], 0),
        ("interior_point", [(0, 0), (4, 0), (0, 4), (1, 1)], 0),
        ("perpendicular_unequal", [(-2, 0), (0, -1), (2, 0), (0, 1)], 0),
        ("outside_segment", [(0, 0), (2, 0), (4, 1), (0, 2)], 0),
        ("at_vertex", [(0, 0), (2, 0), (3, 1), (0, 2)], 0),
        ("unique", [(1, 0), (4, 1), (2, 4), (0, 3)], 1),
        ("rectangle", [(0, 0), (2, 0), (2, 1), (0, 1)], 1),
        ("square", [(0, 0), (1, 0), (1, 1), (0, 1)], "infinite"),
        ("infinite_nonsquare", [(0, 0), (1, -1), (4, 0), (1, 3)], "infinite"),
    ]
    example_results = []
    permutation_count = 0
    for name, points, expected in examples:
        points = [tuple(QQ(value) for value in point) for point in points]
        original = classify(points)
        require(original["count"] == expected, name)
        check_result(original)
        for transform in range(4):
            transformed = [similarity(point, transform) for point in points]
            baseline = classify(transformed)
            check_result(baseline)
            require(baseline["count"] == expected, "similarity invariant count")
            if expected == 1:
                expected_square = {similarity(vertex, transform)
                                   for vertex in original["candidate"]}
                require(set(baseline["candidate"]) == expected_square,
                        "similarity preserves unique square")
            for permuted in permutations(transformed):
                result = classify(permuted)
                require(result == baseline, "point permutation invariance")
                permutation_count += 1
        example_results.append({"name": name, "count": expected})

    square_inputs = Counter()
    values = [QQ(1) / 4, QQ(1) / 2, QQ(3) / 4]
    original_square = {(QQ(0), QQ(0)), (QQ(1), QQ(0)),
                       (QQ(1), QQ(1)), (QQ(0), QQ(1))}
    for a, b, c, d in product(values, repeat=4):
        points = [(a, 0), (1, b), (c, 1), (0, d)]
        result = classify(points)
        expected = "infinite" if d - b - c + a == 0 else 1
        require(result["count"] == expected, "known square input")
        check_result(result)
        if expected == 1:
            require(set(result["candidate"]) == original_square, "recover known square")
        square_inputs[str(expected)] += 1

    epsilon = QQ(1) / 10 ** 100
    for a, b, c, d in ((epsilon, QQ(1) / 4, QQ(1) / 2, QQ(3) / 4),
                        (QQ(1) / 2, QQ(1) / 2, QQ(1) / 2, QQ(1) / 2 + epsilon)):
        result = classify([(a, 0), (1, b), (c, 1), (0, d)])
        require(result["count"] == 1, "exact near-boundary input")
        check_result(result)
        require(set(result["candidate"]) == original_square, "near-boundary square")

    grid = [(QQ(x), QQ(y)) for x, y in product(range(-1, 3), repeat=2)]
    grid_counts = Counter()
    for points in combinations(grid, 4):
        result = classify(points)
        check_result(result)
        grid_counts[str(result["count"])] += 1

    report = {
        "valid": True,
        "sage_version": sage_version,
        "symbolic_identity_count": symbolic_count,
        "examples": example_results,
        "similarity_and_permutation_count": permutation_count,
        "known_square_input_counts": dict(sorted(square_inputs.items())),
        "near_boundary_input_count": 2,
        "geometric_extrema_criterion": "matches the coordinate classification",
        "rational_grid_input_counts": dict(sorted(grid_counts.items())),
        "family_checks": "five interior parameters, both endpoints, both exterior parameters",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
