/** 2D camera view on a resolution_w × resolution_h sensor canvas.
 *
 * The internal canvas matches the sensor resolution. CSS scales it while
 * preserving the configured aspect ratio.
 */

const Viewport2D = (function () {
  const canvas = () => document.getElementById('viewport2d');

  const MODEL_FILES = {
    donut: '/models/donut_2.0.glb',
    cola_can: '/models/coca-cola_can__can_of_soda.glb',
    basket: '/models/shopping_bag.glb',
    person: '/models/free_download_athletic_african_man_walking_223.glb',
    car: '/models/free_porsche_911_carrera_4s.glb',
  };

  const _modelCache = new Map();
  const _fittedTemplateCache = new Map();
  let _offscreenCanvas = null;
  let _offscreenRenderer = null;
  let _offscreenScene = null;
  let _offscreenCamera = null;
  let _offscreenMeshRoot = null;
  let _offscreenKeyLight = null;
  let _offscreenFillLight = null;
  let _lastScreenBBox = null;
  let _lastApiBBox = null;

  function _projectWorldToScreen(camera, point, W, H) {
    const ndc = point.clone().project(camera);
    return {
      u: (ndc.x * 0.5 + 0.5) * W,
      v: (-ndc.y * 0.5 + 0.5) * H,
    };
  }

  /** Pinhole screen AABB of physical object box (same camera as offscreen render). */
  function _screenBBoxFromPhysicalBox(camera, world, dims, W, H) {
    const hw = dims.width_m / 2.0;
    const hh = dims.height_m / 2.0;
    const hd = (dims.depth_m || dims.width_m) / 2.0;
    const cx = world.x;
    const cy = world.y;
    const cz = world.z;
    let minU = Infinity;
    let maxU = -Infinity;
    let minV = Infinity;
    let maxV = -Infinity;

    for (const dx of [-1, 1]) {
      for (const dy of [-1, 1]) {
        for (const dz of [-1, 1]) {
          const p = new THREE.Vector3(cx + dx * hw, cy + dy * hh, cz + dz * hd);
          const { u, v } = _projectWorldToScreen(camera, p, W, H);
          minU = Math.min(minU, u);
          maxU = Math.max(maxU, u);
          minV = Math.min(minV, v);
          maxV = Math.max(maxV, v);
        }
      }
    }
    return {
      left: minU,
      top: minV,
      right: maxU,
      bottom: maxV,
      width: maxU - minU,
      height: maxV - minV,
      center_u: (minU + maxU) / 2.0,
      center_v: (minV + maxV) / 2.0,
    };
  }

  function _screenBBoxFromMesh(camera, meshRoot, W, H) {
    const box = new THREE.Box3().setFromObject(meshRoot);
    const corners = [
      new THREE.Vector3(box.min.x, box.min.y, box.min.z),
      new THREE.Vector3(box.min.x, box.min.y, box.max.z),
      new THREE.Vector3(box.min.x, box.max.y, box.min.z),
      new THREE.Vector3(box.min.x, box.max.y, box.max.z),
      new THREE.Vector3(box.max.x, box.min.y, box.min.z),
      new THREE.Vector3(box.max.x, box.min.y, box.max.z),
      new THREE.Vector3(box.max.x, box.max.y, box.min.z),
      new THREE.Vector3(box.max.x, box.max.y, box.max.z),
    ];
    let minU = Infinity;
    let maxU = -Infinity;
    let minV = Infinity;
    let maxV = -Infinity;
    corners.forEach((p) => {
      const { u, v } = _projectWorldToScreen(camera, p, W, H);
      minU = Math.min(minU, u);
      maxU = Math.max(maxU, u);
      minV = Math.min(minV, v);
      maxV = Math.max(maxV, v);
    });
    return {
      left: minU,
      top: minV,
      right: maxU,
      bottom: maxV,
      width: maxU - minU,
      height: maxV - minV,
      center_u: (minU + maxU) / 2.0,
      center_v: (minV + maxV) / 2.0,
    };
  }

  function _resetOffscreen() {
    if (_offscreenRenderer) {
      _offscreenRenderer.dispose();
    }
    _offscreenCanvas = null;
    _offscreenRenderer = null;
    _offscreenScene = null;
    _offscreenCamera = null;
    _offscreenMeshRoot = null;
    _lastArgs = null;
    _lastScreenBBox = null;
    _lastApiBBox = null;
  }

  let _lastArgs = null;
  let _resW = 0;
  let _resH = 0;

  function setResolution(width, height) {
    const c = canvas();
    if (!c) return;
    const w = Math.max(1, Math.round(width));
    const h = Math.max(1, Math.round(height));
    if (w !== _resW || h !== _resH) {
      _resW = w;
      _resH = h;
      c.width = w;
      c.height = h;
      _resetOffscreen();
    }
    const wrap = c.parentElement;
    if (wrap) wrap.style.aspectRatio = `${w} / ${h}`;
    const title = document.getElementById('viewport2dTitle');
    if (title) title.textContent = `2D — вид камеры (${w}×${h} px)`;
  }

  function _degToRad(deg) {
    return (deg * Math.PI) / 180.0;
  }

  function _effectiveFocalMm(cameraParams) {
    if (
      cameraParams &&
      cameraParams.lens_type === 'fisheye_equidistant' &&
      cameraParams.fisheye_fov_deg
    ) {
      const thetaMaxRad = _degToRad(cameraParams.fisheye_fov_deg / 2.0);
      // Equidistant calibration uses f = (sensor/2) / theta_max, not tan(theta).
      return (cameraParams.sensor_width_mm / 2.0) / Math.max(thetaMaxRad, 1e-9);
    }
    return cameraParams.focal_length_mm;
  }

  function _ensureOffscreen(W, H) {
    if (!_offscreenCanvas || _offscreenCanvas.width !== W || _offscreenCanvas.height !== H) {
      _offscreenCanvas = document.createElement('canvas');
      _offscreenCanvas.width = W;
      _offscreenCanvas.height = H;
    }
    if (!_offscreenRenderer) {
      _offscreenRenderer = new THREE.WebGLRenderer({ canvas: _offscreenCanvas, alpha: true, antialias: true });
      _offscreenRenderer.setPixelRatio(1);
    }
    _offscreenRenderer.setSize(W, H, false);
    if (!_offscreenScene) {
      _offscreenScene = new THREE.Scene();
      _offscreenScene.background = null;
      // Ambient light plus a key light behind the camera, which faces negative Z.
      _offscreenScene.add(new THREE.AmbientLight(0xffffff, 0.95));
      _offscreenScene.add(new THREE.HemisphereLight(0xffffff, 0xb0b8c0, 0.55));
      _offscreenKeyLight = new THREE.DirectionalLight(0xffffff, 1.35);
      _offscreenKeyLight.position.set(0, 4, 6);
      _offscreenKeyLight.target.position.set(0, 0, -4);
      _offscreenScene.add(_offscreenKeyLight);
      _offscreenScene.add(_offscreenKeyLight.target);
      _offscreenFillLight = new THREE.DirectionalLight(0xe8f0ff, 0.45);
      _offscreenFillLight.position.set(-2, 2, 3);
      _offscreenScene.add(_offscreenFillLight);
      _offscreenMeshRoot = new THREE.Group();
      _offscreenScene.add(_offscreenMeshRoot);
    }
    if (!_offscreenCamera) _offscreenCamera = new THREE.PerspectiveCamera(50, W / H, 0.05, 500);
  }

  async function _loadBaseModel(objectId) {
    const file = MODEL_FILES[objectId];
    if (!file) return null;
    if (_modelCache.has(objectId)) return _modelCache.get(objectId);
    if (typeof THREE.GLTFLoader === 'undefined') return null;
    const p = new Promise((resolve) => {
      const loader = new THREE.GLTFLoader();
      loader.load(file, (gltf) => resolve(gltf.scene || null), undefined, () => resolve(null));
    });
    _modelCache.set(objectId, p);
    return p;
  }

  async function _getOrPrepareTemplate(objectId, dims, orientation, objectPreset) {
    const cacheKey = ModelPrep.templateCacheKey(objectId, dims, orientation, objectPreset);
    if (_fittedTemplateCache.has(cacheKey)) return _fittedTemplateCache.get(cacheKey);

    const base = await _loadBaseModel(objectId);
    if (!base) return null;

    const template = ModelPrep.prepareTemplate(base.clone(true), dims, orientation, objectPreset);
    _fittedTemplateCache.set(cacheKey, template);
    return template;
  }

  function _renderObjectSnapshot(ctx, objectId, cameraParams, proj, objectPreset) {
    const W = ctx.canvas.width;
    const H = ctx.canvas.height;
    if (typeof THREE === 'undefined') return;
    _ensureOffscreen(W, H);

    const fEff = _effectiveFocalMm(cameraParams);
    const vfovDeg =
      cameraParams.lens_type === 'fisheye_equidistant'
        ? (cameraParams.sensor_height_mm / Math.max(fEff, 1e-9)) * (180.0 / Math.PI)
        : (2.0 * Math.atan(cameraParams.sensor_height_mm / (2.0 * Math.max(fEff, 1e-9)))) *
          (180.0 / Math.PI);
    _offscreenCamera.fov = vfovDeg;
    _offscreenCamera.aspect = W / H;
    _offscreenCamera.near = 0.05;
    _offscreenCamera.far = 200;
    _offscreenCamera.updateProjectionMatrix();

    const world = ModelPrep.worldPoseFromProjection(proj, cameraParams.mount_height_m);
    _offscreenCamera.position.set(0, world.camY, 0);
    _offscreenCamera.lookAt(0, world.camY, -1);

    // Place the key light above and behind the camera to illuminate the object front.
    if (_offscreenKeyLight) {
      const objZ = -Math.max(Number(proj.object_distance_m) || 1, 0.2);
      _offscreenKeyLight.position.set(0, world.camY + 2.5, 4);
      _offscreenKeyLight.target.position.set(0, world.camY, objZ);
      _offscreenKeyLight.target.updateMatrixWorld();
    }
    if (_offscreenFillLight) {
      _offscreenFillLight.position.set(-2.5, world.camY + 1.0, 2.5);
    }

    const dims = {
      width_m: proj.object_width_m,
      height_m: proj.object_height_m,
      depth_m: proj.object_depth_m || proj.object_width_m,
    };
    const orientation = proj.orientation || 'upright';

    if (_offscreenMeshRoot) _offscreenMeshRoot.clear();

    const cacheKey = ModelPrep.templateCacheKey(objectId, dims, orientation, objectPreset);
    const template = _fittedTemplateCache.get(cacheKey);

    const doRender = (prepared) => {
      if (!prepared || !_offscreenMeshRoot) return;
      _offscreenMeshRoot.clear();
      const w = ModelPrep.worldPoseFromProjection(proj, cameraParams.mount_height_m);
      const instance = ModelPrep.placeInstance(prepared, w, objectPreset);
      _offscreenMeshRoot.add(instance);
      _offscreenRenderer.render(_offscreenScene, _offscreenCamera);

      const dims = {
        width_m: proj.object_width_m,
        height_m: proj.object_height_m,
        depth_m: proj.object_depth_m || proj.object_width_m,
      };
      _lastScreenBBox = _screenBBoxFromMesh(_offscreenCamera, instance, W, H);
      const phys = _screenBBoxFromPhysicalBox(_offscreenCamera, w, dims, W, H);
      // For pinhole rendering, the physical AABB is the API alignment reference.
      if (!cameraParams || cameraParams.lens_type !== 'fisheye_equidistant') {
        _lastScreenBBox = phys;
      }

      ctx.drawImage(_offscreenCanvas, 0, 0, W, H);
    };

    if (template) {
      doRender(template);
      return;
    }

    _lastArgs = { ctx, objectId, cameraParams, proj, objectPreset, W, H };
    _getOrPrepareTemplate(objectId, dims, orientation, objectPreset).then((prepared) => {
      if (!_lastArgs || _lastArgs.objectId !== objectId) return;
      if (_lastArgs.W !== ctx.canvas.width || _lastArgs.H !== ctx.canvas.height) return;
      doRender(prepared);
    });
  }

  function _drawFrameBackground(ctx, W, H) {
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#ececec');
    grad.addColorStop(1, '#dcdcdc');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = '#c8c8c8';
    ctx.lineWidth = 1;
    const gridStepX = Math.max(40, Math.round(W / 16));
    const gridStepY = Math.max(40, Math.round(H / 16));
    for (let x = 0; x <= W; x += gridStepX) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    for (let y = 0; y <= H; y += gridStepY) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    ctx.strokeStyle = '#a0a0a0';
    ctx.lineWidth = 2;
    ctx.strokeRect(0.5, 0.5, W - 1, H - 1);

    ctx.strokeStyle = 'rgba(40, 100, 180, 0.45)';
    ctx.beginPath();
    ctx.moveTo(W / 2, 0);
    ctx.lineTo(W / 2, H);
    ctx.moveTo(0, H / 2);
    ctx.lineTo(W, H / 2);
    ctx.stroke();
  }

  function draw(result, objectId, cvThreshold, cameraParams, objectPreset) {
    const c = canvas();
    if (!c) return;

    if (cameraParams) setResolution(cameraParams.resolution_w, cameraParams.resolution_h);

    const ctx = c.getContext('2d');
    const W = c.width;
    const H = c.height;

    _drawFrameBackground(ctx, W, H);

    if (!result || !result.projection) {
      ctx.fillStyle = '#57606a';
      ctx.font = '20px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText('Выберите объект и дождитесь расчёта', W / 2, H / 2);
      return;
    }

    const proj = result.projection;
    const pw = Math.max(proj.width_px, 1);
    const ph = Math.max(proj.height_px, 1);
    const cx2d = Number(proj.center_u_px);
    const cy2d = Number(proj.center_v_px);
    const bx = cx2d - pw / 2;
    const by = cy2d - ph / 2;
    const pass = Math.min(pw, ph) >= cvThreshold;

    _lastApiBBox = { left: bx, top: by, width: pw, height: ph, center_u: cx2d, center_v: cy2d };

    if (cameraParams && proj.object_width_m && proj.object_height_m) {
      _renderObjectSnapshot(ctx, objectId || proj.object_id, cameraParams, proj, objectPreset);
    }

    ctx.strokeStyle = pass ? '#1a7f37' : '#cf222e';
    ctx.lineWidth = Math.max(1, Math.round(Math.min(W, H) / 400));
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(bx, by, pw, ph);
    ctx.setLineDash([]);

    const labelSize = Math.max(11, Math.min(18, Math.max(ph, 16) * 0.12));
    ctx.fillStyle = '#1f2328';
    ctx.font = `bold ${labelSize}px system-ui`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(proj.label || proj.object_id, cx2d, by + ph + 8);

    const tag = `${Math.round(pw)} × ${Math.round(ph)} px`;
    const tagFont = Math.max(12, Math.min(18, Math.round(Math.min(W, H) / 50)));
    const tagY = by - tagFont > 20 ? by - tagFont : by + ph + tagFont + 4;
    ctx.font = `bold ${tagFont}px system-ui`;
    const tw = ctx.measureText(tag).width;
    ctx.fillStyle = pass ? 'rgba(26,127,55,0.92)' : 'rgba(207,34,46,0.92)';
    ctx.fillRect(cx2d - tw / 2 - 8, tagY - tagFont, tw + 16, tagFont + 8);
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(tag, cx2d, tagY - tagFont / 2 + 2);
  }

  function isBlank() {
    const c = canvas();
    if (!c) return true;
    const ctx = c.getContext('2d');
    const d = ctx.getImageData(0, 0, Math.min(c.width, 8), Math.min(c.height, 8)).data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] < 200 || d[i + 1] < 200 || d[i + 2] < 200) return false;
    }
    return true;
  }

  return {
    draw,
    isBlank,
    canvas,
    setResolution,
    getResolution: () => ({ width: _resW, height: _resH }),
    getLastScreenBBox: () => _lastScreenBBox,
    getLastApiBBox: () => _lastApiBBox,
    getBBoxAlignment: () => {
      if (!_lastScreenBBox || !_lastApiBBox) return null;
      const sw = _lastScreenBBox.width;
      const sh = _lastScreenBBox.height;
      const aw = _lastApiBBox.width;
      const ah = _lastApiBBox.height;
      const wRatio = sw > 0 ? aw / sw : 0;
      const hRatio = sh > 0 ? ah / sh : 0;
      const cu = Math.abs(_lastScreenBBox.center_u - _lastApiBBox.center_u);
      const cv = Math.abs(_lastScreenBBox.center_v - _lastApiBBox.center_v);
      return { wRatio, hRatio, centerDeltaU: cu, centerDeltaV: cv };
    },
  };
})();
