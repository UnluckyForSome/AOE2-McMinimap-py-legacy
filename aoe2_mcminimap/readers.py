"""Recorded-game and scenario loaders."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from types import SimpleNamespace

from .resources import (
    ALL_SUPPORTED_EXTENSIONS,
    CIVILIZATIONS_BY_ID,
    PACKAGE_DIR,
    RECORDED_GAME_EXTENSIONS,
    wall_objects,
)


def _civ_name_from_id(civilization_id):
    if civilization_id is None:
        return "Unknown"
    try:
        civ_id = int(civilization_id)
    except Exception:
        return "Unknown"
    return CIVILIZATIONS_BY_ID.get(civ_id, "Unknown")


@contextmanager
def _suppress_aoe2scenario_parser_output():
    try:
        import AoE2ScenarioParser.helper.printers as printers  # type: ignore
    except Exception:
        printers = None

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if printers is None:
        yield
        return

    old_rprint = getattr(printers, "rprint", None)
    old_s_print = getattr(printers, "s_print", None)

    def _noop(*_args, **_kwargs):
        return None

    try:
        printers.rprint = _noop  # type: ignore
        printers.s_print = _noop  # type: ignore
        yield
    finally:
        if old_rprint is not None:
            printers.rprint = old_rprint  # type: ignore
        if old_s_print is not None:
            printers.s_print = old_s_print  # type: ignore


def _import_aoe2_geniescx_scenario():
    """Load ``aoe2_geniescx.scenario.Scenario`` from pip or a vendored ``pylibs/`` bundle."""
    try:
        from aoe2_geniescx.scenario import Scenario  # type: ignore

        return Scenario
    except ImportError:
        pass

    pylibs = PACKAGE_DIR / "pylibs"
    if (pylibs / "aoe2_geniescx").is_dir():
        s = str(pylibs)
        if s not in sys.path:
            sys.path.insert(0, s)
        from aoe2_geniescx.scenario import Scenario  # type: ignore

        return Scenario

    raise ImportError(
        "aoe2_geniescx not found: pip install AOE2-McGenieSCX "
        "or vendor the package under aoe2_mcminimap/pylibs/aoe2_geniescx."
    )


def _adapter_from_scenario(input_file: str):
    """Definitive Edition ``.aoe2scenario`` via AoE2ScenarioParser."""
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # type: ignore

    with _suppress_aoe2scenario_parser_output():
        scn = AoE2DEScenario.from_file(input_file)

    mm = scn.map_manager
    dim = int(mm.map_width)

    tiles = [
        SimpleNamespace(
            position=SimpleNamespace(x=int(t.x), y=int(t.y)),
            terrain=int(t.terrain_id),
            elevation=int(t.elevation),
        )
        for t in mm.terrain
    ]
    map_obj = SimpleNamespace(dimension=dim, tiles=tiles)

    um = scn.unit_manager
    pm = scn.player_manager

    gaia = []
    player_units = {pid: [] for pid in range(1, 9)}

    for u in um.get_all_units():
        obj_id = int(u.unit_const)
        x, y = int(u.x), int(u.y)
        unit_ns = SimpleNamespace(
            object_id=obj_id,
            class_id=80 if obj_id in wall_objects else 0,
            position=SimpleNamespace(x=x, y=y),
        )
        if int(u.player) == 0:
            gaia.append(SimpleNamespace(object_id=obj_id, position=SimpleNamespace(x=x, y=y)))
        else:
            pid = int(u.player)
            if pid in player_units:
                player_units[pid].append(unit_ns)

    players = []
    for pid in range(1, 9):
        civ_name = "Unknown"
        try:
            p = pm.players[pid]
            civ = getattr(p, "civilization", None)
            if civ is not None and hasattr(civ, "name"):
                civ_name = str(civ.name).replace("_", " ").title()
        except Exception:
            pass

        players.append(
            SimpleNamespace(
                color_id=min(max(0, pid - 1), 7),
                objects=player_units[pid],
                position=SimpleNamespace(x=None, y=None),
                civilization=civ_name,
            )
        )

    return SimpleNamespace(map=map_obj, players=players, gaia=gaia)


def _adapter_from_aoe2_geniescx(input_file: str):
    """Legacy SCX (< 1.35 container) via ``aoe2_geniescx``."""
    Scenario = _import_aoe2_geniescx_scenario()
    with open(input_file, "rb") as f:
        scn = Scenario.read_from(f)

    m = scn.map()
    width = int(m.width)
    height = int(m.height)
    if width != height:
        raise ValueError(f"Scenario map is not square: {width}x{height}")
    dim = width

    tiles = []
    for y in range(height):
        row = m.tiles[y * width : (y + 1) * width]
        for x, t in enumerate(row):
            tiles.append(
                SimpleNamespace(
                    position=SimpleNamespace(x=int(x), y=int(y)),
                    terrain=int(t.terrain),
                    elevation=int(t.elevation),
                )
            )
    map_obj = SimpleNamespace(dimension=dim, tiles=tiles)

    gaia = []
    player_units = {pid: [] for pid in range(1, 9)}
    by_player = scn.format.player_objects
    for owner in range(min(len(by_player), 9)):
        for u in by_player[owner]:
            obj_id = int(u.object_type)
            x, y = int(u.position[0]), int(u.position[1])
            if owner == 0:
                gaia.append(SimpleNamespace(object_id=obj_id, position=SimpleNamespace(x=x, y=y)))
                continue
            unit_ns = SimpleNamespace(
                object_id=obj_id,
                class_id=80 if obj_id in wall_objects else 0,
                position=SimpleNamespace(x=x, y=y),
            )
            if owner in player_units:
                player_units[owner].append(unit_ns)

    scenario_players_list = scn.scenario_players()
    players = []
    for pid in range(1, 9):
        pos_x, pos_y = None, None
        civ_name = "Unknown"
        try:
            sp = scenario_players_list[pid - 1]
            if sp is not None:
                if sp.location:
                    pos_x, pos_y = int(sp.location[0]), int(sp.location[1])
                if sp.name:
                    civ_name = str(sp.name)
        except Exception:
            pass
        players.append(
            SimpleNamespace(
                color_id=min(max(0, pid - 1), 7),
                objects=player_units[pid],
                position=SimpleNamespace(x=pos_x, y=pos_y),
                civilization=civ_name,
            )
        )

    return SimpleNamespace(map=map_obj, players=players, gaia=gaia)


def _adapter_from_aoc_mgz_summary(s) -> SimpleNamespace:
    """Match shape from ``mgz.summary.Summary``."""
    m = s.get_map()
    dim = int(m["dimension"])
    tiles = [
        SimpleNamespace(
            position=SimpleNamespace(x=int(t["x"]), y=int(t["y"])),
            terrain=int(t["terrain_id"]),
            elevation=int(t["elevation"]),
        )
        for t in m["tiles"]
    ]
    map_obj = SimpleNamespace(dimension=dim, tiles=tiles)

    od = s.get_objects()
    gaia = []
    player_units = {pid: [] for pid in range(1, 9)}
    for o in od["objects"]:
        oid = o.get("object_id")
        if oid is None:
            continue
        cid = o.get("class_id")
        if cid is None:
            cid = 80 if oid in wall_objects else 0
        x, y = int(o["x"]), int(o["y"])
        pn = o.get("player_number")
        if pn is None or pn == 0:
            gaia.append(SimpleNamespace(object_id=oid, position=SimpleNamespace(x=x, y=y)))
            continue
        pid = int(pn)
        if pid not in player_units:
            continue
        player_units[pid].append(
            SimpleNamespace(
                object_id=oid,
                class_id=cid,
                position=SimpleNamespace(x=x, y=y),
            )
        )

    players = []
    for pdata in sorted(s.get_players(), key=lambda r: r.get("number", 0)):
        num = int(pdata["number"])
        if num < 1 or num > 8:
            continue
        civ_raw = pdata.get("civilization")
        if isinstance(civ_raw, int):
            civ_name = _civ_name_from_id(civ_raw)
        elif civ_raw is not None:
            civ_name = str(civ_raw)
        else:
            civ_name = "Unknown"
        pos = pdata.get("position")
        pos_x, pos_y = None, None
        if pos and isinstance(pos, (list, tuple)) and len(pos) >= 2:
            pos_x, pos_y = pos[0], pos[1]
        raw_color = pdata.get("color_id", 0)
        color_id = min(max(0, int(raw_color) if raw_color is not None else 0), 7)
        players.append(
            SimpleNamespace(
                color_id=color_id,
                objects=player_units.get(num, []),
                position=SimpleNamespace(x=pos_x, y=pos_y),
                civilization=civ_name,
            )
        )

    return SimpleNamespace(map=map_obj, players=players, gaia=gaia)


def get_mgz(input_file: str):
    """Load a recorded game via ``mgz.summary.Summary`` from ``AOE2-McMGZ``."""
    try:
        from mgz.summary import Summary  # type: ignore  # noqa: PLC0415
    except ImportError as e:
        raise RuntimeError(
            "Recorded games require the ``AOE2-McMGZ`` package "
            "(import namespace ``mgz``). Install: ``pip install AOE2-McMGZ``."
        ) from e

    with open(input_file, "rb") as fh:
        try:
            return _adapter_from_aoc_mgz_summary(Summary(fh))
        except BaseException as e:  # noqa: BLE001
            raise RuntimeError(f"Could not parse recording with mgz Summary: {e!s}") from e


def _sniff_scx_format_version_tuple_from_file(input_file: str) -> tuple[int, int] | None:
    """Try to read the outer 4-byte SCX format version like ``b'1.21'`` or ``b'1.36'``."""
    try:
        with open(input_file, "rb") as f:
            b = f.read(4)
    except OSError:
        return None
    if len(b) != 4:
        return None
    if not (48 <= b[0] <= 57 and b[1] == 46 and 48 <= b[2] <= 57 and 48 <= b[3] <= 57):
        return None
    try:
        major = int(chr(b[0]))
        minor = (int(chr(b[2])) * 10) + int(chr(b[3]))
        return major, minor
    except Exception:
        return None


def read_map(input_file: str):
    """Load map/player data from a supported scenario or recorded game."""
    suffix = Path(input_file).suffix.lower()

    if suffix in RECORDED_GAME_EXTENSIONS:
        return get_mgz(input_file)

    fmt = _sniff_scx_format_version_tuple_from_file(input_file)
    if fmt is not None:
        major, minor = fmt
        if major == 1 and minor >= 35:
            return _adapter_from_scenario(input_file)
        return _adapter_from_aoe2_geniescx(input_file)

    raise ValueError(
        f"Unsupported file type {suffix!r} for {input_file!r}. "
        f"Supported extensions: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
    )


__all__ = ["read_map"]
