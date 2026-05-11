"""Render settings and temporary settings application."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

object_mode = "square"
town_center = "pixel"
_render_emblems_dir: Path | str | None = None
angle = 45
multiplier_integer = 9
orthographic_ratio = 2
border_spacing = 4

draw_cliffs = True
draw_walls = True
smooth_walls = True

draw_players = True
draw_gaia = True
draw_food = True
draw_gold = True
draw_stone = True
draw_relics = True

cliff_size = 1
player_wall_size = 1
relic_size = 4
stone_size = 4
gold_size = 4
food_size = 4
player_object_size = 4
town_center_size = 4
civ_emblem_halo = 40

MAX_MULTIPLIER_INTEGER = 10

ObjectMode = Literal["square", "rotated"]
TownCenterMode = Literal["none", "pixel", "emblem"]


@dataclass(frozen=True)
class MinimapSettings:
    object_mode: ObjectMode = "square"
    town_center: TownCenterMode = "pixel"
    angle: int = 45
    multiplier_integer: int = 9
    orthographic_ratio: int = 2
    border_spacing: int = 4

    draw_players: bool = True
    draw_gaia: bool = True
    draw_food: bool = True
    draw_gold: bool = True
    draw_stone: bool = True
    draw_relics: bool = True
    draw_cliffs: bool = True
    draw_walls: bool = True
    smooth_walls: bool = True
    emblems_dir: Path | str | None = None

    cliff_size: int = 1
    player_wall_size: int = 1
    relic_size: int = 4
    stone_size: int = 4
    gold_size: int = 4
    food_size: int = 4
    player_object_size: int = 4
    town_center_size: int = 4
    civ_emblem_halo: int = 40
    final_size: tuple[int, int] | None = None


@contextmanager
def _apply_settings(settings: MinimapSettings):
    global object_mode
    global town_center
    global angle
    global multiplier_integer
    global orthographic_ratio
    global border_spacing
    global draw_players
    global draw_gaia
    global draw_food
    global draw_gold
    global draw_stone
    global draw_relics
    global draw_cliffs
    global draw_walls
    global smooth_walls
    global _render_emblems_dir
    global cliff_size
    global player_wall_size
    global relic_size
    global stone_size
    global gold_size
    global food_size
    global player_object_size
    global town_center_size
    global civ_emblem_halo

    old = (
        object_mode,
        town_center,
        angle,
        multiplier_integer,
        orthographic_ratio,
        border_spacing,
        draw_players,
        draw_gaia,
        draw_food,
        draw_gold,
        draw_stone,
        draw_relics,
        draw_cliffs,
        draw_walls,
        smooth_walls,
        _render_emblems_dir,
        cliff_size,
        player_wall_size,
        relic_size,
        stone_size,
        gold_size,
        food_size,
        player_object_size,
        town_center_size,
        civ_emblem_halo,
    )
    try:
        object_mode = settings.object_mode
        town_center = settings.town_center
        angle = int(settings.angle)
        multiplier_integer = min(MAX_MULTIPLIER_INTEGER, max(1, int(settings.multiplier_integer)))
        orthographic_ratio = int(settings.orthographic_ratio)
        border_spacing = int(settings.border_spacing)
        draw_players = bool(settings.draw_players)
        draw_gaia = bool(settings.draw_gaia)
        draw_food = bool(settings.draw_food)
        draw_gold = bool(settings.draw_gold)
        draw_stone = bool(settings.draw_stone)
        draw_relics = bool(settings.draw_relics)
        draw_cliffs = bool(settings.draw_cliffs)
        draw_walls = bool(settings.draw_walls)
        smooth_walls = bool(settings.smooth_walls)
        _render_emblems_dir = settings.emblems_dir
        cliff_size = int(settings.cliff_size)
        player_wall_size = int(settings.player_wall_size)
        relic_size = int(settings.relic_size)
        stone_size = int(settings.stone_size)
        gold_size = int(settings.gold_size)
        food_size = int(settings.food_size)
        player_object_size = int(settings.player_object_size)
        town_center_size = int(settings.town_center_size)
        civ_emblem_halo = int(settings.civ_emblem_halo)
        yield
    finally:
        (
            object_mode,
            town_center,
            angle,
            multiplier_integer,
            orthographic_ratio,
            border_spacing,
            draw_players,
            draw_gaia,
            draw_food,
            draw_gold,
            draw_stone,
            draw_relics,
            draw_cliffs,
            draw_walls,
            smooth_walls,
            _render_emblems_dir,
            cliff_size,
            player_wall_size,
            relic_size,
            stone_size,
            gold_size,
            food_size,
            player_object_size,
            town_center_size,
            civ_emblem_halo,
        ) = old


__all__ = [
    "MAX_MULTIPLIER_INTEGER",
    "MinimapSettings",
    "ObjectMode",
    "TownCenterMode",
    "_apply_settings",
]
