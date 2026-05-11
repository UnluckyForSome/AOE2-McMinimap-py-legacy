"""Package data and supported-file constants."""

from __future__ import annotations

import json
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
MCMINIMAP_CONSTANTS_PATH = DATA_DIR / "mcminimap_constants.json"
if not MCMINIMAP_CONSTANTS_PATH.is_file():
    raise RuntimeError(
        "Missing required local JSON data file: "
        f"{MCMINIMAP_CONSTANTS_PATH}\n\n"
        "This file is bundled project data and is not downloaded automatically."
    )

DEFAULT_EMBLEMS_DIR = PACKAGE_DIR / "emblems"


def _load_mcminimap_tables():
    """Load terrain colors and object ID sets from ``data/mcminimap_constants.json``."""
    with open(MCMINIMAP_CONSTANTS_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    def _int_key_str_dict(d):
        return {int(k): str(v) for k, v in d.items()}

    def _int_key_tile_dict(d):
        return {int(k): dict(v) for k, v in d.items()}

    tc_pos = raw["town_center_position_object_ids"]
    tc_pos_tuple = tuple(int(x) for x in tc_pos)
    town_center_skip = frozenset(int(k) for k in raw["town_center_objects"])
    civs_by_id = {int(k): str(v) for k, v in raw.get("civilizations_by_id", {}).items()}
    return (
        tuple(raw["player_colors"]),
        _int_key_tile_dict(raw["tiles_colors"]),
        _int_key_str_dict(raw["wall_objects"]),
        _int_key_str_dict(raw["food_objects"]),
        _int_key_str_dict(raw["stone_objects"]),
        _int_key_str_dict(raw["gold_objects"]),
        _int_key_str_dict(raw["relic_objects"]),
        _int_key_str_dict(raw["cliff_objects"]),
        tc_pos_tuple,
        town_center_skip,
        civs_by_id,
    )


def resolve_emblems_dir(configured: Path | str | None) -> Path:
    if configured is None:
        return DEFAULT_EMBLEMS_DIR
    return Path(configured).expanduser().resolve()


RECORDED_GAME_EXTENSIONS = frozenset({".mgl", ".mgx", ".mgz", ".aoe2record"})
DEFINITIVE_SCENARIO_EXTENSIONS = frozenset({".aoe2scenario"})
LEGACY_SCENARIO_EXTENSIONS = frozenset({".scn", ".scn2", ".scx", ".scx2"})
ALL_SUPPORTED_EXTENSIONS = (
    RECORDED_GAME_EXTENSIONS | DEFINITIVE_SCENARIO_EXTENSIONS | LEGACY_SCENARIO_EXTENSIONS
)
SUPPORTED_INPUT_SUFFIXES = frozenset(ext.lower() for ext in ALL_SUPPORTED_EXTENSIONS)

(
    player_colors,
    tiles_colors,
    wall_objects,
    food_objects,
    stone_objects,
    gold_objects,
    relic_objects,
    cliff_objects,
    TC_IDS,
    TOWN_CENTER_OBJECT_IDS,
    CIVILIZATIONS_BY_ID,
) = _load_mcminimap_tables()


__all__ = [
    "ALL_SUPPORTED_EXTENSIONS",
    "CIVILIZATIONS_BY_ID",
    "DATA_DIR",
    "DEFAULT_EMBLEMS_DIR",
    "DEFINITIVE_SCENARIO_EXTENSIONS",
    "LEGACY_SCENARIO_EXTENSIONS",
    "MCMINIMAP_CONSTANTS_PATH",
    "PACKAGE_DIR",
    "RECORDED_GAME_EXTENSIONS",
    "SUPPORTED_INPUT_SUFFIXES",
    "TC_IDS",
    "TOWN_CENTER_OBJECT_IDS",
    "cliff_objects",
    "food_objects",
    "gold_objects",
    "player_colors",
    "relic_objects",
    "resolve_emblems_dir",
    "stone_objects",
    "tiles_colors",
    "wall_objects",
]
