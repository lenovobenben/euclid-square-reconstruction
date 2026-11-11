"""Monte Carlo probability for four iid uniform points in the unit square."""

import argparse
import json
import math
import os
from pathlib import Path
from statistics import NormalDist
import tempfile
from itertools import combinations, product

import numpy as np
from sage.all import QQ

from analytic_probability import closed_form
from verify_classification import classify, cross, dot, subtract


CASE_NAMES = (
    "degenerate", "nonconvex_no_solution", "convex_unique_solution",
    "convex_general_no_solution", "convex_perpendicular_unequal_no_solution",
    "convex_infinite_solutions",
)


def classify_batch_cases(points):
    """Partition a batch into all six geometric cases, with strict convexity."""
    relative = points - points.mean(axis=1, keepdims=True)
    angles = np.arctan2(relative[:, :, 1], relative[:, :, 0])
    order = np.argsort(angles, axis=1)
    ordered = np.take_along_axis(points, order[:, :, None], axis=1)
    edges = np.roll(ordered, -1, axis=1) - ordered
    next_edges = np.roll(edges, -1, axis=1)
    turns = edges[:, :, 0] * next_edges[:, :, 1] - edges[:, :, 1] * next_edges[:, :, 0]
    convex = (turns > 0).all(axis=1)
    degenerate = (turns == 0).any(axis=1)

    a, b, c, d = (ordered[:, index] for index in range(4))
    p, q = c - a, d - b
    vertical = q + np.stack((p[:, 1], -p[:, 0]), axis=1)
    horizontal = np.stack((vertical[:, 1], -vertical[:, 0]), axis=1)
    relative = ordered - a[:, None, :]
    heights = (relative * vertical[:, None, :]).sum(axis=2)
    positions = (relative * horizontal[:, None, :]).sum(axis=2)
    ac_lower = np.minimum(heights[:, 0], heights[:, 2])
    ac_upper = np.maximum(heights[:, 0], heights[:, 2])
    bd_lower = np.minimum(positions[:, 1], positions[:, 3])
    bd_upper = np.maximum(positions[:, 1], positions[:, 3])
    vertical_extrema = ((heights[:, (1, 3)] > ac_lower[:, None])
                        & (heights[:, (1, 3)] < ac_upper[:, None])).all(axis=1)
    horizontal_extrema = ((positions[:, (0, 2)] > bd_lower[:, None])
                          & (positions[:, (0, 2)] < bd_upper[:, None])).all(axis=1)
    infinite = convex & (vertical == 0).all(axis=1)
    perpendicular = convex & ((p * q).sum(axis=1) == 0) & ~infinite
    unique = convex & vertical_extrema & horizontal_extrema & ~infinite & ~perpendicular
    return {
        "strictly_convex": convex,
        "degenerate": degenerate,
        "nonconvex_no_solution": ~convex & ~degenerate,
        "convex_unique_solution": unique,
        "convex_general_no_solution": convex & ~unique & ~infinite & ~perpendicular,
        "convex_perpendicular_unequal_no_solution": perpendicular,
        "convex_infinite_solutions": infinite,
    }


def classify_batch(points):
    """Return the original two-mask interface for callers of this module."""
    cases = classify_batch_cases(points)
    return cases["strictly_convex"], cases["convex_unique_solution"]


def verify_exact(points):
    """Compare the floating batch decisions with the exact dyadic input values."""
    def exact_coordinate(value):
        numerator, denominator = float(value).as_integer_ratio()
        return QQ(numerator) / denominator

    cases = classify_batch_cases(points)
    for index, coordinates in enumerate(points):
        exact_points = [tuple(exact_coordinate(value) for value in point)
                        for point in coordinates]
        result = classify(exact_points)
        hull = result["ordered_points"]
        if bool(cases["strictly_convex"][index]) != (len(hull) == 4):
            raise AssertionError("batch convexity differs from exact convexity")
        degenerate = any(cross(subtract(b, a), subtract(c, a)) == 0
                         for a, b, c in combinations(exact_points, 3))
        if degenerate:
            expected = "degenerate"
        elif len(hull) != 4:
            expected = "nonconvex_no_solution"
        elif result["count"] == "infinite":
            expected = "convex_infinite_solutions"
        elif dot(subtract(hull[2], hull[0]), subtract(hull[3], hull[1])) == 0:
            expected = "convex_perpendicular_unequal_no_solution"
        elif result["count"] == 1:
            expected = "convex_unique_solution"
        else:
            expected = "convex_general_no_solution"
        if not all(bool(cases[name][index]) == (name == expected) for name in CASE_NAMES):
            raise AssertionError("batch case differs from the exact geometric partition")


