/** Three.js interactive scene: camera frustum, reference object, and DORI.

World coordinates are meters. The floor is y=0; the camera is mounted at
(0, mountHeight, 0) and faces negative Z.
*/

const Scene3D = (function () {
  let scene, viewCamera, renderer, controls;
  let frustumGroup, objectGroup, doriRings, camGroup, mountPole;
  let container;
  let animId = null;
  let framedOnce = false;
  let lastMountY = null;
  /** @type {{camY:number, apexY:number, objectY:number}|null} */
  let lastGeometry = null;

  const OBJECT_COLORS = {
    donut: 0xf4a460,
    cola_can: 0xe74c3c,
    basket: 0x3498db,
    person: 0x9b59b6,
    car: 0x95a5a6,
  };

  function init() {
    container = document.getElementById('viewport3d');
    if (!container || typeof THREE === 'undefined') return;

    scene = new THREE.Scene();
    // A light neutral background keeps models and translucent zones readable.
    scene.background = new THREE.Color(0xd4d8de);
    scene.fog = new THREE.Fog(0xd4d8de, 30, 130);

    viewCamera = new THREE.PerspectiveCamera(55, 1, 0.05, 200);
    viewCamera.position.set(4, 3, 5);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const initH = Math.max(120, container.clientHeight || 420);
    renderer.setSize(container.clientWidth, initH);
    viewCamera.aspect = container.clientWidth / initH;
    viewCamera.updateProjectionMatrix();
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const hint = document.createElement('div');
    hint.className = 'viz3d-hint';
    hint.textContent = 'ЛКМ — вращение · ПКМ — сдвиг · колёсико — zoom · камера смотрит по −Z';
    container.appendChild(hint);

    if (typeof THREE.OrbitControls !== 'undefined') {
      controls = new THREE.OrbitControls(viewCamera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = 0.3;
      controls.maxDistance = 80;
      controls.target.set(0, 1.5, -1);
    }

    // Key light above and behind the CCTV camera, plus a softer fill light.
    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    scene.add(new THREE.HemisphereLight(0xffffff, 0xa8b0b8, 0.45));
    const dir = new THREE.DirectionalLight(0xffffff, 1.15);
    dir.position.set(0, 10, 8);
    dir.target.position.set(0, 1.5, -6);
    scene.add(dir);
    scene.add(dir.target);
    const fill = new THREE.DirectionalLight(0xe8f0ff, 0.4);
    fill.position.set(-4, 4, 3);
    scene.add(fill);

    // Grid scale: one cell represents three meters.
    const gridSize = 60;
    const gridDiv = 20; // 60/20 = 3 meters per cell
    const grid = new THREE.GridHelper(gridSize, gridDiv, 0x9aa3ad, 0xc5ccd3);
    scene.add(grid);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(gridSize, gridSize),
      new THREE.MeshStandardMaterial({ color: 0xc8ced6, roughness: 0.92, metalness: 0 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = 0;
    scene.add(floor);

    // Mounting pole from the floor to the camera.
    mountPole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.02, 0.02, 1, 8),
      new THREE.MeshStandardMaterial({ color: 0x484f58 })
    );
    scene.add(mountPole);

    camGroup = new THREE.Group();
    const camBody = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 20, 20),
      new THREE.MeshStandardMaterial({
        color: 0x58a6ff,
        emissive: 0x1a4a80,
        emissiveIntensity: 0.4,
      })
    );
    camGroup.add(camBody);
    const camCone = new THREE.Mesh(
      new THREE.ConeGeometry(0.08, 0.25, 12),
      new THREE.MeshStandardMaterial({ color: 0x79c0ff })
    );
    camCone.rotation.x = Math.PI / 2;
    camCone.position.z = -0.2;
    camGroup.add(camCone);
    scene.add(camGroup);

    frustumGroup = new THREE.Group();
    scene.add(frustumGroup);

    doriRings = new THREE.Group();
    scene.add(doriRings);

    objectGroup = new THREE.Group();
    scene.add(objectGroup);

    window.addEventListener('resize', onResize);
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => onResize());
      ro.observe(container);
    }
    if (animId) cancelAnimationFrame(animId);
    framedOnce = false;
    animate();
    // Flex height may settle after first layout paint.
    requestAnimationFrame(() => onResize());
  }

  function onResize() {
    if (!container || !renderer || !viewCamera) return;
    if (container.hidden) return;
    const w = container.clientWidth;
    const h = Math.max(120, container.clientHeight || 420);
    if (w < 2 || h < 2) return;
    renderer.setSize(w, h);
    viewCamera.aspect = w / h;
    viewCamera.updateProjectionMatrix();
  }

  function animate() {
    animId = requestAnimationFrame(animate);
    if (controls) controls.update();
    if (renderer && scene && viewCamera) renderer.render(scene, viewCamera);
  }

  function _safeTanHalfFov(fovDeg) {
    const halfDeg = Math.min(fovDeg / 2.0, 89.95);
    return Math.tan((halfDeg * Math.PI) / 180.0);
  }

  /** Half-width of a finite forward-plane footprint. */
  function _vizHalfWidth(hfovDeg, planeZ) {
    const halfDeg = Math.min(hfovDeg / 2.0, 89.95);
    return planeZ * Math.tan((halfDeg * Math.PI) / 180.0);
  }

  /** Display-only fallback when a 180°+ footprint is mathematically unbounded. */
  function _fallbackHalfWidth(planeZ, objectZ) {
    return Math.max(objectZ * 2, planeZ, 2.0);
  }

  function clearGroup(group) {
    while (group.children.length) {
      const c = group.children[0];
      group.remove(c);
      if (c.geometry) c.geometry.dispose();
      if (c.material) {
        if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
        else c.material.dispose();
      }
    }
  }

  function makeObjectMesh(objectId, dims) {
    const color = OBJECT_COLORS[objectId] || 0x238636;
    const mat = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.25,
      roughness: 0.45,
      metalness: 0.1,
    });
    const edgeMat = new THREE.LineBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.6,
    });

    let mesh;
    const w = dims.width_m;   // X extent
    const h = dims.height_m;  // Y extent
    const d = dims.depth_m || w; // Z extent (depth)

    switch (objectId) {
      case 'donut':
        // The torus lies in XY and faces the camera along negative Z.
        // Fit its outer diameter to width and ring thickness to depth.
        mesh = new THREE.Mesh(
          new THREE.TorusGeometry(Math.max(w * 0.33, 0.001), Math.max(d * 0.5, 0.001), 16, 32),
          mat
        );
        // Scale vertically when the requested physical box is not square.
        mesh.scale.y = h / w;
        break;
      case 'cola_can':
        mesh = new THREE.Mesh(new THREE.CylinderGeometry(w / 2, w / 2, h, 24), mat);
        break;
      case 'basket':
        mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
        break;
      case 'person': {
        const body = new THREE.Mesh(
          new THREE.CylinderGeometry(w * 0.22, w * 0.28, h * 0.65, 12),
          mat
        );
        body.position.y = 0;
        const head = new THREE.Mesh(new THREE.SphereGeometry(w * 0.22, 16, 16), mat);
        head.position.y = h * 0.35;
        const grp = new THREE.Group();
        grp.add(body);
        grp.add(head);
        mesh = grp;
        break;
      }
      case 'car':
        mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h * 0.5, d), mat);
        break;
      default:
        mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d * 0.5), mat);
    }

    if (mesh.geometry) {
      mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry), edgeMat));
    }
    return mesh;
  }

  const MODEL_FILES = {
    donut: '/models/donut_2.0.glb',
    cola_can: '/models/coca-cola_can__can_of_soda.glb',
    basket: '/models/shopping_bag.glb',
    person: '/models/free_download_athletic_african_man_walking_223.glb',
    car: '/models/free_porsche_911_carrera_4s.glb',
  };

  const _modelCache = new Map();
  const _fittedTemplateCache = new Map();

  function loadModel(objectId) {
    const file = MODEL_FILES[objectId];
    if (!file) return Promise.resolve(null);
    if (_modelCache.has(objectId)) return _modelCache.get(objectId);
    if (typeof THREE.GLTFLoader === 'undefined') return Promise.resolve(null);

    const p = new Promise((resolve) => {
      const loader = new THREE.GLTFLoader();
      loader.load(
        file,
        (gltf) => resolve(gltf.scene || null),
        undefined,
        () => resolve(null)
      );
    });
    _modelCache.set(objectId, p);
    return p;
  }

  function _addPhysicalBBox(xOff, camY, yOff, oz, objectDims) {
    const w = objectDims.width_m;
    const h = objectDims.height_m;
    const d = objectDims.depth_m || w;
    const geom = new THREE.BoxGeometry(w, h, d);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geom),
      new THREE.LineBasicMaterial({ color: 0x58a6ff, transparent: true, opacity: 0.85 })
    );
    edges.position.set(xOff, camY + yOff, -oz);
    objectGroup.add(edges);
    geom.dispose();
  }

  /**
   * Draw a frustum from the camera apex to the coverage rectangle.
   * Apex and corners use world coordinates.
   */
  function addFrustum(apex, corners, color, opacity) {
    // Translucent frustum faces.
    const faces = [
      [apex, corners[0], corners[1]],
      [apex, corners[1], corners[2]],
      [apex, corners[2], corners[3]],
      [apex, corners[3], corners[0]],
    ];
    faces.forEach((tri) => {
      const geom = new THREE.BufferGeometry();
      const verts = new Float32Array([
        tri[0].x, tri[0].y, tri[0].z,
        tri[1].x, tri[1].y, tri[1].z,
        tri[2].x, tri[2].y, tri[2].z,
      ]);
      geom.setAttribute('position', new THREE.BufferAttribute(verts, 3));
      geom.computeVertexNormals();
      frustumGroup.add(
        new THREE.Mesh(
          geom,
          new THREE.MeshBasicMaterial({
            color,
            transparent: true,
            opacity,
            side: THREE.DoubleSide,
            depthWrite: false,
          })
        )
      );
    });

    const lineMat = new THREE.LineBasicMaterial({ color });
    corners.forEach((c) => {
      const lg = new THREE.BufferGeometry().setFromPoints([apex, c]);
      frustumGroup.add(new THREE.Line(lg, lineMat));
    });

    // Coverage rectangle.
    const rect = [...corners, corners[0]];
    frustumGroup.add(
      new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(rect),
        new THREE.LineBasicMaterial({ color: 0x3fb950 })
      )
    );

    // Optical axis through the coverage center.
    const center = new THREE.Vector3(
      (corners[0].x + corners[2].x) / 2,
      (corners[0].y + corners[2].y) / 2,
      (corners[0].z + corners[2].z) / 2
    );
    frustumGroup.add(
      new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([apex, center]),
        new THREE.LineBasicMaterial({ color: 0xf78166, transparent: true, opacity: 0.85 })
      )
    );
  }

  function frameView(camY, z, halfW) {
    if (!controls) return;
    const lookZ = -Math.max(z, 0.5) * 0.55;
    controls.target.set(0, camY, lookZ);
    const span = Math.max(halfW * 2, z, camY, 1.5) * 1.1;
    viewCamera.position.set(span * 0.85, camY + span * 0.35, span * 0.55);
    controls.update();
  }

  function update(
    result,
    mountHeight,
    objectDims,
    objectDistance,
    lensType,
    objectId
  ) {
    if (!frustumGroup) init();
    if (!result) return;

    clearGroup(frustumGroup);
    clearGroup(doriRings);
    clearGroup(objectGroup);

    // Position the camera at its configured mounting height.
    const camY = Math.max(Number(mountHeight) || 0, 0.05);
    camGroup.position.set(0, camY, 0);

    // Resize the mounting pole.
    if (mountPole) {
      mountPole.geometry.dispose();
      mountPole.geometry = new THREE.CylinderGeometry(0.02, 0.02, camY, 8);
      mountPole.position.set(0, camY / 2, 0);
    }

    const z = Math.max(result.coverage.distance_m, 0.05);
    const objZ =
      result && result.projection && result.projection.object_distance_m
        ? Math.max(result.projection.object_distance_m, 0.05)
        : Math.max(Number(objectDistance) || z, 0.05);
    const halfW =
      result.coverage.width_m !== null
        ? result.coverage.width_m / 2
        : _fallbackHalfWidth(z, objZ);
    const vfovRad = (result.fov.vfov_deg * Math.PI) / 180;
    const halfH =
      result.coverage.height_m !== null
        ? result.coverage.height_m / 2
        : Math.min(z * Math.tan(vfovRad / 2), halfW * 0.75);

    // The frustum apex is the camera position, not the floor projection.
    const apex = new THREE.Vector3(0, camY, 0);

    // The coverage plane is normal to the negative-Z optical axis.
    const corners = [
      new THREE.Vector3(-halfW, camY - halfH, -z),
      new THREE.Vector3(halfW, camY - halfH, -z),
      new THREE.Vector3(halfW, camY + halfH, -z),
      new THREE.Vector3(-halfW, camY + halfH, -z),
    ];

    const frustumColor = lensType === 'fisheye_equidistant' ? 0xd29922 : 0x58a6ff;
    addFrustum(apex, corners, frustumColor, 0.12);

    lastGeometry = {
      camY,
      apexY: apex.y,
      objectY: camY,
      halfW,
      hfovDeg: result.fov.hfov_deg,
      planeZ: z,
    };

    // Top-view DORI wedges show the horizontal FOV footprint by distance.
    // Colors match --id / --rec / --obs / --det in style.css.
    const doriColors = [0x58a6ff, 0x3fb950, 0xd29922, 0xf85149];
    const doriKeys = ['detection_m', 'observation_m', 'recognition_m', 'identification_m'];
    let doriCount = 0;

    doriKeys.forEach((key, i) => {
      const dist = result.dori[key];
      if (!dist || dist <= 0) return;
      const rw = _vizHalfWidth(result.fov.hfov_deg, dist);
      const y = 0.02 + i * 0.002; // Avoid z-fighting between nested wedges.

      // The apex is below the camera; the base lies at z=-dist.
      const p0 = new THREE.Vector3(0, y, 0);
      const p1 = new THREE.Vector3(-rw, y, -dist);
      const p2 = new THREE.Vector3(rw, y, -dist);

      const geom = new THREE.BufferGeometry();
      const verts = new Float32Array([
        p0.x, p0.y, p0.z,
        p1.x, p1.y, p1.z,
        p2.x, p2.y, p2.z,
      ]);
      geom.setAttribute('position', new THREE.BufferAttribute(verts, 3));
      const mat = new THREE.MeshBasicMaterial({
        color: doriColors[i],
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.14 + i * 0.07,
        depthWrite: false,
      });
      doriRings.add(new THREE.Mesh(geom, mat));
      doriCount += 1;
    });

    const proj = result && result.projection ? result.projection : null;
    const yOff = proj && proj.object_offset_y_m !== undefined ? Number(proj.object_offset_y_m) || 0.0 : 0.0;
    const xOff = proj && proj.object_offset_x_m !== undefined ? Number(proj.object_offset_x_m) || 0.0 : 0.0;

    // Place the object using its projected X/Y offsets.
    if (objectDims) {
      const oz = objZ;
      const id = objectId || 'cola_can';

      _addPhysicalBBox(xOff, camY, yOff, oz, objectDims);

      // fallback primitive immediately
      const fallback = makeObjectMesh(id, objectDims);
      const fallbackHolder = new THREE.Group();
      fallbackHolder.position.set(xOff, camY + yOff, -oz);
      fallback.position.set(0, 0, 0);
      fallbackHolder.add(fallback);
      objectGroup.add(fallbackHolder);
      lastGeometry.objectY = camY + yOff;

      // async replace with glb model if present
      loadModel(id).then((model) => {
        if (!model) return;

        objectGroup.remove(fallbackHolder);

        const cacheKey = ModelPrep.templateCacheKey(id, objectDims, objectDims.orientation, objectDims);
        let template = _fittedTemplateCache.get(cacheKey);
        if (!template) {
          template = ModelPrep.prepareTemplate(
            model.clone(true),
            objectDims,
            objectDims.orientation,
            objectDims
          );
          _fittedTemplateCache.set(cacheKey, template);
        }

        const world = { x: xOff, y: camY + yOff, z: -oz };
        lastMeshHolder = ModelPrep.placeInstance(template, world, objectDims);
        objectGroup.add(lastMeshHolder);
      });

      // Vertical guide to the floor.
      const drop = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(xOff, camY + yOff - objectDims.height_m / 2, -oz),
          new THREE.Vector3(xOff, 0, -oz),
        ]),
        new THREE.LineDashedMaterial({
          color: 0x8b949e,
          dashSize: 0.08,
          gapSize: 0.05,
          transparent: true,
          opacity: 0.7,
        })
      );
      drop.computeLineDistances();
      objectGroup.add(drop);

      const label = makeTextSprite(objectDims.label || objectId);
      // Keep the marker compact and place the label above it.
      label.position.set(xOff, camY + yOff + objectDims.height_m / 2 + 0.25, -oz);
      label.scale.set(0.9, 0.45, 1);
      objectGroup.add(label);
    }

    // Expose minimal deterministic state for UI tests.
    if (lastGeometry) lastGeometry.doriCount = doriCount;

    // Reframe only initially or after a mounting-height change.
    const mountChanged = lastMountY === null || Math.abs(lastMountY - camY) > 0.05;
    if (!framedOnce || mountChanged) {
      const dists = doriKeys.map((k) => result.dori && result.dori[k]).filter((v) => typeof v === 'number');
      const maxDori = dists.length ? Math.max(...dists) : z;
      // Keep the overview camera close enough to show nearby object orientation.
      const objZ = result.projection && result.projection.object_distance_m ? result.projection.object_distance_m : z;
      frameView(camY, Math.max(z, Math.min(maxDori, Math.max(objZ * 2.2, z))), halfW);
      framedOnce = true;
      lastMountY = camY;
    }
  }

  let lastMeshHolder = null;

  function getDebugObjectState() {
    if (!lastMeshHolder) return null;
    const box = new THREE.Box3().setFromObject(lastMeshHolder);
    const center = box.getCenter(new THREE.Vector3());
    return {
      holder: lastMeshHolder.position.toArray(),
      meshCenterWorld: center.toArray(),
    };
  }

  function makeTextSprite(text) {
    const c = document.createElement('canvas');
    const ctx = c.getContext('2d');
    c.width = 256;
    c.height = 64;
    ctx.fillStyle = 'rgba(13,17,23,0.85)';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.strokeStyle = '#58a6ff';
    ctx.lineWidth = 3;
    ctx.strokeRect(2, 2, c.width - 4, c.height - 4);
    ctx.fillStyle = '#e6edf3';
    ctx.font = 'bold 24px system-ui';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, c.width / 2, c.height / 2);
    const tex = new THREE.CanvasTexture(c);
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
    return new THREE.Sprite(mat);
  }

  function hasWebGL() {
    if (!container) return false;
    const canvas = container.querySelector('canvas');
    if (!canvas) return false;
    try {
      return !!(canvas.getContext('webgl') || canvas.getContext('webgl2'));
    } catch {
      return false;
    }
  }

  function getLastGeometry() {
    return lastGeometry;
  }

  function getFrustumState() {
    if (!lastGeometry) return null;
    return {
      camY: lastGeometry.camY,
      apexY: lastGeometry.apexY,
      objectY: lastGeometry.objectY,
      doriCount: lastGeometry.doriCount || 0,
      halfW: lastGeometry.halfW,
      hfovDeg: lastGeometry.hfovDeg,
      planeZ: lastGeometry.planeZ,
    };
  }

  return { init, update, resize: onResize, hasWebGL, getLastGeometry, getDebugObjectState, getFrustumState };
})();
