from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest import TestCase

from PIL import Image, ImageDraw

_PKG = Path(__file__).resolve().parents[1] / "aoe2_mcminimap"


def _load_render_module():
    pkg = types.ModuleType("aoe2_mcminimap")
    pkg.__path__ = [str(_PKG)]
    sys.modules["aoe2_mcminimap"] = pkg
    for name in ("settings", "resources"):
        path = _PKG / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"aoe2_mcminimap.{name}", path)
        mod = importlib.util.module_from_spec(spec)
        setattr(pkg, name, mod)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
    readers_stub = types.ModuleType("aoe2_mcminimap.readers")

    def _noop(*_a, **_k):
        raise NotImplementedError

    readers_stub.match_from_parsed_scenario = _noop
    readers_stub.read_map = _noop
    sys.modules["aoe2_mcminimap.readers"] = readers_stub
    setattr(pkg, "readers", readers_stub)
    path = _PKG / "render.py"
    spec = importlib.util.spec_from_file_location("aoe2_mcminimap.render", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_render = _load_render_module()


class TestRenderBorder(TestCase):
    def test_draw_border_outlines_tiny_canvas_does_not_raise(self):
        for size in (1, 2, 3, 6, 7, 8):
            img = Image.new("RGBA", (size, size))
            draw = ImageDraw.Draw(img)
            _render._draw_border_outlines(draw, img.width - 1, img.height - 1)

    def test_create_border_canvas_6x6_map(self):
        img = _render.create_border_canvas(6)
        self.assertGreater(img.width, 0)
        self.assertGreater(img.height, 0)

    def test_min_border_source_dimension(self):
        self.assertGreaterEqual(_render._MIN_BORDER_SOURCE_DIMENSION, 8)
