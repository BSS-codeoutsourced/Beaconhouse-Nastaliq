#!/usr/bin/env python3
"""
Regenerate the fontmake-buildable UFO source for Beaconhouse Nastaliq.

WHY THIS SCRIPT EXISTS
----------------------
The font was originally authored in High-Logic FontCreator and exported to a
Glyphs (.glyphs) file plus a compiled TTF. FontCreator's Glyphs/FEA exporter is
buggy: it produces illegal FEA (commas in class names, <anchor NULL> in base
marks, marks assigned to more than one mark class, and *numbered* mark anchors
such as ``_Anchor_10`` which ufo2ft's MarkFeatureWriter rejects), a non-numeric
``.appVersion`` string that crashes glyphsLib, and (critically) feature code
whose compiled output does not match the font (mark positioning is lost and
diacritics float - see https://github.com/google/fonts/issues/10966).

Google's reviewer (issue #10966) recommended using the ``otf2fea`` script from
the ``fontFeatures`` package to recover clean, correct OpenType feature code
directly from the compiled TTF (which renders correctly). This script automates
that workflow end-to-end so the designer can keep editing in FontCreator and
rebuild the fontmake source with a single command.

WHAT IT DOES
------------
1. Loads ``BeaconhouseNastaliq.glyphs`` (after fixing the ``.appVersion``).
2. Extracts clean FEA from the compiled TTF via ``otf2fea``.
3. Builds a production-name <-> friendly-name mapping (FontCreator renames some
   glyphs to AGL/uni names during compilation, so the otf2fea FEA references
   production names that differ from the .glyphs source names).
4. Rewrites every glyph reference in the FEA from production names back to the
   friendly names used in the .glyphs source (so the FEA resolves during
   fontmake's feature compilation).
5. Fixes an otf2fea quirk: ``ignore sub`` statements emitted inside GPOS
   (positioning) lookup blocks are converted to ``ignore pos`` so each named
   lookup contains only one rule type.
6. Builds the UFO from the .glyphs, then:
     - sets ``features.fea`` to the cleaned, name-mapped FEA,
     - copies per-glyph advance widths from the compiled TTF's ``hmtx`` (some
       glyphs such as ``a_fla`` and the diacritical marks are deliberately
       zero-width in the original; FontCreator bakes this into hmtx rather than
       the glyph width, so the source width is wrong),
     - converts the source's quadratic curves to cubic (FontCreator exported
       quadratic contours, which crash ufo2ft's default booleanOperations
       RemoveOverlapsFilter),
     - sets ``com.github.googlei18n.ufo2ft.featureWriters`` to an empty list in
       the UFO lib so ufo2ft does not try to auto-generate mark/mkmk/kern/curs
       features from the (broken, numbered) anchors - our embedded FEA already
       contains the complete, correct feature definitions recovered by otf2fea.
7. Writes the UFO and a DesignSpace document.

After running this script, the font is built with plain fontmake, e.g.:

    fontmake -m sources/BeaconhouseNastaliq.designspace -o ttf --output-dir fonts

USAGE
-----
    python tools/regenerate_ufo.py \\
        --glyphs sources/BeaconhouseNastaliq.glyphs \\
        --ttf fonts/BeaconhouseNastaliq-Regular.ttf \\
        --ufo sources/BeaconhouseNastaliq-Regular.ufo \\
        --designspace sources/BeaconhouseNastaliq.designspace

REQUIREMENTS
------------
    pip install glyphsLib ufo2ft fontTools fontFeatures
"""

import argparse
import contextlib
import io
import os
import re
import shutil
import sys

import glyphsLib
import ufo2ft
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.ttLib import TTFont


# Manual mappings for ligature glyphs whose names FontCreator and ufo2ft generate
# differently (FontCreator uses the X_uniYYYY + suffix convention, ufo2ft uses a
# hex-concatenation of the component codepoints). These have no Unicode so they
# cannot be mapped via the cmap; we map them by hand from the original TTF name
# back to the friendly name used in the .glyphs source.
MANUAL_LIGATURE_MAPPINGS = {
    "uniFB01_i": "fi_i",
    "uniA761_f": "vy_f",
    "uniA761_i": "vy_i",
    "g_uniA76D": "g_is",
    "k_uniA76D": "k_is",
    "alef_f": "alef_f",  # identity: original TTF kept this friendly name
}


def extract_fea(ttf_path):
    """Run otf2fea on the compiled TTF and return the clean FEA text.

    This calls the same ``fontFeatures.ttLib.unparse`` machinery that the
    ``otf2fea`` console script uses (see fontFeatures.bin.otf2fea:main), so the
    output is byte-identical to running ``otf2fea <font>`` on the command line.
    """
    from fontFeatures.ttLib import unparse

    font = TTFont(ttf_path)
    ff = unparse(font, do_gdef=False, doLookups=True)
    return ff.asFea()


