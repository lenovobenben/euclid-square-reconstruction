"""Audit the classification by solving every point-to-side assignment directly."""

import json
from collections import Counter
from itertools import combinations, permutations, product
from random import Random

from sage.all import QQ, matrix, vector
from sage.version import version as sage_version

from verify_classification import classify, geometric_count


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def square_from_similarity(solution):
    r, s, tx, ty = solution
    norm_squared = r * r + s * s
    require(norm_squared > 0, "invertible square similarity")
    return frozenset(
        ((r * (x - tx) - s * (y - ty)) / norm_squared,
         (s * (x - tx) + r * (y - ty)) / norm_squared)
        for x, y in ((0, 0), (1, 0), (1, 1), (0, 1))
    )


def strict_parameter_interval(values, slopes):
    lower = None
    upper = None
    for value, slope in zip(values, slopes):
        if slope == 0:
            if not 0 < value < 1:
                return None
            continue
        first = -value / slope
        second = (1 - value) / slope
        interval_lower, interval_upper = sorted((first, second))
        lower = interval_lower if lower is None else max(lower, interval_lower)
        upper = interval_upper if upper is None else min(upper, interval_upper)
    if lower is not None and upper is not None and lower >= upper:
        return None
    return (lower, upper)


def solve_all_assignments(points):
    """Use four linear incidence equations, with no convex hull or diagonal test."""
    rhs = vector(QQ, (0, 1, 1, 0))
    squares = set()
    infinite_assignments = 0
    for a, b, c, d in permutations(points):
        # X = r*x + s*y + tx, Y = -s*x + r*y + ty.
        # Require Y(A)=0, X(B)=1, Y(C)=1, X(D)=0.
        incidence = matrix(QQ, (
            (a[1], -a[0], 0, 1),
            (b[0], b[1], 1, 0),
            (c[1], -c[0], 0, 1),
            (d[0], d[1], 1, 0),
        ))
        rank = incidence.rank()
        if incidence.augment(matrix(QQ, 4, 1, rhs)).rank() != rank:
            continue
        require(rank in (3, 4), "consistent square incidence has rank three or four")
        solution = incidence.solve_right(rhs)

        # The remaining coordinates measure position along each prescribed side.
        free_coordinates = matrix(QQ, (
            (a[0], a[1], 1, 0),
            (b[1], -b[0], 0, 1),
            (c[0], c[1], 1, 0),
            (d[1], -d[0], 0, 1),
        ))
        values = free_coordinates * solution
        if rank == 4:
            if all(0 < value < 1 for value in values):
                squares.add(square_from_similarity(solution))
            continue

        direction = incidence.right_kernel().basis()[0]
        slopes = free_coordinates * direction
        if strict_parameter_interval(values, slopes) is not None:
            infinite_assignments += 1

    if infinite_assignments:
        require(not squares, "all feasible assignments describe continuous families")
        return "infinite", squares
    return len(squares), squares


def compare(points):
    points = tuple(tuple(QQ(value) for value in point) for point in points)
    count, squares = solve_all_assignments(points)
    expected = classify(points)
    require(count == expected["count"], ("independent classification mismatch", points,
                                        count, expected["count"]))
    require(count == geometric_count(points), ("geometric extrema mismatch", points))
    if count == 1:
        require(squares == {frozenset(expected["candidate"])},
                ("independent unique square mismatch", points))
    return str(count)


def run():
    grid_counts = Counter()
    grid = tuple(product(range(-1, 3), repeat=2))
    for points in combinations(grid, 4):
        grid_counts[compare(points)] += 1

    rng = Random(20261111)
    random_counts = Counter()
    for _ in range(300):
        points = [(QQ(rng.randrange(-30, 31)) / rng.randrange(1, 12),
                   QQ(rng.randrange(-30, 31)) / rng.randrange(1, 12)) for _ in range(4)]
        random_counts[compare(points)] += 1

    family_counts = Counter()
    values = (QQ(1) / 7, QQ(1) / 2, QQ(6) / 7)
    for b, t in product(values, repeat=2):
        for transform in range(3):
            points = ((0, 0), (b, -t), (1, 0), (b, 1 - t))
            if transform == 1:
                points = tuple((3 * x - 4 * y + 7, 4 * x + 3 * y - 11)
                               for x, y in points)
            if transform == 2:
                points = tuple((-x + 2, y - 3) for x, y in points)
            family_counts[compare(points)] += 1

    special_points = (
        ((0, 0), (0, 0), (0, 0), (0, 0)),
        ((0, 0), (0, 0), (1, 0), (0, 1)),
        ((0, 0), (1, 0), (0, 0), (1, 0)),
        ((0, 0), (2, 0), (3, 1), (0, 2)),
        ((0, 0), (2, 0), (4, 1), (0, 2)),
        ((QQ(1) / 10 ** 100, 0), (1, QQ(1) / 4),
         (QQ(1) / 2, 1), (0, QQ(3) / 4)),
        ((QQ(1) / 2, 0), (1, QQ(1) / 2),
         (QQ(1) / 2, 1), (0, QQ(1) / 2 + QQ(1) / 10 ** 100)),
    )
    special_counts = Counter(compare(points) for points in special_points)
    total = sum(grid_counts.values()) + sum(random_counts.values())
    total += sum(family_counts.values()) + sum(special_counts.values())
    print(json.dumps({
        "valid": True,
        "sage_version": sage_version,
        "method": "all 24 assignments, exact affine similarity incidence systems",
        "geometric_extrema_criterion": "matches every independently solved input",
        "input_count": total,
        "linear_system_count": 24 * total,
        "rational_grid_counts": dict(sorted(grid_counts.items())),
        "random_rational_counts": dict(sorted(random_counts.items())),
        "transformed_family_counts": dict(sorted(family_counts.items())),
        "special_counts": dict(sorted(special_counts.items())),
    }, indent=2))


if __name__ == "__main__":
    run()
