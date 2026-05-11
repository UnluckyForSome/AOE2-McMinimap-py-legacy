"""Backward-compatible surface when ``McMinimap.py`` is on ``sys.path``.

PyPI / package layout: real implementation lives in ``aoe2_mcminimap.mcminimap``.
"""

from __future__ import annotations

from aoe2_mcminimap.mcminimap import (
    MinimapSettings,
    main,
    read_map,
    render_match,
    save_minimap,
    to_image,
    to_image_from_match,
    to_png_bytes,
    to_png_bytes_from_match,
)

__all__ = [
    "MinimapSettings",
    "main",
    "read_map",
    "render_match",
    "save_minimap",
    "to_image",
    "to_image_from_match",
    "to_png_bytes",
    "to_png_bytes_from_match",
]

if __name__ == "__main__":
    main()