def build_name_mapping(glyphs_path, ttf_path):
    """Build a {production_name: friendly_name} mapping.

    FontCreator renames some glyphs (ASCII punctuation, Arabic letters, ligatures)
    to AGL / uni production names during compilation, while the .glyphs source
    keeps friendly names (``alif``, ``onena``, ...). The otf2fea FEA references
    the production names, so we must map them back to the source friendly names.

    The mapping is built by compiling the UFO with *empty* features and
    ``useProductionNames=True`` (which performs ufo2ft's exact production-name
    renaming), then zipping the UFO glyph order with the output glyph order.
    """
    gs = glyphsLib.load(glyphs_path)
    gs.appVersion = "3241"
    ds = glyphsLib.to_designspace(gs)
    ufo = ds.sources[0].font
    ufo_order = list(ufo.glyphOrder)
    # Skip feature compilation entirely - we only want the renamed glyph order.
    ttf = ufo2ft.compileTTF(
        ufo,
        useProductionNames=True,
        removeOverlaps=False,
        skipFeatureCompilation=True,
    )
    out_order = ttf.getGlyphOrder()
    if len(ufo_order) != len(out_order):
        raise RuntimeError(
            f"Glyph order length mismatch: UFO={len(ufo_order)} out={len(out_order)}"
        )
    friendly_to_prod = dict(zip(ufo_order, out_order))
    prod_to_friendly = {v: k for k, v in friendly_to_prod.items() if k != v}
    for k in ufo_order:
        if k == friendly_to_prod.get(k):
            prod_to_friendly.setdefault(k, k)

    # Add the manual ligature mappings.
    prod_to_friendly.update(MANUAL_LIGATURE_MAPPINGS)

    # Add Unicode-based mappings for any remaining original-TTF names not yet
    # covered (AGL-named glyphs like ``colon``, ``exclam`` whose source friendly
    # name is found by matching the codepoint).
    orig_ttf = TTFont(ttf_path)
    orig_cmap = orig_ttf.getBestCmap()
    src_by_unicode = {}
    for g in gs.glyphs:
        u = g.unicode
        if u:
            try:
                cp = int(u, 16)
            except (ValueError, TypeError):
                continue
            src_by_unicode.setdefault(cp, []).append(g.name)
    for cp, oname in orig_cmap.items():
        if oname not in prod_to_friendly and cp in src_by_unicode:
            prod_to_friendly[oname] = src_by_unicode[cp][0]
    return prod_to_friendly


def map_fea_names(fea_text, prod_to_friendly):
    """Rewrite production glyph names in the FEA back to friendly names."""
    mappable = sorted(
        [k for k in prod_to_friendly if k != prod_to_friendly[k]],
        key=len,
        reverse=True,
    )
    if not mappable:
        return fea_text
    pattern = re.compile(
        r"(?<![A-Za-z0-9_.])("
        + "|".join(re.escape(n) for n in mappable)
        + r")(?![A-Za-z0-9_.])"
    )
    return pattern.sub(lambda m: prod_to_friendly[m.group(1)], fea_text)


def fix_ignore_keywords(fea_text):
    """Convert ``ignore sub`` to ``ignore pos`` inside GPOS lookup blocks.

    otf2fea occasionally emits ``ignore sub ...;`` statements inside lookup
    blocks that otherwise contain only positioning rules. FEA requires all rules
    in a named lookup block to share the same lookup type, so those ``ignore
    sub`` statements must become ``ignore pos``.
    """
    lines = fea_text.splitlines()
    blocks = []
    cur = None
    for i, line in enumerate(lines):
        m = re.match(r"\s*lookup\s+(\S+)\s*\{", line)
        if m:
            cur = {"start": i, "is_gpos": False, "is_gsub": False}
        if cur is not None:
            s = line.strip()
            if re.search(r"\bpos\b", s) and (
                "lookup" in s or re.match(r"pos\s+(\[|@|\S+\s+-?\d)", s) or "'" in s
            ):
                cur["is_gpos"] = True
            if (re.match(r"sub\b", s) or re.match(r"substitute\b", s)) and "ignore" not in s:
                cur["is_gsub"] = True
        if re.match(r"\s*\}\s*\S+\s*;", line) and cur:
            cur["end"] = i
            blocks.append(cur)
            cur = None
    out = list(lines)
    nfix = 0
    for b in blocks:
        if b["is_gpos"] and not b["is_gsub"]:
            for i in range(b["start"], b["end"] + 1):
                if re.search(r"\bignore\s+sub\b", out[i]):
                    out[i] = out[i].replace("ignore sub", "ignore pos")
                    nfix += 1
    return "\n".join(out), nfix


