"""Rendering helpers and high-level image APIs."""

from __future__ import annotations

from dataclasses import dataclass
import io
import math
from types import SimpleNamespace

from PIL import Image, ImageDraw

from . import settings as render_settings
from .readers import match_from_parsed_scenario, read_map
from .resources import (
    TOWN_CENTER_OBJECT_IDS,
    cliff_objects,
    food_objects,
    gold_objects,
    player_colors,
    relic_objects,
    resolve_emblems_dir,
    stone_objects,
    tiles_colors,
    wall_objects,
)
from .settings import MinimapSettings, _apply_settings


def rotate_coordinates(
    pixel_coordinates_x,
    pixel_coordinates_y,
    original_map_dimension,
    new_canvas_dimension,
    performed_after_enlargement,
):
    mi = render_settings.multiplier_integer
    x_centered = pixel_coordinates_x - (original_map_dimension / 2)
    y_centered = pixel_coordinates_y - (original_map_dimension / 2)
    x_transformed = x_centered * math.cos(math.radians(-render_settings.angle)) - y_centered * math.sin(
        math.radians(-render_settings.angle)
    )
    y_transformed = x_centered * math.sin(math.radians(-render_settings.angle)) + y_centered * math.cos(
        math.radians(-render_settings.angle)
    )
    x_transformed += new_canvas_dimension / 2
    y_transformed += new_canvas_dimension / 2
    if performed_after_enlargement is False:
        mi = 1
    x_transformed = x_transformed * mi + (new_canvas_dimension - new_canvas_dimension * mi) / 2
    y_transformed = y_transformed * mi + (new_canvas_dimension - new_canvas_dimension * mi) / 2
    return math.floor(x_transformed), math.floor(y_transformed)


def to_rgb(farbe: str) -> tuple[int, int, int]:
    return tuple(int(farbe[i : i + 2], 16) for i in (0, 2, 4))


def _object_canvas_xy(tile_x, tile_y, original_map_dimension, canvas, after_rotation):
    if after_rotation:
        coords = rotate_coordinates(
            tile_x,
            tile_y,
            original_map_dimension,
            canvas.height * render_settings.orthographic_ratio,
            performed_after_enlargement=True,
        )
        return coords[0], coords[1] / render_settings.orthographic_ratio
    mi = render_settings.multiplier_integer
    padding = render_settings.border_spacing * mi
    return tile_x * mi + padding, tile_y * mi + padding


def _draw_square_marker(draw, cx, cy, size_addon, fill):
    offset = 1 if render_settings.multiplier_integer % 2 == 0 else 0
    half = math.floor(render_settings.multiplier_integer / 2) + size_addon
    draw.rectangle(
        [cx - half, cy - half, cx + (half - offset), cy + (half - offset)],
        fill=fill,
    )


@dataclass(frozen=True)
class _RenderPlan:
    draw_player_objects_layer: bool
    player_object_size_addon: int
    draw_tc_pixel_markers: bool
    draw_civ_emblems: bool


def _build_render_plan() -> _RenderPlan:
    return _RenderPlan(
        draw_player_objects_layer=render_settings.draw_players,
        player_object_size_addon=render_settings.player_object_size,
        draw_tc_pixel_markers=render_settings.town_center == "pixel",
        draw_civ_emblems=render_settings.town_center == "emblem",
    )


def draw_terrain_straight(canvas, map_obj):
    default_terrain_color = {"normal": "#339727", "shady": "#008d00", "sunny": "#00a900"}
    unknown_terrain_ids: set = set()
    dim = map_obj.dimension
    tiles = map_obj.tiles
    bs = render_settings.border_spacing
    px = canvas.load()
    d1 = dim + bs - 1

    for i in range(dim * dim):
        t = tiles[i]
        x = t.position.x + bs
        y = t.position.y + bs
        terrain = t.terrain

        if terrain not in tiles_colors:
            if terrain not in unknown_terrain_ids:
                unknown_terrain_ids.add(terrain)
                print(
                    f"Warning: Terrain ID {terrain} not found in tiles_colors dictionary. Using default color."
                )
            terrain_color = default_terrain_color
        else:
            terrain_color = tiles_colors[terrain]

        r, g, b = to_rgb(terrain_color["normal"][1:])
        px[x, y] = (r, g, b, 255)

        if x < d1 and y < d1:
            br = tiles[i + dim + 1]
            if br.elevation < t.elevation:
                r, g, b = to_rgb(terrain_color["sunny"][1:])
                px[x, y] = (r, g, b, 255)
            elif br.elevation > t.elevation:
                r, g, b = to_rgb(terrain_color["shady"][1:])
                px[x, y] = (r, g, b, 255)


