# MyLitho

A locally-hosted lithophane generator: upload a photo, adjust it with a live
3D preview, and export a print-ready STL. Built as a personal, self-hosted
alternative to itslitho.com for producing lithophanes for an Etsy shop.

Everything runs on your machine — no cloud processing, no accounts, no rate
limits.

## Features

- **Live 3D preview** (Three.js) that updates instantly as you drag sliders
- **Shapes**: flat rectangular panel, curved wrap (for lamps/cylinders),
  circle/ornament, and heart
- **Optional hanging hole** for ornaments
- **Optional companion parts**, exported as separate STL files sized to fit
  the panel: an LED backlight box (with a cord slot) and a snap-on frame
  (rabbeted so the panel friction-fits into it)
- Adjustable size, min/max thickness, mesh detail/resolution, brightness,
  contrast, gamma, and invert
- Output is a watertight, manifold mesh ready to slice directly — no repair
  needed in your slicer

## Setup

Requires Python 3.10+.

```bash
cd MyLitho
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8420
```

Then open http://127.0.0.1:8420 in your browser.

## Using it

1. Choose a photo.
2. Set the physical size (width/height in mm) — aspect ratio locks to the
   photo by default.
3. Pick a shape. Curved wrap needs a curve angle (degrees the panel bends
   through); circle/heart clip the panel to that outline.
4. Dial in min/max thickness. Min thickness is the brightest/thinnest area
   (lets the most light through); max thickness is the darkest/thickest
   area. A good starting point for FDM printing is 0.8mm min / 3.0mm max
   with a 0.4mm nozzle — thinner min than your nozzle can reliably extrude
   will look inconsistent.
5. Bump the **Detail** slider for finer surface resolution on close-up or
   high-contrast photos. Higher detail means a heavier mesh and slower
   export (boolean-based shapes — circle, heart, the frame, the box — take
   longer at high detail).
6. Optionally enable the backlight box and/or snap-on frame (flat shape
   only). These export as their own STL files, dimensioned to fit the
   panel with a small tolerance.
7. Click **Download STL**. A single shape downloads as a `.stl`; if you've
   enabled the box or frame it downloads as a `.zip` with all the parts.

The in-browser preview uses a lower mesh resolution than the exported file
for responsiveness — the download is generated at your full detail setting.

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
  only image adjustments (brightness/contrast/gamma/invert) or a new photo
  trigger a server call to `/api/preview`.

## Notes for production use

- Boolean operations (circle/heart shapes, hanging hole, backlight box,
  snap-on frame) are the slowest part of export. If you're batching many
  orders, keep **Detail** moderate for those shapes unless you need the
  extra resolution.
- The snap-on frame's pocket depth needs to be deeper than your panel's
  max thickness for the panel to sit flush — increase **Frame Depth** if
  parts are protruding.