def convert_quads_to_cubics(ufo):
    """Convert every quadratic curve in the UFO to a cubic curve.

    FontCreator exported the source contours as quadratic qcurves. ufo2ft's
    default RemoveOverlapsFilter uses booleanOperations, which cannot operate on
    quadratic curves and crashes ("unsupported segment type: qcurve").
    Converting quads to cubics (an exact, lossless transform) lets the default
    fontmake pipeline run unmodified; ufo2ft's CubicToQuadraticFilter later
    converts them back to quadratics for the final TrueType glyf table.
    """
    n = 0
    for gname in list(ufo.keys()):
        glyph = ufo[gname]
        if not glyph:
            continue
        rec = RecordingPen()
        try:
            glyph.draw(rec)
        except Exception:
            continue
        if not any(cmd == "qCurveTo" for cmd, _ in rec.value):
            continue
        out = RecordingPen()
        rec.replay(Qu2CuPen(out, max_err=0.01, all_cubic=True))
        glyph.clearContours()
        out.replay(glyph.getPen())
        n += 1
    return n


def set_glyph_widths_from_ttf(ufo, ttf_path, prod_to_friendly):
    """Copy per-glyph advance widths from the compiled TTF's hmtx into the UFO.

    FontCreator bakes certain zero-width glyphs (marks, spaces, the ``a_fla``
    half of the Allah ligature, etc.) directly into hmtx rather than the glyph
    width, so the .glyphs source widths are wrong. The compiled TTF is the
    source of truth here.
    """
    orig = TTFont(ttf_path)
    hmtx = orig["hmtx"].metrics
    friendly_to_prod = {v: k for k, v in prod_to_friendly.items() if v != k}
    friendly_to_prod.update({k: k for k in ufo.keys() if k not in friendly_to_prod})
    n_set = 0
    n_missing = 0
    for gname in list(ufo.keys()):
        prod = friendly_to_prod.get(gname, gname)
        if prod in hmtx:
            ufo[gname].width = hmtx[prod][0]
            n_set += 1
        else:
            n_missing += 1
    return n_set, n_missing


def main():
    ap = argparse.ArgumentParser(description="Regenerate the fontmake-buildable UFO for Beaconhouse Nastaliq")
    ap.add_argument("--glyphs", required=True, help="Path to the .glyphs source")
    ap.add_argument("--ttf", required=True, help="Path to the compiled TTF (reference)")
    ap.add_argument("--ufo", required=True, help="Output UFO directory")
    ap.add_argument("--designspace", required=True, help="Output .designspace path")
    args = ap.parse_args()

    print(f"[1/7] Extracting clean FEA from {args.ttf} via otf2fea ...")
    fea_text = extract_fea(args.ttf)
    print(f"      FEA length: {len(fea_text)} chars")

    print("[2/7] Building production<->friendly name mapping ...")
    prod_to_friendly = build_name_mapping(args.glyphs, args.ttf)
    print(f"      Mapped {len(prod_to_friendly)} production names to friendly names")

    print("[3/7] Mapping FEA glyph references to friendly names ...")
    fea_mapped = map_fea_names(fea_text, prod_to_friendly)

    print("[4/7] Fixing otf2fea ignore-keyword quirks ...")
    fea_fixed, nfix = fix_ignore_keywords(fea_mapped)
    print(f"      Fixed {nfix} ignore statements")

    print(f"[5/7] Building UFO from {args.glyphs} ...")
    gs = glyphsLib.load(args.glyphs)
    gs.appVersion = "3241"
    ds = glyphsLib.to_designspace(gs, instance_dir=".")
    ufo = ds.sources[0].font

    print("[6/7] Setting glyph widths, converting curves, installing FEA ...")
    n_set, n_missing = set_glyph_widths_from_ttf(ufo, args.ttf, prod_to_friendly)
    print(f"      Widths set: {n_set} | kept source width: {n_missing}")
    n_conv = convert_quads_to_cubics(ufo)
    print(f"      Converted {n_conv} glyphs from quadratic to cubic curves")
    ufo.features.text = fea_fixed
    # Disable ufo2ft's auto feature writers. Our embedded FEA (recovered by
    # otf2fea) already contains complete, correct mark/mkmk/kern/curs features;
    # letting the writers run would both crash on the numbered anchors
    # (FontCreator's ``_Anchor_10`` etc.) and duplicate the mark/mkmk features.
    ufo.lib["com.github.googlei18n.ufo2ft.featureWriters"] = []

    if os.path.exists(args.ufo):
        shutil.rmtree(args.ufo)
    if os.path.exists(args.designspace):
        os.remove(args.designspace)
    ufo.save(args.ufo, overwrite=True)
    ds.write(args.designspace)
    print(f"[7/7] Saved UFO -> {args.ufo}")
    print(f"      Saved DesignSpace -> {args.designspace}")
    print()
    print("Done. Build the font with:")
    print(f"  fontmake -m {args.designspace} -o ttf --output-dir fonts")


if __name__ == "__main__":
    main()
