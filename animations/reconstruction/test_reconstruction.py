"""Check the displayed construction order, geometry, labels, and output records."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from manim import Text, tempconfig

from reconstruction import LABEL_OFFSETS, PLOT_BOUNDS, SquareReconstruction, load_geometry


class AnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.enterClassContext(tempconfig({
            "media_dir": temporary.name, "dry_run": True, "skip_animations": True,
            "progress_bar": "none", "verbosity": "ERROR", "frame_rate": 30,
            "pixel_width": 1280, "pixel_height": 720,
        }))
        cls.scene = SquareReconstruction()
        cls.text_bounds = []
        original_play = cls.scene.play

        def observe(*args, **kwargs):
            result = original_play(*args, **kwargs)
            for root in cls.scene.mobjects:
                for item in root.get_family():
                    if isinstance(item, Text):
                        cls.text_bounds.append((item.text, item.get_left()[0], item.get_right()[0],
                                                item.get_bottom()[1], item.get_top()[1]))
            return result

        with patch.object(cls.scene, "play", new=observe):
            cls.scene.render()

    def test_documented_sequence_and_parents(self):
        names = [event["object"] for event in self.scene.audit]
        expected = ["AC", "l", "omega", "E0", "E1", "E", "d", "a", "c", "b", "P", "Q", "R", "S"]
        positions = [names.index(name) for name in expected]
        self.assertEqual(positions, sorted(positions))
        known = set("ABCD")
        for event in self.scene.audit:
            self.assertTrue(set(event["parents"]).issubset(known), event)
            known.add(event["object"])
        self.assertLess(names.index("target_square"), names.index("proof_guides"))
        self.assertEqual(len(self.scene.data["steps"]), 13)

    def test_views_and_complete_circle(self):
        data, _ = load_geometry()
        for view in (self.scene.overview, self.scene.detail):
            for name, point_names in (("AC", ("A", "C")), ("l", ("B", "E0", "E1")),
                                       ("d", ("D", "E", "P", "S")), ("a", ("A", "P", "Q")),
                                       ("b", ("B", "Q", "R")), ("c", ("C", "R", "S"))):
                line = view.line(data["lines"][name])
                direction = line.get_end()[:2] - line.get_start()[:2]
                for point_name in point_names:
                    offset = view.at(data["points"][point_name])[:2] - line.get_start()[:2]
                    residual = abs(direction[0] * offset[1] - direction[1] * offset[0])
                    self.assertLess(residual / np.linalg.norm(direction), 1e-9)
        center = self.scene.overview.at(data["circles"]["omega"]["center"])
        radius = data["circles"]["omega"]["radius"] * self.scene.overview.scale
        left, right, bottom, top = PLOT_BOUNDS
        self.assertGreater(center[0] - radius, left)
        self.assertLess(center[0] + radius, right)
        self.assertGreater(center[1] - radius, bottom)
        self.assertLess(center[1] + radius, top)

    def test_labels_and_text_bounds(self):
        points = self.scene.data["points"]
        for name in "ABCDEPQRS":
            group = self.scene.objects[name]
            np.testing.assert_allclose(group[0].get_center(), self.scene.detail.at(points[name]), atol=1e-9)
            own_distance = np.linalg.norm(group[1].get_center() - group[0].get_center())
            for other in "ABCDEPQRS":
                if name != other:
                    other_distance = np.linalg.norm(group[1].get_center() - self.scene.detail.at(points[other]))
                    self.assertLess(own_distance, other_distance, (name, other))
            self.assertIn(name, LABEL_OFFSETS)
        for content, left, right, bottom, top in self.text_bounds:
            with self.subTest(content=content):
                self.assertGreaterEqual(left, -7.1)
                self.assertLessEqual(right, 7.1)
                self.assertGreaterEqual(bottom, -3.95)
                self.assertLessEqual(top, 3.95)

    def test_unfilled_shapes_and_proof_lengths(self):
        self.assertEqual(self.scene.objects["omega"].get_fill_opacity(), 0)
        self.assertEqual(self.scene.objects["target_square"].get_fill_opacity(), 0)
        data = self.scene.data
        a, b, c, e = (np.array(data["points"][name]) for name in "ABCE")
        h, k = (np.array(data["display_points"][name]) for name in ("H", "K"))
        self.assertAlmostEqual(np.dot(c - a, e - b), 0)
        self.assertAlmostEqual(np.linalg.norm(c - a), np.linalg.norm(e - b))
        self.assertAlmostEqual(np.linalg.norm(h - a), 4)
        self.assertAlmostEqual(np.linalg.norm(k - b), 4)

    def test_point_labels_clear_supporting_lines(self):
        checks = {"A": ("AC", "a"), "B": ("l", "b"), "C": ("AC", "c"),
                  "D": ("d",), "E": ("l", "d"), "P": ("a", "d"),
                  "Q": ("a", "b"), "R": ("c", "b"), "S": ("c", "d")}
        for name, line_names in checks.items():
            label = self.scene.objects[name][1]
            for line_name in line_names:
                line = self.scene.detail.line(self.scene.data["lines"][line_name])
                direction = line.get_end()[:2] - line.get_start()[:2]
                normal = np.array([-direction[1], direction[0]]) / np.linalg.norm(direction)
                distance = abs(np.dot(normal, label.get_center()[:2] - line.get_start()[:2]))
                half_extent = abs(normal[0]) * label.width / 2 + abs(normal[1]) * label.height / 2
                self.assertGreater(distance - half_extent, 0.025, (name, line_name))

    def test_timeline_per_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = []
            for width, height, fps in ((1280, 720, 30), (3840, 2160, 60)):
                movie = Path(temporary) / f"{height}p{fps}" / "SquareReconstruction.mp4"
                movie.parent.mkdir()
                with tempconfig({"pixel_width": width, "pixel_height": height, "frame_rate": fps}):
                    with patch.object(self.scene.renderer.file_writer, "movie_file_path", str(movie), create=True):
                        self.scene.write_timeline()
                path = movie.with_suffix(".timeline.json")
                paths.append(path)
                report = json.loads(path.read_text("utf-8"))
                self.assertEqual(report["resolution"], [width, height])
                self.assertEqual(report["frame_rate"], fps)
                self.assertEqual(report["geometry_sha256"], self.scene.geometry_hash)
            self.assertNotEqual(*paths)


if __name__ == "__main__":
    unittest.main()