def wilson_interval(successes, trials):
    if trials == 0:
        return None
    z = NormalDist().inv_cdf(0.975)
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    half_width = z * math.sqrt(proportion * (1 - proportion) / trials
                              + z * z / (4 * trials * trials)) / denominator
    lower = 0.0 if successes == 0 else max(0.0, center - half_width)
    upper = 1.0 if successes == trials else min(1.0, center + half_width)
    return [lower, upper]


def estimate(samples, batch_size, seed):
    grid = tuple(product((0.0, 0.25, 0.5, 0.75), repeat=2))
    grid_inputs = np.array(tuple(combinations(grid, 4)))
    verify_exact(grid_inputs)
    rng = np.random.default_rng(seed)
    convex_count = 0
    unique_count = 0
    case_counts = {name: 0 for name in CASE_NAMES}
    verified_count = 0
    generated_count = 0
    while generated_count < samples:
        size = min(batch_size, samples - generated_count)
        points = rng.random((size, 4, 2))
        check_size = min(size, 1024 - verified_count)
        if check_size > 0:
            verify_exact(points[:check_size])
            verified_count += check_size
        cases = classify_batch_cases(points)
        convex_count += int(cases["strictly_convex"].sum())
        unique_count += int(cases["convex_unique_solution"].sum())
        for name in CASE_NAMES:
            case_counts[name] += int(cases[name].sum())
        generated_count += size
    probability = unique_count / convex_count if convex_count else None
    interval = wilson_interval(unique_count, convex_count)
    unique_exact = closed_form()
    theoretical = {
        "degenerate": ("0", 0.0),
        "nonconvex_no_solution": ("11/36", float(QQ(11) / 36)),
        "convex_unique_solution": ("q", float(unique_exact.n(53))),
        "convex_general_no_solution": ("25/36-q", float((QQ(25) / 36 - unique_exact).n(53))),
        "convex_perpendicular_unequal_no_solution": ("0", 0.0),
        "convex_infinite_solutions": ("0", 0.0),
    }
    table = {}
    for name in CASE_NAMES:
        exact, analytic = theoretical[name]
        observed = case_counts[name] / samples
        standard_error = math.sqrt(analytic * (1 - analytic) / samples)
        table[name] = {
            "count": case_counts[name], "estimate": observed,
            "analytic_expression": exact, "analytic_probability": analytic,
            "wilson_95": wilson_interval(case_counts[name], samples),
            "deviation_in_standard_errors": (observed - analytic) / standard_error
                                            if standard_error else None,
        }
    if sum(case_counts.values()) != samples:
        raise AssertionError("sample cases must form a complete disjoint partition")
    return {
        "model": "four iid uniform points in [0,1]^2, all inputs included",
        "method": "Monte Carlo with strict geometric-extrema classification",
        "numpy_version": np.__version__,
        "bit_generator": type(rng.bit_generator).__name__,
        "seed": seed,
        "sample_count": samples,
        "unique_closed_form": "q=4*log(2)/7-16/63-sqrt(3)*pi/270-41*pi/6720",
        "all_input_probability_table": table,
        "strictly_convex_count": convex_count,
        "unique_solution_count": unique_count,
        "convex_no_unique_solution_count": convex_count - unique_count,
        "conditional_unique_estimate": probability,
        "conditional_no_solution_estimate": 1 - probability if probability is not None else None,
        "conditional_unique_wilson_95": interval,
        "conditional_no_solution_wilson_95": [1 - interval[1], 1 - interval[0]]
                                               if interval is not None else None,
        "unconditional_unique_estimate": unique_count / samples,
        "unconditional_convex_estimate": convex_count / samples,
        "unconditional_convex_exact": "25/36",
        "exact_cross_checked_sample_count": verified_count,
        "exact_grid_cross_checked_sample_count": len(grid_inputs),
        "infinite_solution_probability": "0 under the continuous model",
    }


def positive_integer(value):
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("the value must be positive")
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=positive_integer, default=1_000_000)
    parser.add_argument("--batch-size", type=positive_integer, default=100_000)
    parser.add_argument("--seed", type=int, default=20261111)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()
    report = estimate(args.samples, args.batch_size, args.seed)
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
