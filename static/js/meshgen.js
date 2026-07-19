// Client-side preview mesh builder. Mirrors app/shapes.py's flat/curved
// position math so slider changes (thickness, shape, curve, size) can be
// re-rendered instantly without a server round trip. Only the top surface
// is built (open mesh) since this is a visual preview, not the export --
// the real watertight solid is generated server-side on download.

import * as THREE from "three";

function thicknessGrid(heightmap, rows, cols, minT, maxT) {
  const t = new Float32Array(rows * cols);
  for (let i = 0; i < rows * cols; i++) {
    t[i] = minT + (1 - heightmap[i]) * (maxT - minT);
  }
  return t;
}

export function buildFlatGeometry(heightmap, rows, cols, widthMm, heightMm, minT, maxT, maskFn) {
  const thickness = thicknessGrid(heightmap, rows, cols, minT, maxT);
  const positions = new Float32Array(rows * cols * 3);

  for (let r = 0; r < rows; r++) {
    const y = heightMm - (r / (rows - 1)) * heightMm;
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      const x = (c / (cols - 1)) * widthMm;
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = thickness[i];
    }
  }

  const indices = [];
  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const a = r * cols + c;
      const b = r * cols + c + 1;
      const d = (r + 1) * cols + c;
      const e = (r + 1) * cols + c + 1;
      if (maskFn && !(maskFn(a) && maskFn(b) && maskFn(d) && maskFn(e))) continue;
      indices.push(a, d, b, b, d, e);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

export function buildCurvedGeometry(heightmap, rows, cols, widthMm, heightMm, minT, maxT, curveDegrees) {
  const thickness = thicknessGrid(heightmap, rows, cols, minT, maxT);
  const curveRad = (curveDegrees * Math.PI) / 180;
  const radius = widthMm / curveRad;
  const positions = new Float32Array(rows * cols * 3);

  for (let r = 0; r < rows; r++) {
    const z = heightMm - (r / (rows - 1)) * heightMm;
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      const theta = -curveRad / 2 + (c / (cols - 1)) * curveRad;
      const rOuter = radius + thickness[i];
      positions[i * 3] = rOuter * Math.sin(theta);
      positions[i * 3 + 1] = rOuter * Math.cos(theta);
      positions[i * 3 + 2] = z;
    }
  }

  const indices = [];
  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const a = r * cols + c;
      const b = r * cols + c + 1;
      const d = (r + 1) * cols + c;
      const e = (r + 1) * cols + c + 1;
      indices.push(a, d, b, b, d, e);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

function gridPoint(i, rows, cols, widthMm, heightMm) {
  const r = Math.floor(i / cols);
  const c = i % cols;
  const x = (c / (cols - 1)) * widthMm;
  const y = heightMm - (r / (rows - 1)) * heightMm;
  return [x, y];
}

export function circleMask(rows, cols, widthMm, heightMm) {
  const cx = widthMm / 2;
  const cy = heightMm / 2;
  const rx = widthMm / 2;
  const ry = heightMm / 2;
  return (i) => {
    const [x, y] = gridPoint(i, rows, cols, widthMm, heightMm);
    const nx = (x - cx) / rx;
    const ny = (y - cy) / ry;
    return nx * nx + ny * ny <= 1.0;
  };
}

function heartPolygonPoints(widthMm, heightMm, n = 200) {
  const xs = [];
  const ys = [];
  for (let k = 0; k < n; k++) {
    const t = (k / (n - 1)) * Math.PI * 2;
    xs.push(16 * Math.pow(Math.sin(t), 3));
    ys.push(13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t));
  }
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const pts = [];
  for (let k = 0; k < n; k++) {
    pts.push([
      ((xs[k] - xMin) / (xMax - xMin)) * widthMm,
      ((ys[k] - yMin) / (yMax - yMin)) * heightMm,
    ]);
  }
  return pts;
}

function pointInPolygon(x, y, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

export function heartMask(rows, cols, widthMm, heightMm) {
  const poly = heartPolygonPoints(widthMm, heightMm);
  return (i) => {
    const [x, y] = gridPoint(i, rows, cols, widthMm, heightMm);
    return pointInPolygon(x, y, poly);
  };
}
