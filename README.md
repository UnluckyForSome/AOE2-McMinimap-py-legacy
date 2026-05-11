# AOE2-McMinimap

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

From [PyPI](https://pypi.org/project/aoe2-mcminimap/) for **AOE2-McMinimap**:

```bash
pip install aoe2-mcminimap
```

That installs **AOE2-McGenieSCX**,
**AoE2ScenarioParser**, and the Museum-maintained
**`AOE2-McMGZ`** recorded-game parser automatically.

**Development** (editable install from a clone):

```bash
pip install -e .
```

Recorded games use the Museum-maintained
[**AOE2-McMGZ**](https://github.com/UnluckyForSome/AOE2-McMGZ)
package via **`mgz.summary.Summary`** (the package still imports as `mgz`).

Classic **`.scn` / `.scx`** scenarios use **AOE2-McGenieSCX**. **`.aoe2scenario`** uses **AoE2ScenarioParser**.

---

## Command line

**One file → one PNG**

```bash
aoe2-mcminimap --input "match.aoe2record" --output minimap.png
```

**Folder → many PNGs** (recursive; output tree mirrors input)

```bash
aoe2-mcminimap --input ./replays --output ./pngs
```

Sample inputs live under `examples/input/`, with matching rendered outputs under `examples/output/`.

**Common flags** (defaults match a typical “full map” render):

```bash
aoe2-mcminimap --input map.aoe2scenario --output out.png ^
  --object_mode square ^
  --angle 45 --multiplier_integer 9 --orthographic_ratio 2 --border_spacing 4 ^
  --draw-cliffs --draw-walls --smooth-walls --draw-gaia --draw-players ^
  --draw-food --draw-gold --draw-stone --draw-relics
```

On **Linux/macOS**, replace `^` with `\` for line continuation, or put everything on one line.

Default is **`--town-center pixel`** (small TC marker per player color). Use **`--town-center none`** to disable TC markers, or **`--town-center emblem`** for civ PNGs from the bundled package `emblems/` (`Britons.png`, …). Override with `--emblems-dir /path/to/pngs`.

---

## Python

**PNG bytes** (e.g. for a web app or buffer):

```python
from aoe2_mcminimap import MinimapSettings, to_png_bytes

settings = MinimapSettings(angle=45, multiplier_integer=9)
png = to_png_bytes("scenario.aoe2scenario", settings=settings)
with open("out.png", "wb") as f:
    f.write(png)
```

**Save a PNG with explicit settings:**

```python
from aoe2_mcminimap import MinimapSettings, to_image

to_image(
    "match.aoe2record",
    settings=MinimapSettings(town_center="none"),  # default is pixel; omit MinimapSettings() for defaults
).save("minimap.png")
```

**Read map / player data** without rendering (for your own tooling):

```python
from aoe2_mcminimap import read_map

m = read_map("match.aoe2record")
dim = m.map.dimension
players = m.players
gaia = m.gaia
```

`MinimapSettings` is a frozen dataclass: pass only the fields you care about; the rest use built-in defaults (see `aoe2_mcminimap/settings.py`).

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

Rendering uses **`data/mcminimap_constants.json`** (terrain colors, object ID sets, civilization names for replay headers via `civilizations_by_id`). That file is bundled inside the **`aoe2_mcminimap`** package.

---

## Publishing (maintainers)

**Order:** publish **`AOE2-McGenieSCX`**, **`AOE2-McMGZ`**, then
**`AOE2-McMinimap`**.

Before building wheels, remove stray bytecode so it is not bundled:

```bash
# POSIX example; on Windows, delete **/__pycache__ folders under aoe2_mcminimap/
find aoe2_mcminimap -type d -name __pycache__ -exec rm -rf {} +
pip install build twine
rm -rf dist build
python -m build
twine upload dist/*
```

For **TestPyPI** smoke tests, use `twine upload --repository testpypi dist/*` and install with  
`pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ …`  
(see **AOE2-McGenieSCX** README). Bump `version` in `pyproject.toml` and `aoe2_mcminimap/__init__.__version__` on each upload.

---

## Thanks

Inspired by **Marfullsen**’s [AoE2 minimap generator](https://github.com/Marfullsen/AoE2-minimap-generator). Replay parsing now uses the Museum-maintained [**AOE2-McMGZ**](https://github.com/UnluckyForSome/AOE2-McMGZ) fork of happyleaves **aoc-mgz**.

![Sample minimap](readme/example4.png)
