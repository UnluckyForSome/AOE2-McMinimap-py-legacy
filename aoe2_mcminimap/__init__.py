"""AoE II minimap rendering from scenarios and recorded games."""

from .readers import read_map
from .render import (
    render_match,
    save_minimap,
    to_image,
    to_image_from_match,
    to_png_bytes,
    to_png_bytes_from_match,
)
from .resources import DEFINITIVE_SCENARIO_EXTENSIONS, LEGACY_SCENARIO_EXTENSIONS, RECORDED_GAME_EXTENSIONS
from .settings import MinimapSettings

__all__ = [
    "DEFINITIVE_SCENARIO_EXTENSIONS",
    "LEGACY_SCENARIO_EXTENSIONS",
    "MinimapSettings",
    "RECORDED_GAME_EXTENSIONS",
    "read_map",
    "render_match",
    "save_minimap",
    "to_image",
    "to_image_from_match",
    "to_png_bytes",
    "to_png_bytes_from_match",
]

__version__ = "0.1.1"
