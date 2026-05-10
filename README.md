# McMinimap

Static isometric minimaps for **Age of Empires II** — from **recorded games** (`.aoe2record`, `.mgz`, …) or **scenarios** (`.aoe2scenario`, `.scx`, `.scn`). Use it as a **CLI** or import it from **Python**.

Used for [Button Bash](https://www.youtube.com/@buttonbashofficial) YouTube intros.

![Sample minimap](readme/example1.png)

---

## What you can tweak

- Map **rotation** and **scale** (tile multiplier)
- **Square** vs **rotated** object drawing
- Toggle **players**, **gaia**, **food**, **gold**, **stone**, **relics**, **cliffs**, **walls**
- **Orthographic ratio** (how “flat” the tilt looks)
- **Border** styling around the map
- Optional **town-center markers**: none, **pixel** (default), or **civilization emblem** PNGs

![Another style](readme/example2.png)

---

## Install

Clone the repo, create a venv if you like, then:

```bash
pip install -r requirements.txt
```

Recorded games try, in order: **happyleaves header-only** (`legacy/mgz_legacy/summary/mcminimap_light.py`), then vendored **`FullSummary`**, then pip [AoEInsights mgz-fast](https://github.com/AoEInsights/mgz-fast) (`mgz.fast.header.parse`). No PyPI `mgz` (happyleaves) install.

Classic **`.scn` / `.scx`** scenarios use [genie-scx-py](https://github.com/UnluckyForSome/genie-scx-py) (Rust-aligned pure Python parser). **`.aoe2scenario`** uses [AoE2ScenarioParser](https://github.com/KSneijders/AoE2ScenarioParser).

---

## Command line

**One file → one PNG**

```bash
python McMinimap.py --input "match.aoe2record" --output minimap.png
```

**Folder → many PNGs** (recursive; output tree mirrors input)

```bash
python McMinimap.py --input ./replays --output ./pngs
```

**Common flags** (defaults match a typical “full map” render):

```bash
python McMinimap.py --input map.aoe2scenario --output out.png ^
  --object_mode square ^
  --angle 45 --multiplier_integer 9 --orthographic_ratio 2 --border_spacing 4 ^
  --draw-cliffs --draw-walls --smooth-walls --draw-gaia --draw-players ^
  --draw-food --draw-gold --draw-stone --draw-relics
```

On **Linux/macOS**, replace `^` with `\` for line continuation, or put everything on one line.

Default is **`--town-center pixel`** (small TC marker per player color). Use **`--town-center none`** to disable TC markers, or **`--town-center emblem`** for civ PNGs from `emblems/` next to `McMinimap.py` (`Britons.png`, …). Override with `--emblems-dir /path/to/pngs`.

---

## Python

**PNG bytes** (e.g. for a web app or buffer):

```python
from McMinimap import MinimapSettings, to_png_bytes

settings = MinimapSettings(angle=45, multiplier_integer=9)
png = to_png_bytes("scenario.aoe2scenario", settings=settings)
with open("out.png", "wb") as f:
    f.write(png)
```

**Save a PNG with explicit settings:**

```python
from McMinimap import MinimapSettings, to_image

to_image(
    "match.aoe2record",
    settings=MinimapSettings(town_center="none"),  # default is pixel; omit MinimapSettings() for defaults
).save("minimap.png")
```

**Read map / player data** without rendering (for your own tooling):

```python
from McMinimap import read_map

m = read_map("match.aoe2record")
dim = m.map.dimension
players = m.players
gaia = m.gaia
```

`MinimapSettings` is a frozen dataclass: pass only the fields you care about; the rest use built-in defaults (see `McMinimap.py` near `class MinimapSettings`).

![Rendered example](readme/example3.png)

---

## Supported files

| Kind | Extensions |
|------|------------|
| Recorded games | `.aoe2record`, `.mgz`, `.mgx`, `.mgl` |
| DE scenarios | `.aoe2scenario` |
| Classic scenarios | `.scx` (The Conquerors), `.scn` (Age of Kings) |

Anything else raises `ValueError` from `read_map()`.

---

## Data under `data/`

Rendering uses **`data/mcminimap_constants.json`** (terrain colors, object ID sets, civilization names for replay headers via `civilizations_by_id`). That file ships with the repo.

---

## Thanks

Inspired by **Marfullsen**’s [AoE2 minimap generator](https://github.com/Marfullsen/AoE2-minimap-generator). Replay parsing uses a vendored copy of **happyleaves** [aoc-mgz](https://github.com/happyleavesaoc/aoc-mgz) under `legacy/mgz_legacy/` and **AoEInsights** [mgz-fast](https://github.com/AoEInsights/mgz-fast) from PyPI.

![Sample minimap](readme/example4.png)
