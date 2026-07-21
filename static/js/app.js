import { initViewer, setPreviewMesh, setBacklightMode, loadBacklightTextureFromBase64 } from "./viewer.js";
import { buildFlatGeometry, buildCurvedGeometry, circleMask, heartMask } from "./meshgen.js";
import { initCropEditor, setImage as setCropImage, setTargetAspect, resetCrop, getCropParams, setZoom as setCropZoom } from "./crop.js";
import { refreshRecentProjects, loadProject } from "./projects.js";

const el = (id) => document.getElementById(id);

const state = {
  file: null,
  imageAspect: null,
  previewData: null,
  previewDebounce: null,
};

initViewer(el("viewer"));

initCropEditor(el("cropViewport"), el("cropImage"), (params) => {
  el("cropZoom").value = params.crop_scale.toFixed(2);
  el("cropZoomVal").textContent = params.crop_scale.toFixed(2) + "x";
  scheduleFetchPreview();
});

function paramsFromUI() {
  return {
    width_mm: parseFloat(el("widthMm").value),
    height_mm: parseFloat(el("heightMm").value),
    min_thickness_mm: parseFloat(el("minThickness").value),
    max_thickness_mm: parseFloat(el("maxThickness").value),
    detail: parseFloat(el("detail").value),
    border_mm: parseFloat(el("borderMm").value),
    ...getCropParams(),
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
    box_lip_mm: parseFloat(el("boxLip").value),
    box_tolerance_mm: 0.4,
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
  const showBox = el("addBox").checked && flatShape;
  el("boxOptions").hidden = !showBox;
  el("boxHint").hidden = !showBox;
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

function updateCropAspect() {
  const aspect = parseFloat(el("widthMm").value) / parseFloat(el("heightMm").value);
  setTargetAspect(aspect);
}

// Sets every UI field from a saved project's params (crop is handled
// separately in loadImageFile, since crop.js needs the image loaded
// first to know its natural dimensions).
function applyParams(p) {
  el("widthMm").value = p.width_mm;
  el("heightMm").value = p.height_mm;
  el("minThickness").value = p.min_thickness_mm;
  el("maxThickness").value = p.max_thickness_mm;
  el("detail").value = p.detail;
  el("borderMm").value = p.border_mm;
  el("shape").value = p.shape;
  el("curveDegrees").value = p.curve_degrees;
  el("invert").checked = p.invert;
  el("brightness").value = p.brightness;
  el("contrast").value = p.contrast;
  el("gamma").value = p.gamma;
  el("hangingHole").checked = p.hanging_hole;
  el("addBox").checked = p.add_backlight_box;
  el("boxWall").value = p.box_wall_mm;
  el("boxDepth").value = p.box_depth_mm;
  el("boxLip").value = p.box_lip_mm;
  el("addFrame").checked = p.add_frame;
  el("frameBorder").value = p.frame_border_mm;
  el("frameDepth").value = p.frame_depth_mm;
}

// Shared by both a fresh file-picker upload and reopening a saved
// project; savedParams (if given) restores the exact crop instead of
// resetting to the default "cover" fit, and skips the lock-aspect
// auto-height adjustment since width/height already came from applyParams.
function loadImageFile(file, savedParams) {
  state.file = file;
  const img = new Image();
  img.onload = () => {
    state.imageAspect = img.naturalWidth / img.naturalHeight;
    if (!savedParams && el("lockAspect").checked) {
      el("heightMm").value = (parseFloat(el("widthMm").value) / state.imageAspect).toFixed(1);
    }
    URL.revokeObjectURL(img.src);
    el("cropSection").hidden = false;
    setCropImage(file, savedParams);
    const zoom = savedParams ? savedParams.crop_scale : 1;
    el("cropZoom").value = zoom;
    el("cropZoomVal").textContent = zoom.toFixed(2) + "x";
    updateCropAspect();
    fetchPreview();
  };
  img.src = URL.createObjectURL(file);
}

async function handleSelectProject(id) {
  setStatus("Loading project…");
  try {
    const { params: p, file } = await loadProject(id);
    applyParams(p);
    updateValLabels();
    toggleConditionalFields();
    loadImageFile(file, p);
  } catch (e) {
    setStatus(e.message, true);
  }
}

el("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  loadImageFile(file);
});

["widthMm", "heightMm", "borderMm", "invert", "brightness", "contrast", "gamma"].forEach((id) => {
  el(id).addEventListener("input", () => {
    if (id === "widthMm" && el("lockAspect").checked && state.imageAspect) {
      el("heightMm").value = (parseFloat(el("widthMm").value) / state.imageAspect).toFixed(1);
    }
    if (id === "heightMm" && el("lockAspect").checked && state.imageAspect) {
      el("widthMm").value = (parseFloat(el("heightMm").value) * state.imageAspect).toFixed(1);
    }
    if (id === "widthMm" || id === "heightMm") {
      updateCropAspect();
    }
    updateValLabels();
    scheduleFetchPreview();
  });
});

el("cropZoom").addEventListener("input", () => {
  setCropZoom(parseFloat(el("cropZoom").value));
  el("cropZoomVal").textContent = parseFloat(el("cropZoom").value).toFixed(2) + "x";
});

el("cropResetBtn").addEventListener("click", () => {
  resetCrop();
  el("cropZoom").value = 1;
  el("cropZoomVal").textContent = "1.00x";
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
  "boxLip",
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
    refreshRecentProjects(handleSelectProject);
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
refreshRecentProjects(handleSelectProject);
