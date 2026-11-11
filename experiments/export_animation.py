"""Export the verified unique-solution example for the Manim animation."""

import hashlib
import json
import os
from pathlib import Path
import tempfile

from sage.all import QQ

from square_reconstruction import construct_square, intersect_lines
from verify_construction import require, verify_replay
from verify_linear_system import solve_all_assignments


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ((0, 1), (3, 0), (4, 2), (1, 4))
SOURCES = (
    "experiments/square_reconstruction.py", "experiments/verify_classification.py",
    "experiments/verify_construction.py", "experiments/verify_linear_system.py",
    "experiments/export_animation.py",
)


def encoded_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    result = construct_square(EXAMPLE)
    verify_replay(result)
    count, squares = solve_all_assignments(EXAMPLE)
    require(count == 1, "the independent solver returns a unique square")
    require(sorted(result["vertices"]) == sorted(next(iter(squares))), "independent vertices")
    points, lines, circles = result["points"], result["lines"], result["circles"]
    require(lines["d"].a == 0 and lines["a"].b == lines["c"].b == 0,
            "the chosen example matches the horizontal/vertical proof captions")
    display_points = {
        "F": intersect_lines(lines["AC"], lines["l"]),
        "H": intersect_lines(lines["d"].parallel(points["A"]), lines["c"]),
        "K": intersect_lines(lines["d"], lines["d"].perpendicular(points["B"])),
    }
    horizontal = display_points["H"][0] - points["A"][0]
    vertical = display_points["K"][1] - points["B"][1]
    side = points["S"][0] - points["P"][0]
    require(horizontal == vertical == side > 0, "proof projection lengths equal the side")
    source_hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                     for name in SOURCES}
    exact = {
        "format_version": 1,
        "input": [list(map(str, point)) for point in EXAMPLE],
        "points": {name: [str(QQ(value)) for value in point] for name, point in points.items()},
        "lines": {name: [str(QQ(value)) for value in (line.a, line.b, line.c)]
                  for name, line in lines.items()},
        "circles": {name: {"center": [str(QQ(value)) for value in circle.center],
                           "radius_squared": str(QQ(circle.radius_squared))}
                    for name, circle in circles.items()},
        "display_points": {name: [str(QQ(value)) for value in point]
                           for name, point in display_points.items()},
        "steps": result["steps"],
        "verified": {"unique_solution": True, "strict_side_interiors": True,
                     "independent_solver_agrees": True, "proof_side_length": str(QQ(side))},
        "source_sha256": source_hashes,
    }
    exact_payload = encoded_json(exact)
    exact_path = ROOT / "experiments/results/animation_example.json"
    atomic_write(exact_path, exact_payload)
    data = {
        "format_version": 1,
        "points": {name: list(map(float, point)) for name, point in points.items()},
        "lines": {name: list(map(float, (line.a, line.b, line.c)))
                  for name, line in lines.items()},
        "circles": {name: {"center": list(map(float, circle.center)),
                           "radius": float(circle.radius_squared.sqrt())}
                    for name, circle in circles.items()},
        "display_points": {name: list(map(float, point)) for name, point in display_points.items()},
        "steps": result["steps"],
        "source_sha256": source_hashes,
        "source_example_sha256": hashlib.sha256(exact_payload).hexdigest(),
    }
    path = ROOT / "animations/reconstruction/geometry.json"
    payload = encoded_json(data)
    atomic_write(path, payload)
    digest = hashlib.sha256(payload).hexdigest()
    atomic_write(path.with_suffix(".sha256"), (digest + "\n").encode("ascii"))
    print(json.dumps({"valid": True, "geometry_sha256": digest,
                      "construction_steps": len(result["steps"]), "independent_solutions": count},
                     indent=2))


if __name__ == "__main__":
    main()
