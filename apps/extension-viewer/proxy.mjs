import * as THREE from 'three';

/** Original abstract geometry; arbitrary scene units, no rig or physical model. */
export function createProxy(canvas, onLost) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
  camera.position.set(5.3, 3.5, 6.5);
  camera.lookAt(0, 0.5, 0);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x555555, 3));
  const light = new THREE.DirectionalLight(0xffffff, 3);
  light.position.set(3, 6, 4);
  scene.add(light);
  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x92999e, roughness: 0.85 });
  const faceMaterial = new THREE.MeshStandardMaterial({ color: 0xd5d8da, roughness: 0.9 });
  const darkMaterial = new THREE.MeshStandardMaterial({ color: 0x30383d, roughness: 0.8 });
  const model = new THREE.Group();
  scene.add(model);
  const geometries = [];
  function ellipsoid(parent, material, position, scale) {
    const geometry = new THREE.SphereGeometry(1, 32, 20);
    geometries.push(geometry);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(...position);
    mesh.scale.set(...scale);
    parent.add(mesh);
    return mesh;
  }
  ellipsoid(model, bodyMaterial, [0, 0.3, 0], [0.9, 0.45, 1.05]);
  // Exactly six static legs. No gait, joint actuation, or imported asset.
  for (const side of [-1, 1]) {
    for (const z of [-0.72, 0, 0.72]) {
      const leg = ellipsoid(model, darkMaterial, [side * 1.05, -0.05, z], [0.65, 0.13, 0.16]);
      leg.rotation.z = side * 0.35;
      ellipsoid(model, bodyMaterial, [side * 1.55, -0.32, z], [0.18, 0.13, 0.25]);
    }
  }
  const head = new THREE.Group();
  head.position.set(0, 1, 0.35);
  model.add(head);
  ellipsoid(head, bodyMaterial, [0, 0, 0], [0.68, 0.75, 0.57]);
  ellipsoid(head, faceMaterial, [0, -0.03, 0.45], [0.52, 0.4, 0.18]);
  for (const side of [-1, 1]) {
    const ear = ellipsoid(head, bodyMaterial, [side * 0.47, 0.65, 0], [0.19, 0.48, 0.16]);
    ear.rotation.z = side * -0.2;
    ellipsoid(head, darkMaterial, [side * 0.22, 0.08, 0.61], [0.09, 0.12, 0.06]);
  }
  ellipsoid(head, darkMaterial, [0, -0.16, 0.64], [0.12, 0.07, 0.08]);
  let disposed = false;
  function render(state = { expression: 'neutral', reaction: null, reactionProgress: 0 }, reduced = false) {
    if (disposed) return;
    const wave = state.reaction === 'acknowledge' && !reduced ? Math.sin(state.reactionProgress * Math.PI) : 0;
    model.rotation.x = wave * 0.12;
    model.position.y = wave * 0.08;
    head.rotation.z = state.expression === 'curious' && !reduced ? -0.14 : 0;
    renderer.render(scene, camera);
  }
  const lost = event => { event.preventDefault(); onLost(); };
  canvas.addEventListener('webglcontextlost', lost);
  return {
    render,
    resize(width, height) {
      if (disposed || width <= 0 || height <= 0) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      canvas.removeEventListener('webglcontextlost', lost);
      geometries.forEach(geometry => geometry.dispose());
      [bodyMaterial, faceMaterial, darkMaterial].forEach(material => material.dispose());
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
