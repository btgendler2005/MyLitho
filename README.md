# MyLitho

A locally-hosted lithophane generator: upload a photo, adjust it with a live
3D preview, and export a print-ready STL. Built as a personal, self-hosted
alternative to itslitho.com for producing lithophanes for an Etsy shop.

Everything runs on your machine — no cloud processing, no accounts, no rate
limits.

## Features

- **Live 3D preview** (Three.js) that updates instantly as you drag sliders,
  at a resolution that tracks your Detail setting so the preview isn't
  blocky even at high detail
- **Simulated backlight preview** — a one-click toggle that switches the
  preview to an unlit, glowing render approximating how the print looks
  with a light behind it, so you can judge contrast/detail before printing
- **Shapes**: flat rectangular panel, curved wrap (for lamps/cylinders),
  circle/ornament, and heart
- **Border/mat** — an optional flat-thickness border baked right into the
  panel, like a picture-frame mat, in any shape
- **Optional hanging hole** for ornaments
- **Optional companion parts**, exported as separate STL files sized to fit
  the panel (border included): an LED backlight box (with a cord slot) and
  a snap-on frame (rabbeted so the panel friction-fits into it)
- Adjustable size, min/max thickness, mesh detail/resolution, brightness,
  contrast, gamma, and invert
- Output is a watertight, manifold mesh ready to slice directly — no repair
  needed in your slicer

## Run (macOS, easiest)

Double-click **`run.command`** in Finder. First run installs everything
automatically (takes a minute); every run after that starts instantly.
Your browser opens to the app on its own. To stop it, close the terminal
window that pops up (or press Ctrl+C in it).

If macOS blocks it as an unidentified script the first time, right-click
`run.command` → **Open** → confirm.

## Setup (manual / other platforms)

Requires Python 3.10+.

```bash
cd MyLitho
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (manual)

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8420
```

Then open http://127.0.0.1:8420 in your browser.

## Using it

1. Choose a photo.
2. Set the physical size (width/height in mm) — aspect ratio locks to the
   photo by default.
3. Optionally add a **Border / mat** — a flat, uniform-thickness rim baked
   around the image, like a picture-frame mat. It follows whatever shape
   you pick (rectangular, heart outline, etc).
4. Pick a shape. Curved wrap needs a curve angle (degrees the panel bends
   through); circle/heart clip the panel (and its border) to that outline.
5. Dial in min/max thickness. Min thickness is the brightest/thinnest area
   (lets the most light through); max thickness is the darkest/thickest
   area — the border is solid at max thickness. A good starting point for
   FDM printing is 0.8mm min / 3.0mm max with a 0.4mm nozzle — thinner min
   than your nozzle can reliably extrude will look inconsistent.
6. Bump the **Detail** slider for finer surface resolution on close-up or
   high-contrast photos — this also sharpens the live preview, not just
   the export. Higher detail means a heavier mesh and slower export
   (boolean-based shapes — circle, heart, the frame, the box — take longer
   at high detail).
7. Toggle **Simulate backlight** above the viewer to see an approximation
   of how the print glows with a light behind it — this is the best way to
   catch contrast problems (too washed out, or too dark/muddy) before you
   commit to printing. It's preview-only; it doesn't affect the export.
8. Optionally enable the backlight box and/or snap-on frame (flat shape
   only). These export as their own STL files, sized to fit the panel
   (border included) with a small tolerance.
9. Click **Download STL**. A single shape downloads as a `.stl`; if you've
   enabled the box or frame it downloads as a `.zip` with all the parts.

The in-browser preview matches the exported file's resolution almost
exactly at typical sizes (e.g. a 100mm panel at the default 2.5 pts/mm
detail renders at the *same* 250x250 grid in both preview and export).
It only falls a bit behind the export at the extreme end — very large
panels combined with max Detail — since the preview is still capped a bit
lower than boolean-free (flat/curved) exports to stay smooth in the
browser. Novelty shapes (circle/heart) are capped lower on export than in
preview, because clipping them to their outline is a boolean operation
that gets slow at high resolution — so for those two shapes the preview
can actually look *finer* than the final file. If you want to sanity-check
resolution for your own settings: preview and export both derive from the
same `width_mm/height_mm x Detail`, so bumping Detail sharpens both
together.

## How it works

- `app/imaging.py` — resamples the photo to a heightmap grid, with
  brightness/contrast/gamma/invert applied server-side.
- `app/shapes.py` — converts the heightmap into vertex grids for flat and
  curved panels, and clips novelty shapes (circle/heart) via a boolean
  intersection with an extruded polygon.
- `app/geometry.py` — stitches a heightmap vertex grid (top surface, flat
  or curved backing, and side walls) into a single watertight solid — the
  same top/bottom/wall-stitching approach used by most open-source
  lithophane generators (e.g.
  [jamesphilbrick/lithophane-generator](https://github.com/jamesphilbrick/lithophane-generator)).
- `app/accessories.py` — parametric backlight box and snap-on frame, built
  from primitive boxes combined with boolean operations
  ([trimesh](https://trimesh.org/), [manifold3d](https://github.com/elalish/manifold) engine).
- `static/` — the frontend. `meshgen.js` mirrors the flat/curved position
  math from `shapes.py` in JavaScript so the live preview can rebuild
  instantly on the client without a round trip for every slider tweak;
  image adjustments, size, and border changes trigger a server call to
  `/api/preview` (they change the heightmap itself), while shape/thickness/
  curve changes redraw instantly from the already-fetched heightmap.
- The **border** is implemented by padding the heightmap with 0.0-value
  pixels before meshing (`imaging.apply_border`) — since a 0.0 pixel maps
  to max thickness under the existing thickness formula, this reuses all
  the normal mesh-building and shape-masking code with no special case.
- The **backlight preview** colors each preview vertex directly from its
  heightmap value (the same brightness value used to compute thickness) so
  thin/bright areas glow and thick/dark areas stay dark, rendered with an
  unlit vertex-colored material on a black background.

## Notes for production use

- Boolean operations (circle/heart shapes, hanging hole, backlight box,
  snap-on frame) are the slowest part of export. If you're batching many
  orders, keep **Detail** moderate for those shapes unless you need the
  extra resolution.
- The snap-on frame's pocket depth needs to be deeper than your panel's
  max thickness for the panel to sit flush — increase **Frame Depth** if
  parts are protruding.