def draw_permenant_objects(canvas, gaia, players):
    draw = ImageDraw.Draw(canvas)

    if render_settings.draw_cliffs:
        bs = render_settings.border_spacing
        for unit in gaia:
            if unit.object_id in cliff_objects:
                cx = unit.position.x + bs
                cy = unit.position.y + bs
                s = render_settings.cliff_size
                draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill="#714b33")

    if render_settings.draw_walls and render_settings.smooth_walls:
        bs = render_settings.border_spacing
        s = render_settings.player_wall_size
        for player in players:
            col = to_rgb(player_colors[player.color_id][1:])
            for unit in player.objects:
                if unit.object_id in wall_objects:
                    cx = unit.position.x + bs
                    cy = unit.position.y + bs
                    draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=col)


def draw_gaia_objects_common(canvas, gaia, original_map_dimension, after_rotation):
    if not render_settings.draw_gaia:
        return
    draw = ImageDraw.Draw(canvas)
    rules = []
    if render_settings.draw_food:
        rules.append((food_objects, "#A5C46C", render_settings.food_size))
    if render_settings.draw_stone:
        rules.append((stone_objects, "#919191", render_settings.stone_size))
    if render_settings.draw_gold:
        rules.append((gold_objects, "#FFC700", render_settings.gold_size))
    if render_settings.draw_relics:
        rules.append((relic_objects, "#FFFFFF", render_settings.relic_size))
    if not rules:
        return

    for unit in gaia:
        oid = unit.object_id
        for id_set, color, size_addon in rules:
            if oid in id_set:
                cx, cy = _object_canvas_xy(
                    unit.position.x, unit.position.y, original_map_dimension, canvas, after_rotation
                )
                _draw_square_marker(draw, cx, cy, size_addon, color)
                break


def draw_player_objects_common(
    canvas, players, original_map_dimension, after_rotation, player_object_size_addon: int
):
    draw = ImageDraw.Draw(canvas)

    for player in players:
        col = to_rgb(player_colors[player.color_id][1:])
        for unit in player.objects:
            if unit.object_id in TOWN_CENTER_OBJECT_IDS:
                continue
            if getattr(unit, "class_id", None) != 80 or unit.object_id not in wall_objects:
                cx, cy = _object_canvas_xy(
                    unit.position.x, unit.position.y, original_map_dimension, canvas, after_rotation
                )
                _draw_square_marker(draw, cx, cy, player_object_size_addon, col)


def draw_player_walls_common(canvas, players, original_map_dimension, after_rotation):
    draw = ImageDraw.Draw(canvas)

    for player in players:
        col = to_rgb(player_colors[player.color_id][1:])
        for unit in player.objects:
            if unit.object_id in wall_objects:
                cx, cy = _object_canvas_xy(
                    unit.position.x, unit.position.y, original_map_dimension, canvas, after_rotation
                )
                _draw_square_marker(draw, cx, cy, render_settings.player_wall_size, col)


def draw_player_tcs(canvas, players, original_map_dimension, after_rotation):
    draw = ImageDraw.Draw(canvas)

    for player in players:
        if player.position.x is None or player.position.y is None:
            continue
        col = to_rgb(player_colors[player.color_id][1:])
        cx, cy = _object_canvas_xy(
            player.position.x, player.position.y, original_map_dimension, canvas, after_rotation
        )
        _draw_square_marker(draw, cx, cy, render_settings.town_center_size, col)


