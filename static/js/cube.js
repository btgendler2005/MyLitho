import * as THREE from "three";
import { initViewer, setPreviewGroup } from "./viewer.js";
import { buildFlatGeometry } from "./meshgen.js";
import { createCropEditor } from "./crop.js";

const el = (id) => document.getElementById(id);

const FACES = ["top", "front", "right", "back", "left"];
const SIDE_FACES = ["front", "right", "back", "left"];

const faceState = {};
FACES.forEach((face) => {
  faceState[face] = { file: null, previewData: null, cropEditor: null };
});

const debounceTimers = {};

initViewer(el("viewer"));

function setStatus(msg, isError = false) {
  const s = el("statusMsg");
  s.textContent = msg;
  s.classList.toggle("error", isError);
}

function updateValLabels() {
  el("edgeMmVal").textContent = el("edgeMm").value + "mm";
  el("minThicknessVal").textContent = parseFloat(el("minThickness").value).toFixed(2) + "mm";
  el("maxThicknessVal").textContent = parseFloat(el("maxThickness").value).toFixed(2) + "mm";
  el("detailVal").textContent = parseFloat(el("detail").value).toFixed(1) + " pts/mm";
  el("brightnessVal").textContent = el("brightness").value;
  el("contrastVal").textContent = el("contrast").value;
  el("gammaVal").textContent = parseFloat(el("gamma").value).toFixed(2);
  el("postMmVal").textContent = parseFloat(el("postMm").value).toFixed(1) + "mm";
  el("grooveDepthVal").textContent = parseFloat(el("grooveDepth").value).toFixed(1) + "mm";
  el("toleranceVal").textContent = parseFloat(el("tolerance").value).toFixed(2) + "mm";
  el("puckDiameterVal").textContent = el("puckDiameter").value + "mm";
  el("puckPocketDepthVal").textContent = parseFloat(el("puckPocketDepth").value).toFixed(1) + "mm";
}

function paramsFromUI() {
  const p = {
    edge_mm: parseFloat(el("edgeMm").value),
    min_thickness_mm: parseFloat(el("minThickness").value),
    max_thickness_mm: parseFloat(el("maxThickness").value),
    detail: parseFloat(el("detail").value),
    invert: el("invert").checked,
    brightness: parseFloat(el("brightness").value),
    contrast: parseFloat(el("contrast").value),
    gamma: parseFloat(el("gamma").value),
    post_mm: parseFloat(el("postMm").value),
    groove_depth_mm: parseFloat(el("grooveDepth").value),
    tolerance_mm: parseFloat(el("tolerance").value),
    puck_diameter_mm: parseFloat(el("puckDiameter").value),
    puck_pocket_depth_mm: parseFloat(el("puckPocketDepth").value),
  };
  FACES.forEach((face) => {
    p[face] = faceState[face].cropEditor.getCropParams();
  });
  return p;
}

function updateDownloadEnabled() {
  el("downloadBtn").disabled = FACES.some((f) => !faceState[f].file);
}

async function fetchFacePreview(face) {
  const f = faceState[face];
  if (!f.file) return;
  const fd = new FormData();
  fd.append("image", f.file);
  fd.append("face", face);
  fd.append("params", JSON.stringify(paramsFromUI()));
  try {
    const res = await fetch("/api/cube/preview", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Preview failed");
    }
    f.previewData = await res.json();
    rebuildAssembledGeometry();
    setStatus("");
  } catch (e) {
    setStatus(e.message, true);
  }
}

function scheduleFetchFace(face) {
  clearTimeout(debounceTimers[face]);
  debounceTimers[face] = setTimeout(() => fetchFacePreview(face), 250);
}

function scheduleFetchAllFaces() {
  FACES.forEach((f) => {
    if (faceState[f].file) scheduleFetchFace(f);
  });
}

