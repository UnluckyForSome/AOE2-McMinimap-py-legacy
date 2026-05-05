"""Python port of `genie-scx` (genie-rs) scenario parser.

Supports SCX container format versions from AoK/AoC/HD era up to (but not including) DE2 1.36+.

For **DE2 container format >= 1.36**, use AoE2ScenarioParser (see `vendor/aoe2mcminimap/McMinimap.py`).

This module is designed to be reusable outside mcminimap (e.g. scenario upload verification).
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Any


def _decode_cp1252(b: bytes) -> str:
    # genie-scx uses Windows-1252. We also strip trailing NULLs.
    if not b:
        return ""
    if b"\x00" in b:
        b = b.split(b"\x00", 1)[0]
    return b.decode("cp1252", errors="strict")


class Reader:
    __slots__ = ("_b", "_p")

    def __init__(self, b: bytes):
        self._b = b
        self._p = 0

    def tell(self) -> int:
        return self._p

    def read(self, n: int) -> bytes:
        if n < 0:
            raise ValueError("read length < 0")
        p2 = self._p + n
        if p2 > len(self._b):
            raise EOFError(f"unexpected EOF: need {n} bytes at {self._p}, size={len(self._b)}")
        out = self._b[self._p : p2]
        self._p = p2
        return out

    def skip(self, n: int) -> None:
        self.read(n)

    def u8(self) -> int:
        return self.read(1)[0]

    def i8(self) -> int:
        return struct.unpack_from("<b", self.read(1), 0)[0]

    def u16(self) -> int:
        return struct.unpack_from("<H", self.read(2), 0)[0]

    def i16(self) -> int:
        return struct.unpack_from("<h", self.read(2), 0)[0]

    def u32(self) -> int:
        return struct.unpack_from("<I", self.read(4), 0)[0]

    def i32(self) -> int:
        return struct.unpack_from("<i", self.read(4), 0)[0]

    def f32(self) -> float:
        return struct.unpack_from("<f", self.read(4), 0)[0]

    def f64(self) -> float:
        return struct.unpack_from("<d", self.read(8), 0)[0]

    def read_str_len(self, length: int) -> str | None:
        if length <= 0:
            return None
        s = _decode_cp1252(self.read(length))
        return s if s != "" else None

    def read_u16_length_prefixed_str(self) -> str | None:
        ln = self.u16()
        if ln == 0xFFFF:
            return None
        return self.read_str_len(ln)

    def read_u32_length_prefixed_str(self) -> str | None:
        ln = self.u32()
        if ln == 0xFFFF_FFFF:
            return None
        return self.read_str_len(ln)

    def read_hd_style_str(self) -> str | None:
        sig = self.u16()
        if sig != 0x0A60:
            raise ValueError(f"bad hd-style string signature: {sig:#x}")
        ln = self.u16()
        return self.read_str_len(ln)

def _starting_age_from_i32(n: int, version: float) -> int:
    # We keep this as the raw numeric code; conversion tables differ pre/post 1.25 in Rust.
    # The full enum mapping is not needed for mcminimap, but we still preserve the parsed value.
    return n


def _default_player_start_resources() -> dict[str, int]:
    return {
        "gold": 100,
        "wood": 200,
        "food": 200,
        "stone": 200,
        "ore": 100,
        "goods": 0,
        "player_color": None,
    }


def _read_player_start_resources(r: Reader, version: float) -> dict[str, int]:
    gold = r.i32()
    wood = r.i32()
    food = r.i32()
    stone = r.i32()
    ore = r.i32() if version >= 1.17 else 100
    goods = r.i32() if version >= 1.17 else 0
    player_color = r.i32() if version >= 1.24 else None
    return {
        "gold": gold,
        "wood": wood,
        "food": food,
        "stone": stone,
        "ore": ore,
        "goods": goods,
        "player_color": player_color,
    }


def _read_victory_info(r: Reader) -> dict[str, Any]:
    return {
        "conquest": r.i32() != 0,
        "ruins": r.i32(),
        "relics": r.i32(),
        "discoveries": r.i32(),
        "exploration": r.i32(),
        "gold": r.i32(),
    }


def _read_legacy_victory_info(r: Reader) -> dict[str, Any]:
    object_type = r.i32()
    all_flag = r.i32() != 0
    player_id = r.i32()
    dest_object_id = r.i32()
    area = (r.f32(), r.f32(), r.f32(), r.f32())
    victory_type = r.i32()
    amount = r.i32()
    attribute = r.i32()
    object_id = r.i32()
    dest_object_id2 = r.i32()
    _object = r.u32()
    _dest_object = r.u32()
    return {
        "object_type": object_type,
        "all_flag": all_flag,
        "player_id": player_id,
        "dest_object_id": dest_object_id,
        "area": area,
        "victory_type": victory_type,
        "amount": amount,
        "attribute": attribute,
        "object_id": object_id,
        "dest_object_id2": dest_object_id2,
    }


def _read_rge_scen(r: Reader) -> dict[str, Any]:
    # Port of `RGEScen::read_from` (genie-scx/format.rs).
    version = r.f32()

    player_names: list[str | None] = [None] * 16
    if version > 1.13:
        player_names = [r.read_str_len(256) for _ in range(16)]

    player_string_table: list[int | None] = [None] * 16
    if version > 1.16:
        for i in range(16):
            v = r.u32()
            player_string_table[i] = None if v in (0xFFFF_FFFF, 0xFFFF_FFFE) else v

    player_base_properties = [{"active": 0, "player_type": 0, "civilization": 0, "posture": 0} for _ in range(16)]
    if version > 1.13:
        for i in range(16):
            player_base_properties[i]["active"] = r.i32()
            player_base_properties[i]["player_type"] = r.i32()
            player_base_properties[i]["civilization"] = r.i32()
            player_base_properties[i]["posture"] = r.i32()

    victory_conquest = (r.u8() != 0) if version >= 1.07 else True

    _timeline_count = r.i16()
    _timeline_available = r.i16()
    _old_time = r.f32()

    if version >= 1.28:
        for _ in range(16):
            r.u32()  # civ lock table

    name_length = r.i16()
    name = r.read_str_len(name_length) or ""

    if version >= 1.16:
        description_string_table = _read_opt_u32(r)
        hints_string_table = _read_opt_u32(r)
        win_message_string_table = _read_opt_u32(r)
        loss_message_string_table = _read_opt_u32(r)
        history_string_table = _read_opt_u32(r)
    else:
        description_string_table = hints_string_table = win_message_string_table = loss_message_string_table = history_string_table = None

    scout_string_table = _read_opt_u32(r) if version >= 1.22 else None

    description_length = r.i16()
    description = r.read_str_len(description_length)

    if version >= 1.11:
        hints = r.read_u16_length_prefixed_str()
        win_message = r.read_u16_length_prefixed_str()
        loss_message = r.read_u16_length_prefixed_str()
        history = r.read_u16_length_prefixed_str()
    else:
        hints = win_message = loss_message = history = None

    scout = r.read_u16_length_prefixed_str() if version >= 1.22 else None

    pregame_cinematic = r.read_u16_length_prefixed_str()
    victory_cinematic = r.read_u16_length_prefixed_str()
    loss_cinematic = r.read_u16_length_prefixed_str()

    mission_bmp = r.read_u16_length_prefixed_str() if version >= 1.09 else None

    if version >= 1.10:
        _ = _read_bitmap(r)

    player_build_lists = [r.read_u16_length_prefixed_str() for _ in range(16)]
    player_city_plans = [r.read_u16_length_prefixed_str() for _ in range(16)]

    player_ai_rules = [None] * 16
    if version >= 1.08:
        player_ai_rules = [r.read_u16_length_prefixed_str() for _ in range(16)]

    player_files = []
    for _ in range(16):
        build_list_length = r.i32()
        city_plan_length = r.i32()
        ai_rules_length = r.i32() if version >= 1.08 else 0
        build_list = r.read_str_len(build_list_length)
        city_plan = r.read_str_len(city_plan_length)
        ai_rules_content = r.read_str_len(ai_rules_length)
        player_files.append({"build_list": build_list, "city_plan": city_plan, "ai_rules": ai_rules_content})

    ai_rules_types = [0] * 16
    if version >= 1.20:
        ai_rules_types = [r.i8() for _ in range(16)]

    if version >= 1.02:
        _sep = r.i32()  # -99

    return {
        "version": version,
        "player_names": player_names,
        "player_string_table": player_string_table,
        "player_base_properties": player_base_properties,
        "victory_conquest": victory_conquest,
        "name": name,
        "description_string_table": description_string_table,
        "hints_string_table": hints_string_table,
        "win_message_string_table": win_message_string_table,
        "loss_message_string_table": loss_message_string_table,
        "history_string_table": history_string_table,
        "scout_string_table": scout_string_table,
        "description": description,
        "hints": hints,
        "win_message": win_message,
        "loss_message": loss_message,
        "history": history,
        "scout": scout,
        "pregame_cinematic": pregame_cinematic,
        "victory_cinematic": victory_cinematic,
        "loss_cinematic": loss_cinematic,
        "mission_bmp": mission_bmp,
        "player_build_lists": player_build_lists,
        "player_city_plans": player_city_plans,
        "player_ai_rules": player_ai_rules,
        "player_files": player_files,
        "ai_rules_types": ai_rules_types,
    }


def _read_opt_u32(r: Reader) -> int | None:
    v = r.u32()
    return None if v in (0xFFFF_FFFF, 0xFFFF_FFFE) else v


def _read_bitmap(r: Reader) -> None:
    # Port of `Bitmap::read_from` (genie-scx/src/bitmap.rs). We only need to consume bytes.
    own_memory = r.u32()
    width = r.u32()
    height = r.u32()
    _orientation = r.u16()

    if width <= 0 or height <= 0:
        return

    # BitmapInfo
    _size = r.u32()
    _info_width = r.i32()
    _info_height = r.i32()
    _planes = r.u16()
    _bit_count = r.u16()
    _compression = r.u32()
    _size_image = r.u32()
    _xpels_per_meter = r.i32()
    _ypels_per_meter = r.i32()
    _clr_used = r.u32()
    _clr_important = r.u32()
    # 256 RGBA8 entries
    r.skip(256 * 4)

    # Pixel payload: height * aligned_width, where aligned_width is (width+3)&~3
    aligned_row = (width + 3) & ~3
    pixel_len = height * aligned_row
    r.skip(int(pixel_len))


def _read_trigger_effect(r: Reader, version: float) -> dict[str, Any]:
    effect_type = r.i32()
    num_properties = r.i32() if version > 1.0 else 16
    props = [r.i32() for _ in range(num_properties)]
    while len(props) < 24:
        props.append(-1)
    chat_text = r.read_u32_length_prefixed_str()
    audio_file = r.read_u32_length_prefixed_str()
    objects: list[int] = []
    if version > 1.1:
        for _ in range(max(0, props[4])):
            objects.append(r.i32())
    else:
        objects.append(props[4])
        props[4] = 1
    return {
        "effect_type": effect_type,
        "properties": props,
        "chat_text": chat_text,
        "audio_file": audio_file,
        "objects": objects,
    }


def _read_trigger_condition(r: Reader, version: float) -> dict[str, Any]:
    condition_type = r.i32()
    num_properties = r.i32() if version > 1.0 else 13
    props = [r.i32() for _ in range(num_properties)]
    while len(props) < 18:
        props.append(-1)
    return {"condition_type": condition_type, "properties": props}


def _read_trigger(r: Reader, version: float) -> dict[str, Any]:
    enabled = r.i32() != 0
    looping = r.i8() != 0
    name_id = r.i32()
    is_objective = r.i8() != 0
    objective_order = r.i32()

    make_header = False
    short_description_id = None
    display_short_description = False
    short_description_state = 0
    mute_objective = False
    if version >= 1.8:
        make_header = r.u8() != 0
        short_description_id = _read_opt_u32(r)
        display_short_description = r.u8() != 0
        short_description_state = r.u8()
        start_time = r.u32()
        mute_objective = r.u8() != 0
    else:
        start_time = r.u32()

    description = r.read_u32_length_prefixed_str()
    name = r.read_u32_length_prefixed_str()
    short_description = r.read_u32_length_prefixed_str() if version >= 1.8 else None

    num_effects = r.i32()
    effects = [_read_trigger_effect(r, version) for _ in range(num_effects)]
    effect_order = [r.i32() for _ in range(num_effects)]

    num_conditions = r.i32()
    conditions = [_read_trigger_condition(r, version) for _ in range(num_conditions)]
    condition_order = [r.i32() for _ in range(num_conditions)]

    return {
        "enabled": enabled,
        "looping": looping,
        "name_id": name_id,
        "is_objective": is_objective,
        "objective_order": objective_order,
        "make_header": make_header,
        "short_description_id": short_description_id,
        "display_short_description": display_short_description,
        "short_description_state": short_description_state,
        "mute_objective": mute_objective,
        "start_time": start_time,
        "description": description,
        "name": name,
        "short_description": short_description,
        "effects": effects,
        "effect_order": effect_order,
        "conditions": conditions,
        "condition_order": condition_order,
    }

@dataclass(frozen=True)
class SCXVersion:
    raw: bytes  # length 4

    def __post_init__(self):
        if not isinstance(self.raw, (bytes, bytearray)) or len(self.raw) != 4:
            raise ValueError("SCXVersion must be 4 bytes")

    def as_str(self) -> str:
        return self.raw.decode("ascii", errors="replace")

    def to_player_version(self) -> float | None:
        # Port of genie-scx `SCXVersion::to_player_version`.
        b = self.raw
        if b == b"1.07":
            return 1.07
        if b in (b"1.09", b"1.10", b"1.11"):
            return 1.11
        if b in (b"1.12", b"1.13", b"1.14", b"1.15", b"1.16"):
            return 1.12
        if b in (b"1.18", b"1.19"):
            return 1.13
        if b in (b"1.20", b"1.21", b"1.32", b"1.36", b"1.37"):
            return 1.14
        return None

    def _cmp_key(self) -> tuple[int, int, int]:
        # Same ordering as Rust impl: major digit, then digit2, then digit3.
        b = self.raw
        return b[0], b[2], b[3]

    def __lt__(self, other: "SCXVersion") -> bool:
        return self._cmp_key() < other._cmp_key()

    def __ge__(self, other: "SCXVersion") -> bool:
        return self._cmp_key() >= other._cmp_key()


def sniff_scx_format_version_tuple(buf4: bytes) -> tuple[int, int] | None:
    if not isinstance(buf4, (bytes, bytearray)) or len(buf4) != 4:
        return None
    b = bytes(buf4)
    if not (48 <= b[0] <= 57 and b[1] == 46 and 48 <= b[2] <= 57 and 48 <= b[3] <= 57):
        return None
    return (b[0] - 48, (b[2] - 48) * 10 + (b[3] - 48))


def sniff_scx_format_version_tuple_from_file(path: str) -> tuple[int, int] | None:
    try:
        with open(path, "rb") as f:
            b = f.read(4)
    except OSError:
        return None
    return sniff_scx_format_version_tuple(b)


def is_de2_container_136_plus(path: str) -> bool:
    vt = sniff_scx_format_version_tuple_from_file(path)
    return bool(vt and vt[0] == 1 and vt[1] >= 36)


@dataclass
class DLCOptions:
    version: int
    game_data_set: int
    dependencies: list[int]

    @classmethod
    def read_from(cls, r: Reader) -> "DLCOptions":
        version_or_data_set = r.i32()
        if version_or_data_set in (0, 1):
            game_data_set = version_or_data_set
        else:
            game_data_set = r.i32()
        version = 0 if version_or_data_set == 1 else version_or_data_set
        num_deps = r.u32()
        deps = [r.i32() for _ in range(num_deps)]
        return cls(version=version, game_data_set=game_data_set, dependencies=deps)


@dataclass
class SCXHeader:
    version: int
    timestamp: int
    description: str | None
    author_name: str | None
    any_sp_victory: bool
    active_player_count: int
    dlc_options: DLCOptions | None

    @classmethod
    def read_from(cls, r: Reader, format_version: SCXVersion) -> "SCXHeader":
        _header_size = r.u32()
        version = r.u32()
        timestamp = r.u32() if version >= 2 else 0
        if format_version.raw == b"3.13":
            description = r.read_hd_style_str()
        else:
            description = r.read_u32_length_prefixed_str()
        any_sp_victory = r.u32() != 0
        active_player_count = r.u32()
        dlc_options = None
        if version > 2 and format_version.raw != b"3.13":
            dlc_options = DLCOptions.read_from(r)
        author_name = None
        if version >= 5:
            author_name = r.read_u32_length_prefixed_str()
            _num_triggers = r.u32()
        return cls(
            version=version,
            timestamp=timestamp,
            description=description,
            author_name=author_name,
            any_sp_victory=any_sp_victory,
            active_player_count=active_player_count,
            dlc_options=dlc_options,
        )


@dataclass
class Tile:
    terrain: int
    elevation: int
    zone: int
    mask_type: int | None
    layered_terrain: int | None


@dataclass
class Map:
    version: int
    width: int
    height: int
    render_waves: bool
    tiles: list[Tile]

    @classmethod
    def read_from(cls, r: Reader) -> "Map":
        first = r.u32()
        if first == 0xDEADF00D:
            version = r.u32()
            if version < 2:
                render_waves = True
            else:
                render_waves = r.u8() == 0
            width = r.u32()
            height = r.u32()
        else:
            version = 0
            render_waves = True
            width = first
            height = r.u32()

        if width > 500 or height > 500:
            raise ValueError(f"unexpected map size {width}x{height}")

        tiles: list[Tile] = []
        for _y in range(height):
            for _x in range(width):
                terrain = r.u8()
                elevation = r.i8()
                zone = r.i8()
                mask_type = None
                layered_terrain = None
                if version >= 1:
                    mt = r.u16()
                    lt = r.u16()
                    mask_type = None if mt == 0xFFFF else mt
                    layered_terrain = None if lt == 0xFFFF else lt
                tiles.append(
                    Tile(
                        terrain=terrain,
                        elevation=elevation,
                        zone=zone,
                        mask_type=mask_type,
                        layered_terrain=layered_terrain,
                    )
                )
        return cls(
            version=version, width=width, height=height, render_waves=render_waves, tiles=tiles
        )


@dataclass
class ScenarioObject:
    position: tuple[float, float, float]
    id: int
    object_type: int
    state: int
    angle: float
    frame: int
    garrisoned_in: int | None


def _read_scenario_object(r: Reader, version: SCXVersion) -> ScenarioObject:
    x = r.f32()
    y = r.f32()
    z = r.f32()
    oid = r.i32()
    object_type = r.u16()
    state = r.u8()
    angle = r.f32()
    frame = -1 if version < SCXVersion(b"1.15") else r.i16()
    garrisoned_in: int | None = None
    if version >= SCXVersion(b"1.13"):
        g = r.i32()
        if g in (-1, 0) and version > SCXVersion(b"1.12"):
            garrisoned_in = None
        else:
            garrisoned_in = None if g == -1 else g
    return ScenarioObject(
        position=(x, y, z),
        id=oid,
        object_type=object_type,
        state=state,
        angle=angle,
        frame=frame,
        garrisoned_in=garrisoned_in,
    )


# --- Full-format structures ----------------------------------------------------


@dataclass
class ScenarioPlayerData:
    name: str | None
    view: tuple[float, float]
    location: tuple[int, int]
    allied_victory: bool
    relations: list[int]
    unit_diplomacy: list[int]
    color: int | None
    victory: Any


def _read_scenario_player_data(r: Reader, player_version: float) -> ScenarioPlayerData:
    name = r.read_u16_length_prefixed_str()
    view = (r.f32(), r.f32())
    location = (r.i16(), r.i16())
    allied_victory = (r.u8() != 0) if player_version > 1.0 else False
    diplo_count = r.i16()
    relations = [r.i8() for _ in range(diplo_count)]
    if player_version >= 1.08:
        unit_diplomacy = [r.i32() for _ in range(9)]
    else:
        unit_diplomacy = [0] * 9
    color = r.i32() if player_version >= 1.13 else None
    # VictoryConditions is large; we parse and store raw fields minimally for now.
    # (Still consumes correctly to keep cursor aligned.)
    victory = VictoryConditions.read_from(r, has_version=(player_version >= 1.09))
    return ScenarioPlayerData(
        name=name,
        view=view,
        location=location,
        allied_victory=allied_victory,
        relations=relations,
        unit_diplomacy=unit_diplomacy,
        color=color,
        victory=victory,
    )


@dataclass
class VictoryEntry:
    command: int
    object_type: int
    player_id: int
    x0: float
    y0: float
    x1: float
    y1: float
    number: int
    count: int
    source_object: int
    target_object: int
    victory_group: int
    ally_flag: int
    state: int

    @classmethod
    def read_from(cls, r: Reader) -> "VictoryEntry":
        command = r.u8()
        object_type = r.i32()
        player_id = r.i32()
        x0, y0, x1, y1 = r.f32(), r.f32(), r.f32(), r.f32()
        number = r.i32()
        count = r.i32()
        source_object = r.i32()
        target_object = r.i32()
        victory_group = r.i8()
        ally_flag = r.i8()
        state = r.i8()
        return cls(
            command=command,
            object_type=object_type,
            player_id=player_id,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            number=number,
            count=count,
            source_object=source_object,
            target_object=target_object,
            victory_group=victory_group,
            ally_flag=ally_flag,
            state=state,
        )


@dataclass
class VictoryPointEntry:
    command: int
    state: int
    attribute: int
    amount: int
    points: int
    current_points: int
    id: int
    group: int
    current_attribute_amount: float
    attribute1: int
    current_attribute_amount1: float

    @classmethod
    def read_from(cls, r: Reader, version: float) -> "VictoryPointEntry":
        command = r.i8()
        state = r.i8()
        attribute = r.i32()
        amount = r.i32()
        points = r.i32()
        current_points = r.i32()
        id_ = r.i8()
        group = r.i8()
        current_attribute_amount = r.f32()
        if version >= 2.0:
            attribute1 = r.i32()
            current_attribute_amount1 = r.f32()
        else:
            attribute1 = -1
            current_attribute_amount1 = 0.0
        return cls(
            command=command,
            state=state,
            attribute=attribute,
            amount=amount,
            points=points,
            current_points=current_points,
            id=id_,
            group=group,
            current_attribute_amount=current_attribute_amount,
            attribute1=attribute1,
            current_attribute_amount1=current_attribute_amount1,
        )


@dataclass
class VictoryConditions:
    version: float
    victory: int
    total_points: int
    starting_points: int
    starting_group: int
    entries: list[VictoryEntry]
    point_entries: list[VictoryPointEntry]

    @classmethod
    def read_from(cls, r: Reader, *, has_version: bool) -> "VictoryConditions":
        version = r.f32() if has_version else 0.0
        num_conditions = r.i32()
        victory = r.u8()
        entries = [VictoryEntry.read_from(r) for _ in range(num_conditions)]
        total_points = 0
        point_entries: list[VictoryPointEntry] = []
        starting_points = 0
        starting_group = 0
        if version >= 1.0:
            total_points = r.i32()
            num_point_entries = r.i32()
            if version >= 2.0:
                starting_points = r.i32()
                starting_group = r.i32()
            for _ in range(num_point_entries):
                point_entries.append(VictoryPointEntry.read_from(r, version))
        return cls(
            version=version,
            victory=victory,
            total_points=total_points,
            starting_points=starting_points,
            starting_group=starting_group,
            entries=entries,
            point_entries=point_entries,
        )


@dataclass
class TriggerSystem:
    version: float
    num_triggers: int
    raw: Any


def _read_trigger_system(r: Reader) -> TriggerSystem:
    version = r.f64()
    objectives_state = r.i8() if version >= 1.5 else 0
    num_triggers = r.i32()
    triggers = [_read_trigger(r, version) for _ in range(num_triggers)]
    if version >= 1.4:
        trigger_order = [r.i32() for _ in range(num_triggers)]
    else:
        trigger_order = list(range(num_triggers))

    variable_values: list[int] = []
    enabled_techs: list[int] = []
    variable_names: list[str] = []
    if version >= 2.2:
        variable_values = [r.u32() for _ in range(256)]
        n_enabled = r.u32()
        enabled_techs = [r.u32() for _ in range(n_enabled)]
        n_var_names = r.u32()
        variable_names = [""] * 256
        for _ in range(n_var_names):
            idx = r.u32()
            name = r.read_u32_length_prefixed_str() or ""
            if idx < 256:
                variable_names[idx] = name

    return TriggerSystem(
        version=version,
        num_triggers=len(triggers),
        raw={
            "objectives_state": objectives_state,
            "triggers": triggers,
            "trigger_order": trigger_order,
            "enabled_techs": enabled_techs,
            "variable_values": variable_values,
            "variable_names": variable_names,
        },
    )


@dataclass
class AIInfo:
    raw: Any


def _read_ai_info(r: Reader) -> AIInfo | None:
    # Port of ai.rs. Implement minimal, cursor-correct read.
    has_ai_files = r.u32() != 0
    has_error = r.u32() != 0
    if not has_ai_files and not has_error:
        return None
    if has_error:
        _filename = r.read(257)
        _line = r.i32()
        _desc = r.read(128)
        _code = r.u32()
    num_ai_files = r.u32()
    for _ in range(num_ai_files):
        _fn = r.read_u32_length_prefixed_str()
        _content = r.read_u32_length_prefixed_str()
    return AIInfo(raw=True)


@dataclass
class TribeScen:
    base: Any


def _read_tribe_scen(r: Reader) -> TribeScen:
    base = _read_rge_scen(r)
    version = base["version"]

    player_start_resources = [_default_player_start_resources() for _ in range(16)]

    # Moved to RGEScen in 1.13
    if version <= 1.13:
        base["player_names"] = [r.read_str_len(256) for _ in range(16)]
        pprops = base["player_base_properties"]
        for i in range(16):
            pprops[i]["active"] = r.i32()
            player_start_resources[i] = _read_player_start_resources(r, version)
            pprops[i]["player_type"] = r.i32()
            pprops[i]["civilization"] = r.i32()
            pprops[i]["posture"] = r.i32()
    else:
        for i in range(16):
            player_start_resources[i] = _read_player_start_resources(r, version)

    if version >= 1.02:
        sep = r.i32()
        # debug assert -99

    victory = _read_victory_info(r)
    victory_all_flag = r.i32() != 0
    mp_victory_type = r.i32() if version >= 1.13 else 4
    victory_score = r.i32() if version >= 1.13 else 900
    victory_time = r.i32() if version >= 1.13 else 9000

    diplomacy = [[r.i32() for _ in range(16)] for _ in range(16)]

    legacy_victory_info = [[_read_legacy_victory_info(r) for _ in range(12)] for _ in range(16)]

    if version >= 1.02:
        _sep2 = r.i32()

    allied_victory = [r.i32() for _ in range(16)]

    if version >= 1.24:
        teams_locked = r.i8() != 0
        can_change_teams = r.i8() != 0
        random_start_locations = r.i8() != 0
        max_teams = r.u8()
    elif abs(version - 1.23) < 1e-6:
        teams_locked = r.i32() != 0
        can_change_teams = True
        random_start_locations = True
        max_teams = 4
    else:
        teams_locked = False
        can_change_teams = True
        random_start_locations = True
        max_teams = 4

    num_disabled_techs = [0] * 16
    disabled_techs: list[list[int]] = [[] for _ in range(16)]
    num_disabled_units = [0] * 16
    disabled_units: list[list[int]] = [[] for _ in range(16)]
    num_disabled_buildings = [0] * 16
    disabled_buildings: list[list[int]] = [[] for _ in range(16)]

    if version >= 1.28:
        num_disabled_techs = [r.i32() for _ in range(16)]
        for i, n in enumerate(num_disabled_techs):
            disabled_techs[i] = [r.i32() for _ in range(max(0, n))]
        num_disabled_units = [r.i32() for _ in range(16)]
        for i, n in enumerate(num_disabled_units):
            disabled_units[i] = [r.i32() for _ in range(max(0, n))]
        num_disabled_buildings = [r.i32() for _ in range(16)]
        for i, n in enumerate(num_disabled_buildings):
            disabled_buildings[i] = [r.i32() for _ in range(max(0, n))]
    elif version >= 1.18:
        num_disabled_techs = [r.i32() for _ in range(16)]
        for i in range(16):
            disabled_techs[i] = [r.i32() for _ in range(30)]
        num_disabled_units = [r.i32() for _ in range(16)]
        for i in range(16):
            disabled_units[i] = [r.i32() for _ in range(30)]
        num_disabled_buildings = [r.i32() for _ in range(16)]
        max_disabled_buildings = 30 if version >= 1.25 else 20
        for i in range(16):
            disabled_buildings[i] = [r.i32() for _ in range(max_disabled_buildings)]
    elif version > 1.03:
        for i in range(16):
            arr = [r.i32() for _ in range(20)]
            disabled_techs[i] = arr
            try:
                num_disabled_techs[i] = next((j + 1 for j, v in enumerate(arr) if v <= 0), 0)
            except Exception:
                num_disabled_techs[i] = 0

    combat_mode = r.i32() if version > 1.04 else 0
    if version >= 1.12:
        naval_mode = r.i32()
        all_techs = r.i32() != 0
    else:
        naval_mode = 0
        all_techs = False

    player_start_ages = [_starting_age_from_i32(r.i32(), version) for _ in range(16)] if version > 1.05 else [0]*16

    if version >= 1.02:
        _sep3 = r.i32()

    view = (r.i32(), r.i32()) if version >= 1.19 else (-1, -1)

    if version >= 1.21:
        mt = r.i32()
        map_type = None if mt in (-2, -1) else mt
    else:
        map_type = None

    base_priorities = [r.i8() for _ in range(16)] if version >= 1.24 else [0]*16

    water_definition = None
    color_mood = None
    collide_and_correct = False
    villager_force_drop = False

    if version >= 1.35:
        _trigger_count = r.u32()
    if version >= 1.30:
        _sig = r.u16()
        water_definition = r.read_u16_length_prefixed_str()
    if version >= 1.32:
        _sig2 = r.u16()
        color_mood = r.read_u16_length_prefixed_str()
    if version >= 1.36:
        collide_and_correct = r.u8() != 0
    if version >= 1.37:
        villager_force_drop = r.u8() != 0

    return TribeScen(
        base={
            "base": base,
            "player_start_resources": player_start_resources,
            "victory": victory,
            "victory_all_flag": victory_all_flag,
            "mp_victory_type": mp_victory_type,
            "victory_score": victory_score,
            "victory_time": victory_time,
            "diplomacy": diplomacy,
            "legacy_victory_info": legacy_victory_info,
            "allied_victory": allied_victory,
            "teams_locked": teams_locked,
            "can_change_teams": can_change_teams,
            "random_start_locations": random_start_locations,
            "max_teams": max_teams,
            "num_disabled_techs": num_disabled_techs,
            "disabled_techs": disabled_techs,
            "num_disabled_units": num_disabled_units,
            "disabled_units": disabled_units,
            "num_disabled_buildings": num_disabled_buildings,
            "disabled_buildings": disabled_buildings,
            "combat_mode": combat_mode,
            "naval_mode": naval_mode,
            "all_techs": all_techs,
            "player_start_ages": player_start_ages,
            "view": view,
            "map_type": map_type,
            "base_priorities": base_priorities,
            "water_definition": water_definition,
            "color_mood": color_mood,
            "collide_and_correct": collide_and_correct,
            "villager_force_drop": villager_force_drop,
        }
    )


@dataclass
class Scenario:
    format_version: SCXVersion
    header: SCXHeader
    next_object_id: int
    tribe_scen: Any
    map: Map
    world_players: list[Any]
    player_objects: list[list[ScenarioObject]]
    scenario_players: list[ScenarioPlayerData]
    triggers: Any
    ai_info: Any

    @classmethod
    def read_from_bytes(cls, data: bytes) -> "Scenario":
        r0 = Reader(data)
        fmt = SCXVersion(r0.read(4))
        player_version = fmt.to_player_version()
        if player_version is None:
            raise ValueError(f"unsupported format version: {fmt.as_str()!r}")
        header = SCXHeader.read_from(r0, fmt)

        # Remaining bytes are raw DEFLATE stream (no zlib wrapper).
        comp = data[r0.tell() :]
        decomp = zlib.decompress(comp, wbits=-zlib.MAX_WBITS)
        r = Reader(decomp)

        next_object_id = r.i32()
        tribe_scen = _read_tribe_scen(r)
        m = Map.read_from(r)

        num_players = r.u32()
        world_players = []
        for _ in range(1, num_players):
            world_players.append(_read_world_player_data(r, player_version))

        # Objects vs players order depends on 1.36+ in Rust, but we stop before that.
        player_objects = _read_player_objects(r, num_players, fmt)
        scenario_players = _read_scenario_players(r, player_version)

        triggers = None
        if fmt >= SCXVersion(b"1.14"):
            triggers = _read_trigger_system(r)
        ai_info = None
        if fmt > SCXVersion(b"1.17") and fmt < SCXVersion(b"2.00"):
            ai_info = _read_ai_info(r)

        return cls(
            format_version=fmt,
            header=header,
            next_object_id=next_object_id,
            tribe_scen=tribe_scen,
            map=m,
            world_players=world_players,
            player_objects=player_objects,
            scenario_players=scenario_players,
            triggers=triggers,
            ai_info=ai_info,
        )

    @classmethod
    def from_file(cls, path: str) -> "Scenario":
        with open(path, "rb") as f:
            return cls.read_from_bytes(f.read())


def _read_world_player_data(r: Reader, version: float) -> dict[str, float]:
    food = r.f32() if version > 1.06 else 200.0
    wood = r.f32() if version > 1.06 else 200.0
    gold = r.f32() if version > 1.06 else 50.0
    stone = r.f32() if version > 1.06 else 100.0
    ore = r.f32() if version > 1.12 else 100.0
    goods = r.f32() if version > 1.12 else 0.0
    pop = r.f32() if version >= 1.14 else 75.0
    return {
        "food": food,
        "wood": wood,
        "gold": gold,
        "stone": stone,
        "ore": ore,
        "goods": goods,
        "population": pop,
    }


def _read_scenario_players(r: Reader, player_version: float) -> list[ScenarioPlayerData]:
    num = r.u32()
    out = []
    for _ in range(1, num):
        out.append(_read_scenario_player_data(r, player_version))
    return out


def _read_player_objects(r: Reader, num_players: int, version: SCXVersion) -> list[list[ScenarioObject]]:
    out: list[list[ScenarioObject]] = []
    for _ in range(num_players):
        num_objects = r.u32()
        objs = [_read_scenario_object(r, version) for _ in range(num_objects)]
        out.append(objs)
    return out