def create_border_canvas(original_map_dimension):
    border_canvas = Image.new("RGBA", (original_map_dimension, original_map_dimension))
    draw = ImageDraw.Draw(border_canvas)
    w, h = border_canvas.width - 1, border_canvas.height - 1
    draw.rectangle([(0, 0), (w, h)], outline="rgb(0, 0, 0)", width=1)
    draw.rectangle([(1, 1), (w - 1, h - 1)], outline="rgb(157, 135, 114)", width=1)
    draw.rectangle([(2, 2), (w - 2, h - 2)], outline="rgb(215, 182, 151)", width=1)
    draw.rectangle([(3, 3), (w - 3, h - 3)], outline="rgb(31, 31, 31)", width=1)

    edge = (original_map_dimension + render_settings.border_spacing * 2) * render_settings.multiplier_integer
    border_canvas = border_canvas.resize(
        (edge, edge),
        resample=Image.Resampling.NEAREST,
    )
    border_canvas = border_canvas.rotate(
        render_settings.angle, resample=Image.Resampling.BILINEAR, expand=True
    )
    border_canvas = border_canvas.resize(
        (border_canvas.size[0], border_canvas.size[1] // render_settings.orthographic_ratio),
        resample=Image.Resampling.LANCZOS,
    )
    return border_canvas


def new_canvas(original_map_dimension):
    return Image.new(
        "RGBA",
        (
            original_map_dimension + 2 * render_settings.border_spacing,
            original_map_dimension + 2 * render_settings.border_spacing,
        ),
    )


def create_transparency_mask(canvas):
    return canvas.getchannel("A").point(lambda p: 255 if p == 0 else 0)


def render_match(
    match: SimpleNamespace,
    *,
    output_path: str | None = None,
    final_size: tuple[int, int] | None = None,
):
    """Render a minimap from an in-memory ``match`` (same shape as ``read_map`` returns)."""
    map_obj = match.map
    players = match.players
    gaia = match.gaia
    original_map_dimension = map_obj.dimension

    plan = _build_render_plan()

    canvas = new_canvas(original_map_dimension)
    draw_terrain_straight(canvas, map_obj)
    draw_permenant_objects(canvas, gaia, players)

    canvas = canvas.resize(
        (
            (original_map_dimension + render_settings.border_spacing * 2)
            * render_settings.multiplier_integer,
            (original_map_dimension + render_settings.border_spacing * 2)
            * render_settings.multiplier_integer,
        ),
        resample=Image.Resampling.NEAREST,
    )

    if render_settings.object_mode == "rotated":
        draw_gaia_objects_common(canvas, gaia, original_map_dimension, after_rotation=False)

        if plan.draw_player_objects_layer:
            draw_player_objects_common(
                canvas,
                players,
                original_map_dimension,
                after_rotation=False,
                player_object_size_addon=plan.player_object_size_addon,
            )

        if render_settings.draw_walls and not render_settings.smooth_walls:
            draw_player_walls_common(canvas, players, original_map_dimension, after_rotation=False)

        if plan.draw_tc_pixel_markers:
            draw_player_tcs(canvas, players, original_map_dimension, after_rotation=False)

        canvas = canvas.rotate(
            render_settings.angle, resample=Image.Resampling.BILINEAR, expand=True
        )
        canvas = canvas.resize(
            (canvas.size[0], canvas.size[1] // render_settings.orthographic_ratio),
            resample=Image.Resampling.LANCZOS,
        )

    if render_settings.object_mode == "square":
        canvas = canvas.rotate(
            render_settings.angle, resample=Image.Resampling.BILINEAR, expand=True
        )
        canvas = canvas.resize(
            (canvas.size[0], canvas.size[1] // render_settings.orthographic_ratio),
            resample=Image.Resampling.LANCZOS,
        )

        original_canvas = canvas.copy()
        transparency_mask = create_transparency_mask(original_canvas)

        draw_gaia_objects_common(canvas, gaia, original_map_dimension, after_rotation=True)

        if plan.draw_player_objects_layer:
            draw_player_objects_common(
                canvas,
                players,
                original_map_dimension,
                after_rotation=True,
                player_object_size_addon=plan.player_object_size_addon,
            )

        if render_settings.draw_walls and not render_settings.smooth_walls:
            draw_player_walls_common(canvas, players, original_map_dimension, after_rotation=True)

        if plan.draw_tc_pixel_markers:
            draw_player_tcs(canvas, players, original_map_dimension, after_rotation=True)

        canvas.paste(original_canvas, mask=transparency_mask)

    border_canvas = create_border_canvas(original_map_dimension)

    if plan.draw_civ_emblems:
        civ_emblem_canvas = create_civ_icon_canvas(players, original_map_dimension)
        canvas.paste(civ_emblem_canvas, civ_emblem_canvas)

    canvas.paste(border_canvas, border_canvas)

    if final_size is not None:
        canvas = canvas.resize(final_size, resample=Image.Resampling.LANCZOS)

    if output_path:
        canvas.save(output_path)

    return canvas


def save_minimap(
    input_file: str,
    *,
    output_path: str | None = None,
    verbose: bool = False,
    final_size: tuple[int, int] | None = None,
):
    """Render a minimap from a recording or scenario."""
    if verbose:
        print(f"Input file: {input_file}")
    match = read_map(input_file)
    return render_match(match, output_path=output_path, final_size=final_size)


def to_image(input_file: str, *, settings: MinimapSettings | None = None):
    """Render to an in-memory PIL image."""
    s = settings or MinimapSettings()
    with _apply_settings(s):
        return save_minimap(input_file, output_path=None, verbose=False, final_size=s.final_size)


def to_image_from_match(match: SimpleNamespace, *, settings: MinimapSettings | None = None):
    """Like ``to_image`` but takes a prebuilt ``match``."""
    s = settings or MinimapSettings()
    with _apply_settings(s):
        return render_match(match, output_path=None, final_size=s.final_size)


def to_image_from_parsed_scenario(parsed_scenario, *, settings: MinimapSettings | None = None):
    """Render a parser-owned scenario result without re-reading the source file."""
    return to_image_from_match(match_from_parsed_scenario(parsed_scenario), settings=settings)


def to_png_bytes(input_file: str, *, settings: MinimapSettings | None = None) -> bytes:
    img = to_image(input_file, settings=settings)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def to_png_bytes_from_match(match: SimpleNamespace, *, settings: MinimapSettings | None = None) -> bytes:
    img = to_image_from_match(match, settings=settings)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def to_png_bytes_from_parsed_scenario(parsed_scenario, *, settings: MinimapSettings | None = None) -> bytes:
    img = to_image_from_parsed_scenario(parsed_scenario, settings=settings)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_civ_icon_canvas(players, original_map_dimension):
    civ_emblem_canvas = new_canvas(original_map_dimension)
    civ_emblem_canvas = civ_emblem_canvas.resize(
        (
            (original_map_dimension + render_settings.border_spacing * 2)
            * render_settings.multiplier_integer,
            (original_map_dimension + render_settings.border_spacing * 2)
            * render_settings.multiplier_integer,
        ),
        resample=Image.Resampling.NEAREST,
    )
    civ_emblem_canvas = civ_emblem_canvas.rotate(
        render_settings.angle, resample=Image.Resampling.BILINEAR, expand=True
    )

    emblems_root = resolve_emblems_dir(render_settings._render_emblems_dir)
    for player in players:
        if player.position.x is None or player.position.y is None:
            continue
        coords = rotate_coordinates(
            player.position.x,
            player.position.y,
            original_map_dimension,
            civ_emblem_canvas.height,
            performed_after_enlargement=True,
        )

        civ_path = emblems_root / f"{player.civilization}.png"
        if not civ_path.is_file():
            print(
                f"Warning: missing civ emblem {civ_path!s} (town_center=emblem); skipping marker for "
                f"{player.civilization!r}."
            )
            continue
        civ_image = Image.open(civ_path)

        image_width, image_height = civ_image.size
        top_left_coords = (
            math.floor(coords[0] - image_width / 2),
            math.floor(coords[1] - image_height / 2),
        )

        draw = ImageDraw.Draw(civ_emblem_canvas)
        radius = max(image_width, image_height) / 2 + render_settings.civ_emblem_halo
        center = (
            top_left_coords[0] + image_width / 2,
            top_left_coords[1] + image_height / 2,
        )
        draw.ellipse(
            [
                (center[0] - radius, center[1] - radius),
                (center[0] + radius, center[1] + radius),
            ],
            outline=(0, 0, 0),
            fill=to_rgb(player_colors[player.color_id][1:]),
            width=2,
        )

        civ_emblem_canvas.paste(civ_image, top_left_coords, civ_image)

    civ_emblem_canvas = civ_emblem_canvas.resize(
        (civ_emblem_canvas.size[0], civ_emblem_canvas.size[1] // render_settings.orthographic_ratio),
        resample=Image.Resampling.LANCZOS,
    )
    return civ_emblem_canvas


__all__ = [
    "render_match",
    "save_minimap",
    "to_image",
    "to_image_from_match",
    "to_png_bytes",
    "to_png_bytes_from_match",
]
