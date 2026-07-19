import { initViewer, setPreviewMesh, setBacklightMode, loadBacklightTextureFromBase64 } from "./viewer.js";
import { buildFlatGeometry, buildCurvedGeometry, circleMask, heartMask } from "./meshgen.js";

const el = (id) => document.getElementById(id);

const state = {
  file: null,
  imageAspect: null,
  previewData: null,
  previewDebounce: null,
};

initViewer(el("viewer"));

function paramsFromUI() {
  return {
    width_mm: parseFloat(el("widthMm").value),
    height_mm: parseFloat(el("heightMm").value),
    min_thickness_mm: parseFloat(el("minThickness").value),
    max_thickness_mm: parseFloat(el("maxThickness").value),
    detail: parseFloat(el("detail").value),
    border_mm: parseFloat(el("borderMm").value),
    shape: el("shape").value,
    curve_degrees: parseFloat(el("curveDegrees").value),
    invert: el("invert").checked,
    brightness: parseFloat(el("brightness").value),
    contrast: parseFloat(el("contrast").value),
    gamma: parseFloat(el("gamma").value),
    hanging_hole: el("hangingHole").checked,
    add_backlight_box: el("addBox").checked,
    box_wall_mm: parseFloat(el("boxWall").value),
    box_depth_mm: parseFloat(el("boxDepth").value),
    box_tolerance_mm: 0.3,
    add_frame: el("addFrame").checked,
    frame_border_mm: parseFloat(el("frameBorder").value),
    frame_depth_mm: parseFloat(el("frameDepth").value),
    frame_tolerance_mm: 0.3,
  };
}

function setStatus(msg, isError = false) {
  const s = el("statusMsg");
  s.textContent = msg;
  s.classList.toggle("error", isError);
}

function updateValLabels() {
  el("curveDegreesVal").textContent = el("curveDegrees").value + "°";
  el("minThicknessVal").textContent = parseFloat(el("minThickness").value).toFixed(2) + "mm";
  el("maxThicknessVal").textContent = parseFloat(el("maxThickness").value).toFixed(2) + "mm";
  el("detailVal").textContent = parseFloat(el("detail").value).toFixed(1) + " pts/mm";
  el("borderMmVal").textContent = el("borderMm").value + "mm";
  el("brightnessVal").textContent = el("brightness").value;
  el("contrastVal").textContent = el("contrast").value;
  el("gammaVal").textContent = parseFloat(el("gamma").value).toFixed(2);
}

function toggleConditionalFields() {
  const shape = el("shape").value;
  el("curveField").hidden = shape !== "curved";

  const flatShape = shape === "flat";
  el("addBox").disabled = !flatShape;
  el("addFrame").disabled = !flatShape;
  if (!flatShape) {
    el("addBox").checked = false;
    el("addFrame").checked = false;
  }
  el("boxOptions").hidden = !(el("addBox").checked && flatShape);
  el("frameOptions").hidden = !(el("addFrame").checked && flatShape);
}

async function fetchPreview() {
  if (!state.file) return;
  const p = paramsFromUI();
  const fd = new FormData();
  fd.append("image", state.file);
  fd.append("params", JSON.stringify(p));
  setStatus("Processing image…");
  try {
    const res = await fetch("/api/preview", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Preview failed");
    }
    state.previewData = await res.json();
    rebuildGeometry();
    if (state.previewData.texture_png_base64) {
      loadBacklightTextureFromBase64(state.previewData.texture_png_base64);
    }
    setStatus("");
    el("downloadBtn").disabled = false;
  } catch (e) {
    setStatus(e.message, true);
  }
}

function scheduleFetchPreview() {
  clearTimeout(state.previewDebounce);
  state.previewDebounce = setTimeout(fetchPreview, 250);
}

function rebuildGeometry() {
  if (!state.previewData) return;
  const p = paramsFromUI();
  const { cols, rows, heightmap, width_mm, height_mm } = state.previewData;

  let geo;
  if (p.shape === "curved") {
    geo = buildCurvedGeometry(heightmap, rows, cols, width_mm, height_mm, p.min_thickness_mm, p.max_thickness_mm, p.curve_degrees);
  } else {
    let maskFn = null;
    if (p.shape === "circle") maskFn = circleMask(rows, cols, width_mm, height_mm);
    if (p.shape === "heart") maskFn = heartMask(rows, cols, width_mm, height_mm);
    geo = buildFlatGeometry(heightmap, rows, cols, width_mm, height_mm, p.min_thickness_mm, p.max_thickness_mm, maskFn);
  }
  setPreviewMesh(geo);
}

el("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  state.file = file;
  const img = new Image();
  img.onload = () => {
    state.imageAspect = img.naturalWidth / img.naturalHeight;
    if (el("lockAspect").checked) {
      el("heightMm").value = (parseFloat(el("widthMm").value) / state.imageAspect).toFixed(1);
    }
    URL.revokeObjectURL(img.src);
    fetchPreview();
  };
  img.src = URL.createObjectURL(file);
});

["widthMm", "heightMm", "borderMm", "invert", "brightness", "contrast", "gamma"].forEach((id) => {
  el(id).addEventListener("input", () => {
    if (id === "widthMm" && el("lockAspect").checked && state.imageAspect) {
      el("heightMm").value = (parseFloat(el("widthMm").value) / state.imageAspect).toFixed(1);
    }
    if (id === "heightMm" && el("lockAspect").checked && state.imageAspect) {
      el("widthMm").value = (parseFloat(el("heightMm").value) * state.imageAspect).toFixed(1);
    }
    updateValLabels();
    scheduleFetchPreview();
  });
});

[
  "shape",
  "curveDegrees",
  "minThickness",
  "maxThickness",
  "detail",
  "hangingHole",
  "addBox",
  "addFrame",
  "boxWall",
  "boxDepth",
  "frameBorder",
  "frameDepth",
].forEach((id) => {
  el(id).addEventListener("input", () => {
    updateValLabels();
    toggleConditionalFields();
    rebuildGeometry();
  });
});

el("downloadBtn").addEventListener("click", async () => {
  if (!state.file) return;
  const p = paramsFromUI();
  const fd = new FormData();
  fd.append("image", state.file);
  fd.append("params", JSON.stringify(p));
  setStatus("Generating STL… boolean shapes can take a few seconds.");
  el("downloadBtn").disabled = true;
  try {
    const res = await fetch("/api/generate", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Generation failed");
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = /filename="([^"]+)"/.exec(disposition);
    const filename = match ? match[1] : "lithophane.stl";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
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

el("backlightToggle").addEventListener("change", (e) => {
  setBacklightMode(e.target.checked);
});

updateValLabels();
toggleConditionalFields();
