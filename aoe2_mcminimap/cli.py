"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .render import save_minimap
from .resources import DEFAULT_EMBLEMS_DIR, SUPPORTED_INPUT_SUFFIXES
from .settings import MAX_MULTIPLIER_INTEGER, MinimapSettings, _apply_settings


def _cli_collect_batch_jobs(input_dir: Path, output_dir: Path) -> list[tuple[Path, Path]]:
    """Pair each supported file under ``input_dir`` with a mirrored ``.png`` path."""
    jobs: list[tuple[Path, Path]] = []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
            continue
        rel = path.relative_to(input_dir)
        jobs.append((path, output_dir / rel.with_suffix(".png")))
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an AoE2 minimap from a scenario/recording.")
    parser.add_argument(
        "--input",
        required=False,
        help="Input file, or a directory (searched recursively for supported extensions).",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="Output PNG file, or when --input is a directory, the output directory (required for directories).",
    )
    parser.add_argument("--object_mode", choices=["square", "rotated"], default="square")
    parser.add_argument(
        "--town-center",
        dest="town_center",
        choices=["none", "pixel", "emblem"],
        default="pixel",
        help="TC marker: none, pixel (default), or emblem (PNG from --emblems-dir or bundled emblems/).",
    )
    parser.add_argument(
        "--emblems-dir",
        type=Path,
        default=None,
        help=f"Directory of civ emblem PNGs (default: {DEFAULT_EMBLEMS_DIR}).",
    )
    parser.add_argument("--angle", type=int, default=45)
    parser.add_argument(
        "--multiplier_integer",
        type=int,
        default=9,
        choices=range(1, MAX_MULTIPLIER_INTEGER + 1),
        help=f"Tile multiplier (1..{MAX_MULTIPLIER_INTEGER}); larger values increase output resolution and memory use.",
    )
    parser.add_argument("--orthographic_ratio", type=int, default=2)
    parser.add_argument("--border_spacing", type=int, default=4)
    parser.add_argument("--draw_cliffs", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw_walls", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--smooth-walls", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw-gaia", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw-players", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw-food", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw-gold", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw-stone", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--draw-relics", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--resize",
        nargs=2,
        type=int,
        metavar=("W", "H"),
        default=None,
        help="Optional final width and height in pixels (stretches to fit). Default: native size from render settings.",
    )
    args = parser.parse_args()

    if not args.input:
        parser.error("--input is required")

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        parser.error(f"Input path does not exist: {input_path}")

    settings = MinimapSettings(
        object_mode=args.object_mode,
        town_center=args.town_center,
        angle=args.angle,
        multiplier_integer=args.multiplier_integer,
        orthographic_ratio=args.orthographic_ratio,
        border_spacing=args.border_spacing,
        draw_players=args.draw_players,
        draw_gaia=args.draw_gaia,
        draw_food=args.draw_food,
        draw_gold=args.draw_gold,
        draw_stone=args.draw_stone,
        draw_relics=args.draw_relics,
        draw_cliffs=args.draw_cliffs,
        draw_walls=args.draw_walls,
        smooth_walls=args.smooth_walls,
        emblems_dir=args.emblems_dir,
        final_size=tuple(args.resize) if args.resize else None,
    )

    with _apply_settings(settings):
        if input_path.is_dir():
            if not args.output:
                parser.error("When --input is a directory, --output must be the destination directory.")
            out_root = Path(args.output).expanduser().resolve()
            if out_root.exists() and not out_root.is_dir():
                parser.error("When --input is a directory, --output must be a directory path.")
            out_root.mkdir(parents=True, exist_ok=True)
            input_root = input_path.resolve()
            jobs = _cli_collect_batch_jobs(input_root, out_root)
            if not jobs:
                print(
                    f"No supported files under {input_root} "
                    f"(extensions: {', '.join(sorted(SUPPORTED_INPUT_SUFFIXES))})."
                )
                sys.exit(1)
            print(f"Rendering {len(jobs)} file(s) from {input_root} into {out_root}")
            failures: list[tuple[Path, str]] = []
            ok_count = 0
            for src, dest in jobs:
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    save_minimap(
                        str(src), output_path=str(dest), verbose=True, final_size=settings.final_size
                    )
                    ok_count += 1
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                    failures.append((src, err))
                    print(f"FAILED ({err})")
            print(f"\nBatch finished: {ok_count} succeeded, {len(failures)} failed (of {len(jobs)}).")
            if failures:
                print("Failed files:")
                for path, msg in failures:
                    print(f"  {path}\n    {msg}")
                sys.exit(1)
        else:
            save_minimap(
                str(input_path),
                output_path=args.output,
                verbose=True,
                final_size=settings.final_size,
            )


if __name__ == "__main__":
    main()
