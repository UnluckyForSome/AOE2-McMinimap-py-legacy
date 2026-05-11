"""AoE II minimap rendering from scenarios and recorded games."""

from aoe2_mcminimap.mcminimap import (
    DEFINITIVE_SCENARIO_EXTENSIONS,
    LEGACY_SCENARIO_EXTENSIONS,
    MinimapSettings,
    RECORDED_GAME_EXTENSIONS,
    read_map,
    render_match,
    save_minimap,
    to_image,
    to_image_from_match,
    to_png_bytes,
    to_png_bytes_from_match,
)

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

__version__ = "0.1.0"
