"""The unique-solution cross construction, using exact verified geometry."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
from manim import (
    Circle, Create, DashedLine, Dot, FadeIn, FadeOut, Indicate, Line,
    Polygon, Scene, Text, Transform, VGroup, VMobject, config,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONT = "Noto Sans CJK SC"
BACKGROUND = "#07101F"
FOREGROUND = "#E8F0F7"
MUTED = "#8397A8"
INPUT = "#F45BFF"
CURRENT = "#FFC857"
AUXILIARY = "#8AC6D9"
RESULT = "#5DE2A5"
PLOT_BOUNDS = (-6.35, 1.05, -2.95, 2.72)
LABEL_OFFSETS = {
    "A": (-0.31, 0.22), "B": (0.36, -0.22), "C": (0.31, -0.24),
    "D": (-0.08, 0.29), "E": (0.18, 0.29), "E0": (0.22, 0.24),
    "P": (-0.27, 0.26), "Q": (-0.27, -0.26),
    "R": (0.27, -0.26), "S": (0.27, 0.26),
}


def load_geometry():
    payload = (HERE / "geometry.json").read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != (HERE / "geometry.sha256").read_text("ascii").strip():
        raise ArithmeticError("the animation geometry digest does not match")
    data = json.loads(payload)
    exact = (ROOT / "experiments/results/animation_example.json").read_bytes()
    if hashlib.sha256(exact).hexdigest() != data["source_example_sha256"]:
        raise ArithmeticError("the exact animation example changed")
    certificate = json.loads(exact)
    if not all(certificate["verified"][name] for name in (
        "unique_solution", "strict_side_interiors", "independent_solver_agrees"
    )):
        raise ArithmeticError("the animation example must pass all exact checks")
    for name, expected in data["source_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ArithmeticError(f"source changed since geometric verification: {name}")
    return data, digest


@dataclass(frozen=True)
class View:
    origin: tuple
    offset: tuple
    scale: float

    def at(self, point):
        position = (np.array(point) - np.array(self.origin)) * self.scale + np.array(self.offset)
        return np.array([position[0], position[1], 0.0])

    def line(self, coefficients, color=CURRENT, opacity=0.8):
        a, b, c = coefficients
        screen_left, screen_right, screen_bottom, screen_top = PLOT_BOUNDS
        left = (screen_left - self.offset[0]) / self.scale + self.origin[0]
        right = (screen_right - self.offset[0]) / self.scale + self.origin[0]
        bottom = (screen_bottom - self.offset[1]) / self.scale + self.origin[1]
        top = (screen_top - self.offset[1]) / self.scale + self.origin[1]
        candidates = []
        if abs(b) > 1e-14:
            for x in (left, right):
                y = -(a * x + c) / b
                if bottom - 1e-10 <= y <= top + 1e-10:
                    candidates.append((x, y))
        if abs(a) > 1e-14:
            for y in (bottom, top):
                x = -(b * y + c) / a
                if left - 1e-10 <= x <= right + 1e-10:
                    candidates.append((x, y))
        if len(candidates) < 2:
            raise ArithmeticError("a displayed construction line misses the viewport")
        first, second = max(((p, q) for p in candidates for q in candidates),
                            key=lambda pair: np.linalg.norm(np.array(pair[0]) - pair[1]))
        return Line(self.at(first), self.at(second), color=color,
                    stroke_width=1.5, stroke_opacity=opacity)


class SquareReconstruction(Scene):
    def text(self, content, size=25, color=FOREGROUND, max_width=12.7):
        result = Text(content, font=FONT, font_size=size, color=color, line_spacing=1.2)
        if result.width > max_width:
            result.scale_to_fit_width(max_width)
        return result

    def stage(self, title):
        self.sections.append({"title": title, "start_seconds": round(float(self.time), 6)})
        heading = self.text(title, 32, max_width=9.5)
        heading.move_to([-6.35, 3.47, 0], aligned_edge=np.array([-1, 0, 0]))
        if hasattr(self, "heading"):
            self.play(FadeOut(self.heading), FadeIn(heading), run_time=0.35)
        else:
            self.play(FadeIn(heading), run_time=0.35)
        self.heading = heading

    def caption(self, content, color=CURRENT):
        replacement = self.text(content, 24, color).move_to([0, -3.48, 0])
        if hasattr(self, "caption_object"):
            self.remove(self.caption_object)
        self.caption_object = replacement
        self.add(replacement)

    def panel(self, title, lines, color=FOREGROUND):
        heading = self.text(title, 28, color, 4.6).move_to([4.0, 2.03, 0])
        body = [self.text(line, 24, FOREGROUND, 4.6).move_to([4.0, 1.05 - index * 0.8, 0])
                for index, line in enumerate(lines)]
        replacement = VGroup(heading, *body)
        if hasattr(self, "panel_object"):
            self.play(FadeOut(self.panel_object), FadeIn(replacement), run_time=0.5)
        else:
            self.play(FadeIn(replacement), run_time=0.5)
        self.panel_object = replacement

    def reveal(self, name, parents=None):
        parents = self.definitions[name]["inputs"] if parents is None else parents
        if any(parent not in self.available for parent in parents):
            raise ArithmeticError(f"construction object appeared before its parents: {name}")
        self.available.add(name)
        self.audit.append({"object": name, "parents": parents,
                           "seconds": round(float(self.time), 6)})

    def draw(self, name, mobject, duration=0.9, parents=None):
        self.reveal(name, parents)
        self.objects[name] = mobject
        self.play(Create(mobject), run_time=duration)
        return mobject

    def point_object(self, name, view, label=None, color=INPUT):
        point = view.at(self.data["points"][name])
        dot = Dot(point, radius=0.043, color=color).set_z_index(5)
        group = VGroup(dot)
        if label != "":
            content = name if label is None else label
            offset = LABEL_OFFSETS[name]
            tag = self.text(content, 22, color)
            tag.move_to(point + np.array([*offset, 0])).set_z_index(6)
            group.add(tag)
        return group

    def mark(self, name, label=None, color=INPUT, given=False):
        if not given:
            self.reveal(name)
        group = self.point_object(name, self.view, label, color)
        self.objects[name] = group
        self.play(FadeIn(group), run_time=0.35)
        return group

    def segment(self, first, second, color=CURRENT, width=2):
        return Line(self.view.at(self.data["points"][first]),
                    self.view.at(self.data["points"][second]), color=color, stroke_width=width)

    def right_angle(self, view):
        at = view.at(self.data["display_points"]["F"])
        direction = np.array(self.data["points"]["C"]) - self.data["points"]["A"]
        direction = np.array([*direction, 0.0]) / np.linalg.norm(direction)
        normal = np.array([-direction[1], direction[0], 0.0])
        size = 0.16
        marker = VMobject(color=AUXILIARY, stroke_width=1.2)
        marker.set_points_as_corners([at + size * direction,
                                     at + size * (direction + normal), at + size * normal])
        return marker

    def construct(self):
        config.background_color = BACKGROUND
        self.data, self.geometry_hash = load_geometry()
        self.definitions = {name: step for step in self.data["steps"] for name in step["outputs"]}
        self.objects = {}
        self.audit, self.sections = [], []
        self.available = set("ABCD")
        self.overview = View((3, 0), (-2.35, -0.15), 0.62)
        self.detail = View((2, 2), (-2.3, -0.2), 1.16)
        self.view = self.overview
        self.add(Line([-6.5, 3.03, 0], [6.5, 3.03, 0], color=MUTED, stroke_width=0.6))
        self.add(self.text("唯一解情形", 19, MUTED).move_to([5.55, 3.47, 0]))
        self.input_points()
        self.cross_and_circle()
        self.select_and_zoom()
        self.restore_sides()
        self.restore_vertices()
        self.explain_direction()
        self.finish_square()
        if not config.dry_run and config.write_to_movie:
            self.write_timeline()

    def input_points(self):
        self.stage("四个边上点恢复正方形")
        self.caption("给定四点分别在四条边内部，已知正方形有唯一解")
        for name in "ABCD":
            self.mark(name, given=True)
        self.wait(2.6)

    def cross_and_circle(self):
        self.stage("连接 A、C")
        self.caption("连接 A、C，取得线段 AC")
        self.draw("AC", self.view.line(self.data["lines"]["AC"]), 1)
        self.wait(1.3)
        self.stage("过 B 作 AC 的垂线")
        self.caption("过 B 作直线 AC 的垂线")
        self.draw("l", self.view.line(self.data["lines"]["l"]), 1)
        self.draw("right_angle", self.right_angle(self.view), 0.4, ["AC", "l"])
        self.wait(1.2)
        self.stage("以 B 为圆心作圆")
        self.caption("将 AC 的长度转移到 B，以 B 为圆心作圆")
        self.play(Indicate(self.objects["AC"], color=CURRENT), run_time=0.7)
        circle = self.data["circles"]["omega"]
        mobject = Circle(radius=circle["radius"] * self.view.scale, color=CURRENT,
                         stroke_width=1.6, stroke_opacity=0.8, fill_opacity=0)
        mobject.move_to(self.view.at(circle["center"]))
        self.draw("omega", mobject, 1.8)
        self.wait(1.1)

    def select_and_zoom(self):
        self.stage("选取异侧交点 E")
        self.caption("取与 B 位于直线 AC 异侧的交点 E")
        self.mark("E0", "E′", MUTED)
        self.mark("E1", "", CURRENT)
        if not np.allclose(self.data["points"]["E"], self.data["points"]["E1"], atol=1e-12):
            raise ArithmeticError("the selected example must name its chosen point E1")
        self.reveal("E")
        self.objects["E"] = self.objects["E1"]
        label = self.point_object("E", self.view, color=RESULT)[1]
        self.objects["E"].add(label)
        self.play(self.objects["E"][0].animate.set_color(RESULT), FadeIn(label), run_time=0.6)
        self.draw("BE", self.segment("B", "E", RESULT), 0.7, ["B", "E", "l"])
        self.panel("十字架", ["BE ⟂ AC", "BE = AC"], AUXILIARY)
        self.wait(2.5)
        self.play(FadeOut(self.objects["omega"]), FadeOut(self.objects["E0"]), run_time=0.6)

        transformations = []
        for name in ("A", "B", "C", "D", "E"):
            replacement = self.point_object(name, self.detail, color=RESULT if name == "E" else INPUT)
            transformations.append(Transform(self.objects[name], replacement))
        for name in ("AC", "l"):
            replacement = self.detail.line(self.data["lines"][name], AUXILIARY, 0.45)
            transformations.append(Transform(self.objects[name], replacement))
        transformations.append(Transform(self.objects["right_angle"], self.right_angle(self.detail)))
        replacement = Line(self.detail.at(self.data["points"]["B"]),
                           self.detail.at(self.data["points"]["E"]),
                           color=RESULT, stroke_width=2)
        transformations.append(Transform(self.objects["BE"], replacement))
        self.play(*transformations, run_time=1.25)
        self.view = self.detail

    def restore_sides(self):
        self.stage("连接 D、E，取得一条边线")
        self.caption("连接 D、E，得到目标正方形的一条边线")
        self.draw("d", self.view.line(self.data["lines"]["d"]), 1.1)
        self.wait(1.6)
        self.stage("恢复其余三条边")
        for name, caption, hold in (
            ("a", "过 A 作 DE 的垂线", 1),
            ("c", "过 C 作 DE 的垂线", 1),
            ("b", "过 B 作 DE 的平行线", 1.5),
        ):
            self.caption(caption)
            self.draw(name, self.view.line(self.data["lines"][name]))
            self.wait(hold)

    def restore_vertices(self):
        self.stage("取得四个顶点")
        self.caption("取四条边线的相邻交点，得到 P、Q、R、S")
        for name in "PQRS":
            self.mark(name, color=RESULT)
        self.play(*[self.objects[name].animate.set_stroke(opacity=0.15)
                    for name in ("AC", "l", "BE", "right_angle")], run_time=0.4)
        square = Polygon(*[self.view.at(self.data["points"][name]) for name in "PQRS"],
                         color=RESULT, stroke_width=2.8, fill_opacity=0)
        self.draw("target_square", square, 1.7, list("PQRS"))
        self.wait(2)

    def proof_guides(self):
        points = {**self.data["points"], **self.data["display_points"]}
        group = VGroup()
        for first, second, color in (("A", "H", RESULT), ("H", "C", AUXILIARY),
                                     ("B", "K", RESULT), ("K", "E", AUXILIARY)):
            group.add(DashedLine(self.view.at(points[first]), self.view.at(points[second]),
                                 color=color, stroke_width=1.5, dash_length=0.07))
        horizontal_middle = (np.array(points["A"]) + points["H"]) / 2
        vertical_middle = (np.array(points["B"]) + points["K"]) / 2
        group.add(self.text("s", 23, RESULT).move_to(
            self.view.at(horizontal_middle) + np.array([0, -0.23, 0])))
        group.add(self.text("s", 23, RESULT).move_to(
            self.view.at(vertical_middle) + np.array([0.23, 0.10, 0])))
        return group

    def explain_direction(self):
        self.stage("为什么 DE 是目标边线")
        self.caption("旋转90°后，BE 的竖直跨度等于 AC 的水平跨度")
        self.play(self.objects["AC"].animate.set_stroke(opacity=0.55),
                  self.objects["BE"].animate.set_stroke(opacity=0.55), run_time=0.4)
        self.draw("proof_guides", self.proof_guides(), 1.1, ["A", "B", "C", "E", "d", "c"])
        self.panel("边方向的依据", ["设目标正方形的边长为 s", "AC 的水平跨度是 s",
                                    "BE 的竖直跨度也是 s", "E 与 D 同在上边线上"], AUXILIARY)
        self.wait(6.5)

    def finish_square(self):
        self.stage("正方形 PQRS 已恢复")
        self.caption("A、B、C、D 分别位于四条边的内部", RESULT)
        self.play(FadeOut(self.objects["proof_guides"]),
                  *[self.objects[name].animate.set_stroke(opacity=0)
                    for name in ("AC", "l", "BE", "right_angle")],
                  *[self.objects[name].animate.set_stroke(opacity=0.22)
                    for name in ("a", "b", "c", "d")], run_time=0.5)
        self.panel("完整正方形已作成", ["四个顶点 P、Q、R、S", "四条边分别包含给定点"], RESULT)
        for name in "ABCD":
            self.play(Indicate(self.objects[name][0], color=INPUT, scale_factor=1.5), run_time=0.45)
        self.wait(3.8)

    def write_timeline(self):
        movie = Path(self.renderer.file_writer.movie_file_path)
        report = {
            "scene": type(self).__name__, "movie_file": movie.name,
            "geometry_sha256": self.geometry_hash,
            "animation_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "resolution": [config.pixel_width, config.pixel_height],
            "frame_rate": config.frame_rate,
            "duration_seconds": round(float(self.time), 6),
            "sections": self.sections, "construction_events": self.audit,
        }
        movie.with_suffix(".timeline.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
