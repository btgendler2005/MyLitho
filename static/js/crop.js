// Interactive crop/pan/zoom editor. The photo is displayed behind a
// fixed-aspect viewport (aspect = panel width_mm/height_mm) and dragged
// or zoomed to choose which part becomes the lithophane. State is kept
// as three plain numbers -- scale, centerX, centerY (fractions of the
// source image) -- that map 1:1 onto app/imaging.py's crop_to_frame, so
// what you see here is exactly what gets cropped server-side.

const state = {
  naturalW: 0,
  naturalH: 0,
  scale: 1,
  centerX: 0.5,
  centerY: 0.5,
  dragging: false,
  dragStart: null,
};

let viewportEl, imgEl, onChange;

export function initCropEditor(viewport, img, changeCallback) {
  viewportEl = viewport;
  imgEl = img;
  onChange = changeCallback;

  viewportEl.addEventListener("pointerdown", onPointerDown);
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);
  viewportEl.addEventListener("wheel", onWheel, { passive: false });
  new ResizeObserver(render).observe(viewportEl);
}

// initialCrop optionally restores a previously-saved crop (e.g. reopening
// a project from Recent) instead of resetting to the default "cover" fit.
// Applied inside the same onload callback that sets naturalW/H, since
// setting it before the image loads would just get overwritten here.
export function setImage(file, initialCrop) {
  const url = URL.createObjectURL(file);
  imgEl.onload = () => {
    state.naturalW = imgEl.naturalWidth;
    state.naturalH = imgEl.naturalHeight;
    state.scale = initialCrop?.crop_scale ?? 1;
    state.centerX = initialCrop?.crop_center_x ?? 0.5;
    state.centerY = initialCrop?.crop_center_y ?? 0.5;
    render();
    URL.revokeObjectURL(url);
  };
  imgEl.src = url;
}

export function setTargetAspect(aspect) {
  viewportEl.style.aspectRatio = String(aspect);
  clampCenterForScale();
  render();
}

export function resetCrop() {
  state.scale = 1;
  state.centerX = 0.5;
  state.centerY = 0.5;
  render();
  emitChange();
}

export function getCropParams() {
  return { crop_scale: state.scale, crop_center_x: state.centerX, crop_center_y: state.centerY };
}

function emitChange() {
  if (onChange) onChange(getCropParams());
}

function baseScale() {
  const vw = viewportEl.clientWidth;
  const vh = viewportEl.clientHeight;
  if (!state.naturalW || !vw || !vh) return 1;
  return Math.max(vw / state.naturalW, vh / state.naturalH);
}

function render() {
  if (!state.naturalW) return;
  const vw = viewportEl.clientWidth;
  const vh = viewportEl.clientHeight;
  const cssScale = baseScale() * state.scale;
  const dispW = state.naturalW * cssScale;
  const dispH = state.naturalH * cssScale;
  const left = vw / 2 - state.centerX * state.naturalW * cssScale;
  const top = vh / 2 - state.centerY * state.naturalH * cssScale;
  imgEl.style.width = dispW + "px";
  imgEl.style.height = dispH + "px";
  imgEl.style.left = left + "px";
  imgEl.style.top = top + "px";
}

// Keeps the crop window's edges from leaving the source image bounds as
// scale/viewport shape change.
function clampCenterForScale() {
  const vw = viewportEl.clientWidth;
  const vh = viewportEl.clientHeight;
  if (!vw || !vh || !state.naturalW) return;
  const cssScale = baseScale() * state.scale;
  const cropWpx = vw / cssScale;
  const cropHpx = vh / cssScale;
  const halfFracX = Math.min(0.5, cropWpx / 2 / state.naturalW);
  const halfFracY = Math.min(0.5, cropHpx / 2 / state.naturalH);
  state.centerX = Math.min(1 - halfFracX, Math.max(halfFracX, state.centerX));
  state.centerY = Math.min(1 - halfFracY, Math.max(halfFracY, state.centerY));
}

function onPointerDown(e) {
  if (!state.naturalW) return;
  state.dragging = true;
  viewportEl.setPointerCapture(e.pointerId);
  state.dragStart = { x: e.clientX, y: e.clientY, centerX: state.centerX, centerY: state.centerY };
  viewportEl.classList.add("dragging");
}

function onPointerMove(e) {
  if (!state.dragging) return;
  const cssScale = baseScale() * state.scale;
  const dx = e.clientX - state.dragStart.x;
  const dy = e.clientY - state.dragStart.y;
  state.centerX = state.dragStart.centerX - dx / (state.naturalW * cssScale);
  state.centerY = state.dragStart.centerY - dy / (state.naturalH * cssScale);
  clampCenterForScale();
  render();
}

function onPointerUp() {
  if (!state.dragging) return;
  state.dragging = false;
  viewportEl.classList.remove("dragging");
  emitChange();
}

function onWheel(e) {
  if (!state.naturalW) return;
  e.preventDefault();
  const delta = -e.deltaY * 0.0015;
  state.scale = Math.min(6, Math.max(1, state.scale * (1 + delta)));
  clampCenterForScale();
  render();
  emitChange();
}

export function setZoom(scale) {
  state.scale = Math.min(6, Math.max(1, scale));
  clampCenterForScale();
  render();
  emitChange();
}
