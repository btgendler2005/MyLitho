import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

let scene, camera, renderer, controls, meshObj, container;
let backlightEnabled = false;

const NORMAL_BG = 0x14161a;
const BACKLIT_BG = 0x000000;

const normalMaterial = () =>
  new THREE.MeshStandardMaterial({
    color: 0xf1ead9,
    roughness: 0.8,
    metalness: 0.02,
    side: THREE.DoubleSide,
  });

const backlitMaterial = () =>
  new THREE.MeshBasicMaterial({
    vertexColors: true,
    side: THREE.DoubleSide,
  });

export function initViewer(el) {
  container = el;
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x14161a);

  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 5000);
  camera.up.set(0, 0, 1);
  camera.position.set(0, -180, 160);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x22262e, 1.15));
  const dirA = new THREE.DirectionalLight(0xffffff, 1.1);
  dirA.position.set(80, -120, 200);
  scene.add(dirA);
  const dirB = new THREE.DirectionalLight(0xffffff, 0.45);
  dirB.position.set(-100, 100, -60);
  scene.add(dirB);

  new ResizeObserver(onResize).observe(container);
  animate();
}

function onResize() {
  if (!container || container.clientWidth === 0) return;
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

export function setPreviewMesh(geometry) {
  if (meshObj) {
    scene.remove(meshObj);
    meshObj.geometry.dispose();
    meshObj.material.dispose();
  }
  const material = backlightEnabled ? backlitMaterial() : normalMaterial();
  meshObj = new THREE.Mesh(geometry, material);
  scene.add(meshObj);
  frameCamera(geometry);
}

export function setBacklightMode(enabled) {
  backlightEnabled = enabled;
  scene.background = new THREE.Color(enabled ? BACKLIT_BG : NORMAL_BG);
  if (meshObj) {
    meshObj.material.dispose();
    meshObj.material = enabled ? backlitMaterial() : normalMaterial();
  }
}

function frameCamera(geometry) {
  geometry.computeBoundingSphere();
  const s = geometry.boundingSphere;
  if (!s || !isFinite(s.radius) || s.radius === 0) return;
  const dist = s.radius * 2.4;
  const dir = new THREE.Vector3(0, -0.75, 0.65).normalize();
  camera.position.copy(s.center).addScaledVector(dir, dist);
  controls.target.copy(s.center);
  camera.near = Math.max(dist / 200, 0.01);
  camera.far = dist * 20;
  camera.updateProjectionMatrix();
}
