"""Certify the closed-form square-reconstruction probability over all inputs."""

import argparse
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import tempfile

from sage.all import AA, QQ, SR, Polyhedron, PolynomialRing, log, matrix, pi, sqrt, vector
from sage.version import version as sage_version


DENSITY_COEFFICIENTS = (
    28, 196, 710, 1807, 3562, 5635, 7465, 8193, 7684,
    5883, 3788, 1808, 654, 71, -27, -18, 8, 9,
)
ANTIDERIVATIVE_COEFFICIENTS = (
    -284, -3241, -11869, -28723, -51789, -73154, -84326,
    -78515, -60037, -36027, -16707, -5088, -780, 108,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def closed_form():
    return 4 * log(SR(2)) / 7 - QQ(16) / 63 - sqrt(SR(3)) * pi / 270 - 41 * pi / 6720


def density(parameter):
    ring = PolynomialRing(QQ, "t")
    polynomial = ring(DENSITY_COEFFICIENTS)
    return polynomial(parameter) / (
        210 * (1 + parameter) ** 4 * (1 + parameter ** 2) ** 3
        * (1 + parameter + parameter ** 2) ** 3
    )


def linear_rows(parameter, base_ring=QQ):
    ring = PolynomialRing(base_ring, names=("x", "y", "l", "a", "b", "c", "d"))
    x, y, length, a, b, c, d = ring.gens()
    coordinates = (
        x + a, y + parameter * a,
        x + length - parameter * b, y + parameter * length + b,
        x + c - parameter * length, y + parameter * c + length,
        x - parameter * d, y + d,
    )
    forms = []
    for coordinate in coordinates:
        forms.extend((coordinate, 1 - coordinate))
    for position in (a, b, c, d):
        forms.extend((position, length - position))
    forms.append(a - b - c + d)
    return [[form.constant_coefficient()]
            + [form.monomial_coefficient(variable) for variable in ring.gens()]
            for form in forms]


def exact_polytope_density(parameter):
    polytope = Polyhedron(ieqs=linear_rows(parameter))
    vertices = [vector(QQ, vertex) for vertex in polytope.vertex_generator()]
    moment = QQ(0)
    for simplex in polytope.triangulate(engine="internal"):
        corners = [vertices[index] for index in simplex]
        volume = abs(matrix([point - corners[0] for point in corners[1:]]).det()) / 5040
        average = sum(point[3] - point[4] - point[5] + point[6] for point in corners) / 8
        moment += volume * average
    return 96 * (1 + parameter ** 2) ** 2 * moment


def verify_parameterization():
    ring = PolynomialRing(QQ, names=("x", "y", "l", "t", "a", "b", "c", "d"))
    x, y, length, t, a, b, c, d = ring.gens()
    points = ((x + a, y + t * a),
              (x + length - t * b, y + t * length + b),
              (x + c - t * length, y + t * c + length),
              (x - t * d, y + d))
    coordinates = [coordinate for point in points for coordinate in point]
    jacobian = matrix(ring, [[coordinate.derivative(variable) for variable in ring.gens()]
                            for coordinate in coordinates]).det()
    require(jacobian == (a - b - c + d) * (1 + t ** 2) ** 2, "Jacobian identity")

    substitution = {x: y + t * length, y: 1 - x - length,
                    a: b, b: length - c, c: d, d: length - a}
    transformed = [tuple(coordinate.subs(substitution) for coordinate in point)
                   for point in points]
    rotated_cycle = [(point[1], 1 - point[0]) for point in points[1:] + points[:1]]
    require(transformed == rotated_cycle, "quarter-turn and cyclic relabeling symmetry")
    require((a - b - c + d).subs(substitution) == -(a - b - c + d),
            "symmetry interchanges the two Jacobian signs")
    fixed_parameter_variables = (x, y, length, a, b, c, d)
    transformed_variables = (y + t * length, 1 - x - length, length,
                             b, length - c, d, length - a)
    symmetry_determinant = matrix(ring, [
        [expression.derivative(variable) for variable in fixed_parameter_variables]
        for expression in transformed_variables
    ]).det()
    require(symmetry_determinant in (1, -1), "symmetry preserves seven-dimensional measure")


def verify_parametric_vertices():
    ring = PolynomialRing(QQ, "t")
    t = ring.gen()
    field = ring.fraction_field()
    rows = linear_rows(field(t), field)
    reference = QQ(1) / 2
    reference_rows = [[entry(reference) for entry in row] for row in rows]
    polytope = Polyhedron(ieqs=reference_rows)
    require(polytope.dim() == 7, "full-dimensional reference polytope")
    vertices = [vector(QQ, vertex) for vertex in polytope.vertex_generator()]
    center = sum(vertices) / len(vertices)
    require(all(row[0] + vector(row[1:]) * center > 0 for row in reference_rows),
            "strictly interior polar origin")
    checked_factors = set()
    check_count = 0

    def check_nonzero(polynomial):
        nonlocal check_count
        require(polynomial != 0, "nonzero certificate polynomial")
        for factor, _ in polynomial.factor():
            factor = factor.monic()
            if factor not in checked_factors:
                require(not any(0 < root < 1 for root in factor.roots(AA, multiplicities=False)),
                        "certificate factor has no root in the open parameter interval")
                checked_factors.add(factor)
        check_count += 1

    active_sets = []
    symbolic_vertices = []
    denominator = ring(1)
    for vertex in vertices:
        active = [index for index, row in enumerate(reference_rows)
                  if row[0] + vector(row[1:]) * vertex == 0]
        active_sets.append(active)
        normals = matrix(QQ, [reference_rows[index][1:] for index in active])
        basis = [active[index] for index in normals.transpose().pivots()]
        coefficients = matrix(field, [rows[index][1:] for index in basis])
        check_nonzero(coefficients.det().numerator())
        symbolic = coefficients.solve_right(vector(field, [-rows[index][0] for index in basis]))
        symbolic_vertices.append(symbolic)
        for value in symbolic:
            denominator = denominator.lcm(value.denominator())
        for index, row in enumerate(rows):
            slack = row[0] + vector(field, row[1:]) * symbolic
            if index in active:
                require(slack == 0, "active inequality stays an equality")
            else:
                require(slack(reference) > 0, "inactive inequality is strictly positive")
                check_nonzero(slack.numerator())
                check_nonzero(slack.denominator())

    # Use one global pulling order on the polar boundary. Its triangulations
    # agree on shared faces, so coning them gives a continuous complete fan.
    polar_points = {}
    for index, row in enumerate(reference_rows):
        slack = row[0] + vector(row[1:]) * center
        point = tuple(-entry / slack for entry in row[1:])
        require(point not in polar_points, "distinct polar constraint points")
        polar_points[point] = index
    polar = Polyhedron(vertices=list(polar_points))
    extreme_rows = {polar_points[tuple(vertex)] for vertex in polar.vertex_generator()}
    polar_facets = {frozenset(index for index in active if index in extreme_rows)
                    for active in active_sets}

    @lru_cache(maxsize=None)
    def pulling(face):
        if len(face) == 1:
            return (tuple(face),)
        intersections = {face & facet for facet in polar_facets}
        proper = sorted((part for part in intersections if part and part != face),
                        key=lambda part: (-len(part), tuple(sorted(part))))
        facets = []
        for part in proper:
            if not any(part < larger for larger in facets):
                facets.append(part)
        apex = min(face)
        simplices = []
        for facet in facets:
            if apex not in facet:
                simplices.extend((apex,) + simplex for simplex in pulling(facet))
        return tuple(simplices)

    normal_bases = {tuple(sorted(simplex)) for facet in polar_facets
                    for simplex in pulling(facet)}
    require(all(len(basis) == 7 for basis in normal_bases), "full-dimensional normal cones")
    for basis in normal_bases:
        determinant = matrix(ring, [[ring(-entry) for entry in rows[index][1:]]
                                    for index in basis]).det()
        check_nonzero(determinant)

    scaled_degree = max(ring(denominator * value).degree()
                        for vertex in symbolic_vertices for value in vertex)
    expected_denominator = (t + 1) * (t ** 2 + 1) * (t ** 2 + t + 1)
    require(denominator.monic() == expected_denominator, "common symbolic vertex denominator")
    require(scaled_degree == 5, "scaled vertex degree")
    return {
        "inequality_count": len(rows),
        "vertex_count": len(vertices),
        "normal_cone_basis_count": len(normal_bases),
        "univariate_nonvanishing_check_count": check_count,
        "checked_factors": sorted(map(str, checked_factors)),
        "common_vertex_denominator": str(denominator),
        "scaled_vertex_degree": int(scaled_degree),
        "density_numerator_degree_bound": int(8 * scaled_degree + 4),
    }, denominator


def verify_density(certificate, denominator):
    ring = denominator.parent()
    t = ring.gen()
    field = ring.fraction_field()
    expression = density(field(t))
    scaled = ring(expression * denominator ** 8)
    bound = certificate["density_numerator_degree_bound"]
    require(scaled.degree() <= bound, "proposed density obeys certified degree bound")
    checks = []
    for index in range(1, bound + 2):
        parameter = QQ(index) / (bound + 2)
        actual = exact_polytope_density(parameter)
        require(actual == density(parameter), "exact rational polytope moment agrees with density")
        checks.append({"parameter": str(parameter), "density": str(actual)})
    return checks


def verify_antiderivative():
    ring = PolynomialRing(QQ, "t")
    t = ring.gen()
    field = ring.fraction_field()
    rational_part = field(ring(ANTIDERIVATIVE_COEFFICIENTS) / (
        5040 * (1 + t) ** 3 * (1 + t ** 2) ** 2 * (1 + t + t ** 2) ** 2
    ))
    elementary_part = (QQ(58) / (105 * (1 + t))
                       + (QQ(4) * t / 105 - QQ(41) / 1680) / (1 + t ** 2)
                       - QQ(1) / (30 * (1 + t + t ** 2)))
    require(rational_part.derivative() + elementary_part == density(field(t)),
            "rational antiderivative reduction")
    require(rational_part(1) - rational_part(0) == -QQ(16) / 63,
            "rational endpoint contribution")
    integrated = (-SR(16) / 63 + SR(4) * log(SR(2)) / 7
                  - 41 * pi / 6720 - pi / (90 * sqrt(SR(3))))
    require((integrated - closed_form()).simplify_full() == 0, "closed-form integral")
    return str(rational_part)


def verify_convex_probability():
    ring = PolynomialRing(QQ, names=("length", "fraction"))
    length, fraction = ring.gens()
    integrand = 6 * length ** 2 * (1 - length) * (2 - fraction + fraction ** 2) / 12
    expected_area = integrand.integral(length).subs({length: 1})
    expected_area = expected_area.integral(fraction).subs({fraction: 1})
    require(expected_area == QQ(11) / 144, "expected triangle area")
    require(1 - 4 * expected_area == QQ(25) / 36, "strict convexity probability")


def compare_monte_carlo(path, probabilities):
    simulation = json.loads(path.read_text(encoding="utf-8"))
    trials = simulation["sample_count"]
    table = simulation["all_input_probability_table"]
    require(sum(table[name]["count"] for name in probabilities) == trials,
            "Monte Carlo cases partition all samples")
    chi_squared = 0.0
    maximum_standardized_deviation = 0.0
    zero_probability_observations = 0
    for name, probability in probabilities.items():
        observed = table[name]["count"]
        exact = float(probability.n(100))
        if exact == 0:
            zero_probability_observations += observed
            continue
        difference = observed - trials * exact
        chi_squared += difference ** 2 / (trials * exact)
        standardized = abs(difference) / math.sqrt(trials * exact * (1 - exact))
        maximum_standardized_deviation = max(maximum_standardized_deviation, standardized)
    return {
        "sample_count": trials,
        "seed": simulation["seed"],
        "positive_probability_case_count": 3,
        "pearson_chi_squared": chi_squared,
        "degrees_of_freedom": 2,
        "asymptotic_tail_probability": math.exp(-chi_squared / 2),
        "maximum_marginal_standardized_deviation": maximum_standardized_deviation,
        "zero_probability_case_observations": zero_probability_observations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", type=Path)
    parser.add_argument("--monte-carlo", type=Path)
    args = parser.parse_args()
    verify_parameterization()
    verify_convex_probability()
    certificate, denominator = verify_parametric_vertices()
    checks = verify_density(certificate, denominator)
    rational_antiderivative = verify_antiderivative()
    unique = closed_form()
    probabilities = {
        "degenerate": SR(0),
        "nonconvex_no_solution": SR(QQ(11) / 36),
        "convex_unique_solution": unique,
        "convex_general_no_solution": QQ(25) / 36 - unique,
        "convex_perpendicular_unequal_no_solution": SR(0),
        "convex_infinite_solutions": SR(0),
    }
    require(sum(probabilities.values()).simplify_full() == 1, "complete probability partition")
    report = {
        "valid": True,
        "sage_version": sage_version,
        "model": "four iid uniform points in [0,1]^2, all inputs included",
        "unique_closed_form": "4*log(2)/7 - 16/63 - sqrt(3)*pi/270 - 41*pi/6720",
        "probabilities": {name: {"exact": str(value), "decimal": str(value.n(100))}
                          for name, value in probabilities.items()},
        "conditional_unique_decimal": str((36 * unique / 25).n(100)),
        "total_no_solution_decimal": str((1 - unique).n(100)),
        "density_coefficients_ascending": list(DENSITY_COEFFICIENTS),
        "antiderivative_coefficients_ascending": list(ANTIDERIVATIVE_COEFFICIENTS),
        "rational_antiderivative": rational_antiderivative,
        "parametric_polytope_certificate": certificate,
        "exact_density_checks": checks,
    }
    if args.monte_carlo is not None:
        report["monte_carlo_validation"] = compare_monte_carlo(args.monte_carlo, probabilities)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write is not None:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                         dir=args.write.parent, suffix=".tmp") as temporary:
            temporary.write(encoded)
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, args.write)
        finally:
            temporary_path.unlink(missing_ok=True)
    print(encoded, end="")


if __name__ == "__main__":
    main()