// Mirrors app/cube.py's cube_layout() -- same numbers, so the JS
// preview assembles the panels at the same positions the printed frame
// will actually hold them at. floorMm can be taller than postMm (a
// deep puck pocket needs more floor material below it) -- see
// cube.py's cube_layout() docstring.
function cubeLayout(edgeMm, postMm, grooveDepthMm, puckPocketDepthMm) {
  const clampedGroove = Math.min(grooveDepthMm, postMm * 0.6);
  const inset = postMm - clampedGroove;
  const outer = edgeMm + 2 * inset;
  const floorMm = Math.max(postMm, puckPocketDepthMm + 2.5);
  const postH = floorMm + edgeMm;
  return { inset, outer, floorMm, postH, center: outer / 2 };
}

// Places a flat panel geometry (built in its own local frame: X/Y =
// width/height in [0, edge_mm], Z = thickness) at its assembled cube
// position. Side faces stand the panel up (rotate 90 deg about local
// X) and swing it to the right wall via a pivot group centered on the
// footprint, matching app/cube.py's build_cube_base()/_replicate_4().
// postMm positions the panel against the post's inner face (an X/Y
// concept); layout.floorMm is where its bottom edge rests (Z).
function placeFaceGeometry(geometry, face, layout, postMm) {
  const mesh = new THREE.Mesh(geometry);
  if (face === "top") {
    mesh.position.set(layout.inset, layout.inset, layout.postH);
    return mesh;
  }
  const faceIndex = SIDE_FACES.indexOf(face);
  mesh.rotation.x = Math.PI / 2;
  mesh.position.set(layout.inset - layout.center, postMm - layout.center, layout.floorMm);
  const pivot = new THREE.Group();
  pivot.position.set(layout.center, layout.center, 0);
  pivot.rotation.z = (Math.PI / 2) * faceIndex;
  pivot.add(mesh);
  return pivot;
}

function rebuildAssembledGeometry() {
  const p = paramsFromUI();
  const layout = cubeLayout(p.edge_mm, p.post_mm, p.groove_depth_mm, p.puck_pocket_depth_mm);
  const group = new THREE.Group();
  let any = false;
  FACES.forEach((face) => {
    const data = faceState[face].previewData;
    if (!data) return;
    any = true;
    const geo = buildFlatGeometry(
      data.heightmap,
      data.rows,
      data.cols,
      data.width_mm,
      data.height_mm,
      p.min_thickness_mm,
      p.max_thickness_mm,
      null
    );
    group.add(placeFaceGeometry(geo, face, layout, p.post_mm));
  });
  if (any) setPreviewGroup(group);
}

function setupFace(face) {
  const editor = createCropEditor(el(`crop-${face}`), el(`cropImg-${face}`), () => scheduleFetchFace(face));
  editor.setTargetAspect(1); // every cube face crops to a square
  faceState[face].cropEditor = editor;

  el(`file-${face}`).addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    faceState[face].file = file;
    editor.setImage(file);
    updateDownloadEnabled();
    scheduleFetchFace(face);
  });
}

FACES.forEach(setupFace);

["edgeMm", "invert", "brightness", "contrast", "gamma", "detail"].forEach((id) => {
  el(id).addEventListener("input", () => {
    updateValLabels();
    scheduleFetchAllFaces();
  });
});

["minThickness", "maxThickness"].forEach((id) => {
  el(id).addEventListener("input", () => {
    updateValLabels();
    rebuildAssembledGeometry();
  });
});

["postMm", "grooveDepth", "tolerance", "puckDiameter", "puckPocketDepth"].forEach((id) => {
  el(id).addEventListener("input", updateValLabels);
});

el("downloadBtn").addEventListener("click", async () => {
  const missing = FACES.filter((f) => !faceState[f].file);
  if (missing.length) {
    setStatus(`Add a photo for: ${missing.join(", ")}`, true);
    return;
  }
  const p = paramsFromUI();
  const fd = new FormData();
  FACES.forEach((f) => fd.append(`image_${f}`, faceState[f].file));
  fd.append("params", JSON.stringify(p));
  setStatus("Generating STLs… 7 parts, this can take a bit.");
  el("downloadBtn").disabled = true;
  try {
    const res = await fetch("/api/cube/generate", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Generation failed");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cube_lamp_export.zip";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus("Done — check your downloads.");
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    el("downloadBtn").disabled = false;
  }
});

updateValLabels();
