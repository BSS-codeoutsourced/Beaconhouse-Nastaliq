# Beaconhouse Nastaliq

[![OFL](https://img.shields.io/badge/License-OFL%201.1-blue.svg)](https://scripts.sil.org/OFL)

**Beaconhouse Nastaliq** is the first open-source Urdu Nastaliq typeface, designed and engineered entirely by developers in Pakistan. It was commissioned by **Beaconhouse Group** and designed and engineered by **Muhammad Zeeshan Nasar**, built to bring the visual character of **Noori Nastaliq** to a modern, character-based (non-ligature-heavy) architecture suited for the web, publishing, and education.

![BH Nastaliq Sample](documentation/sample-image.png)

## About the Project

Traditional Nastaliq fonts like Noori Nastaliq rely on thousands of pre-composed ligatures to render the script's complex joining behavior, which makes them heavy, slow to load, and difficult to maintain. Beaconhouse Nastaliq takes a different approach: it is a **character-based font**, built with roughly **600 glyphs total (including Latin/English glyphs)**, while still aiming for a look and feel close to Noori Nastaliq.

This dramatic reduction in glyph count was made possible by a custom **joining-glyph technique**: instead of drawing a unique ligature for every possible letter combination, the font uses a set of extension/joining glyphs that combine with base glyphs through GSUB rules to dynamically produce the hundreds of contextual forms Nastaliq requires — without pre-building each one individually.

## Key Features

- **Character-based architecture** — ~600 glyphs total instead of the thousands of ligatures typical Nastaliq fonts require, achieved through a custom joining-glyph (extension glyph) system built with OpenType GSUB rules.
- **Noori Nastaliq–inspired design** — visually closer to the classic Noori Nastaliq look, re-engineered for efficient digital rendering.
- **Automatic dot-collision avoidance** — one of the hardest problems in Nastaliq typesetting is overlapping dots between adjacent letters. Beaconhouse Nastaliq uses custom **GPOS and GSUB rules** to detect and resolve dot collisions automatically wherever they occur.
- **Full diacritic (اعراب) support** — proper positioning and rendering of Urdu diacritical marks.
- **Built-in letter-joining education feature** — the glyphs are specially cut and shaped so that each letter's contribution to a joined word can be visually isolated. For example, in the word "نستعلیق," coloring each letter individually clearly shows where each character starts and ends within the joined form. This makes the font a practical tool for children learning how Urdu letters join together, simply by coloring or highlighting individual characters.

![BH Nastaliq Sample](documentation/sample-image2.png)

## Ownership and Credits

Beaconhouse Nastaliq was commissioned by, and is solely owned by, **Beaconhouse Group**.

- **Beaconhouse Group** — Commissioning Body & Copyright Holder
  - Website: <https://www.beaconhouse.net/>
  - *Beaconhouse is one of the world's largest private school networks, committed to educational excellence and cultural preservation.*

- **Muhammad Zeeshan Nasar** — Designer & Engineer
  - *Designed and engineered the font's character-based architecture, joining-glyph system, and dot-collision resolution rules.*

See [`AUTHORS.txt`](AUTHORS.txt) and [`CONTRIBUTORS.txt`](CONTRIBUTORS.txt) for the full copyright and contributor record.

## License

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied in [`OFL.txt`](OFL.txt), and is also available with a FAQ at: <https://scripts.sil.org/OFL>

## Repository Structure

- `sources/` — the font source:
  - `BeaconhouseNastaliq.glyphs` — editable Glyphs source authored in High-Logic FontCreator (the `.appVersion` is corrected so `glyphsLib` can parse it).
  - `BeaconhouseNastaliq-Regular.ufo/` — the **fontmake-buildable UFO source**. Its OpenType feature code was recovered from the compiled TTF with `otf2fea` (see [Google Fonts issue #10966](https://github.com/google/fonts/issues/10966)), and glyph widths and cubic contours are normalized so the default `fontmake` pipeline runs unmodified.
  - `BeaconhouseNastaliq.designspace` — DesignSpace document referencing the UFO.
  - `config.yaml` — gftools builder recipe (points at the designspace).
- `tools/regenerate_ufo.py` — script that regenerates the UFO from the `.glyphs` source + compiled TTF. Run this after editing the font in FontCreator (see below).
- `fonts/` — final binary font file (TTF).
- `documentation/` — Images, samples, and promotional materials.

## Changelog

**Beaconhouse Nastaliq Font**

**04 August 2026 — Version 1.00**
- First official release.
- 1 stylistic set added.

## Building from Source

Beaconhouse Nastaliq ships a fontmake-buildable UFO source (`sources/BeaconhouseNastaliq-Regular.ufo` + `sources/BeaconhouseNastaliq.designspace`). The OpenType feature code embedded in the UFO was recovered from the compiled TTF with [`otf2fea`](https://github.com/simoncozens/fontFeatures) (see [Google Fonts issue #10966](https://github.com/google/fonts/issues/10966)), because High-Logic FontCreator's Glyphs/FEA exporter produces feature code whose compiled output does not match the font (mark positioning is lost and diacritics float). The UFO is the canonical build source; the `.glyphs` file is the editable design source.

This is a single-weight, static font — there are no variable axes or multiple masters.

### Build the font

1. **Install dependencies:**

   ```bash
   pip install fontmake gftools
   ```

2. **Build the TTF from the UFO source:**

   ```bash
   gftools builder sources/config.yaml
   ```

   This reads `sources/config.yaml`, compiles `sources/BeaconhouseNastaliq.designspace` via `fontmake`, and outputs the final static TTF into `fonts/`.

   Equivalently, with plain `fontmake`:

   ```bash
   fontmake -m sources/BeaconhouseNastaliq.designspace -o ttf --output-dir fonts
   ```

### Regenerate the UFO after editing the font

The `.glyphs` file is authored and compiled in High-Logic FontCreator. Because FontCreator's Glyphs/FEA export is buggy, the buildable UFO is regenerated from the `.glyphs` source **and** the compiled TTF (the TTF renders correctly and is the source of truth for the OpenType features and glyph metrics). After editing the font in FontCreator and re-exporting the `.glyphs` and `.ttf`:

```bash
pip install glyphsLib ufo2ft fontTools fontFeatures
python tools/regenerate_ufo.py \
    --glyphs sources/BeaconhouseNastaliq.glyphs \
    --ttf fonts/BeaconhouseNastaliq-Regular.ttf \
    --ufo sources/BeaconhouseNastaliq-Regular.ufo \
    --designspace sources/BeaconhouseNastaliq.designspace
```

This script recovers clean feature code from the TTF via `otf2fea`, maps production glyph names back to the source's friendly names, fixes per-glyph advance widths, converts the source's quadratic contours to cubic, and disables ufo2ft's auto feature writers (the embedded FEA is already complete and the source's numbered mark anchors would otherwise crash the auto `MarkFeatureWriter`). After regeneration, rebuild with `fontmake` as shown above.


**Copyright (c) 2026 Beaconhouse Group.**
