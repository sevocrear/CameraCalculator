/** 2D вид камеры: pinhole-проекция на сенсор resolution_w × resolution_h. */

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
  let _lastArgs = null;

  function setResolution(width, height) {
    const c = canvas();
    if (!c) return;
    const w = Math.max(1, Math.round(width));
    const h = Math.max(1, Math.round(height));
    if (c.width !== w || c.height !== h) {
      c.width = w;
      c.height = h;
    }
    const title = document.getElementById('viewport2dTitle');
    if (title) title.textContent = `2D — вид камеры (${w}×${h})`;
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
      return (cameraParams.sensor_width_mm / 2.0) / Math.max(Math.tan(thetaMaxRad), 1e-9);
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
      _offscreenScene.add(new THREE.AmbientLight(0xffffff, 0.6));
      const dir = new THREE.DirectionalLight(0xffffff, 0.9);
      dir.position.set(2, 6, 3);
      _offscreenScene.add(dir);
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
    const vfovDeg = (2.0 * Math.atan(cameraParams.sensor_height_mm / (2.0 * Math.max(fEff, 1e-9)))) * (180.0 / Math.PI);
    _offscreenCamera.fov = vfovDeg;
    _offscreenCamera.aspect = W / H;
    _offscreenCamera.near = 0.05;
    _offscreenCamera.far = 200;
    _offscreenCamera.updateProjectionMatrix();

    const world = ModelPrep.worldPoseFromProjection(proj, cameraParams.mount_height_m);
    _offscreenCamera.position.set(0, world.camY, 0);
    _offscreenCamera.lookAt(0, world.camY, -1);

    const dims = {
      width_m: proj.object_width_m,
      height_m: proj.object_height_m,
      depth_m: proj.object_depth_m || proj.object_width_m,
    };
    const orientation = proj.orientation || 'upright';

    if (_offscreenMeshRoot) _offscreenMeshRoot.clear();

    const cacheKey = ModelPrep.templateCacheKey(objectId, dims, orientation, objectPreset);
    const template = _fittedTemplateCache.get(cacheKey);
    if (template) {
      _offscreenMeshRoot.add(ModelPrep.placeInstance(template, world, objectPreset));
      _offscreenRenderer.render(_offscreenScene, _offscreenCamera);
      ctx.drawImage(_offscreenCanvas, 0, 0);
      return;
    }

    _lastArgs = { ctx, objectId, cameraParams, proj, objectPreset };
    _getOrPrepareTemplate(objectId, dims, orientation, objectPreset).then((prepared) => {
      if (!_lastArgs || _lastArgs.objectId !== objectId || !prepared || !_offscreenMeshRoot) return;
      _offscreenMeshRoot.clear();
      const w = ModelPrep.worldPoseFromProjection(_lastArgs.proj, _lastArgs.cameraParams.mount_height_m);
      _offscreenMeshRoot.add(ModelPrep.placeInstance(prepared, w, _lastArgs.objectPreset));
      _offscreenRenderer.render(_offscreenScene, _offscreenCamera);
      _lastArgs.ctx.drawImage(_offscreenCanvas, 0, 0);
    });
  }

  function draw(result, objectId, cvThreshold, cameraParams, objectPreset) {
    const c = canvas();
    if (!c) return;

    if (cameraParams) setResolution(cameraParams.resolution_w, cameraParams.resolution_h);

    const ctx = c.getContext('2d');
    const W = c.width;
    const H = c.height;

    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#1a2430');
    grad.addColorStop(1, '#121a22');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = '#3a4652';
    ctx.lineWidth = 1;
    const gridStepX = Math.max(60, Math.round(W / 16));
    const gridStepY = Math.max(60, Math.round(H / 16));
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

    ctx.strokeStyle = '#484f58';
    ctx.lineWidth = 2;
    ctx.strokeRect(1, 1, W - 2, H - 2);

    ctx.strokeStyle = 'rgba(88,166,255,0.35)';
    ctx.setLineDash([12, 8]);
    ctx.strokeRect(W * 0.05, H * 0.05, W * 0.9, H * 0.9);
    ctx.setLineDash([]);

    ctx.strokeStyle = 'rgba(88,166,255,0.5)';
    ctx.beginPath();
    ctx.moveTo(W / 2, 0);
    ctx.lineTo(W / 2, H);
    ctx.moveTo(0, H / 2);
    ctx.lineTo(W, H / 2);
    ctx.stroke();

    if (!result || !result.projection) {
      ctx.fillStyle = '#8b949e';
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

    if (cameraParams && proj.object_width_m && proj.object_height_m) {
      _renderObjectSnapshot(ctx, objectId || proj.object_id, cameraParams, proj, objectPreset);
    }

    ctx.strokeStyle = pass ? '#3fb950' : '#f85149';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(bx, by, pw, ph);
    ctx.setLineDash([]);

    ctx.fillStyle = '#e6edf3';
    ctx.font = `bold ${Math.max(12, Math.min(20, Math.max(ph, 16) * 0.12))}px system-ui`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(proj.label || proj.object_id, cx2d, by + ph + 10);

    const tag = `${Math.round(pw)} × ${Math.round(ph)} px`;
    const tagY = by - 14 > 28 ? by - 14 : by + ph + 22;
    ctx.font = 'bold 20px system-ui';
    const tw = ctx.measureText(tag).width;
    ctx.fillStyle = pass ? 'rgba(35,134,54,0.9)' : 'rgba(218,54,51,0.9)';
    ctx.fillRect(cx2d - tw / 2 - 8, tagY - 16, tw + 16, 24);
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(tag, cx2d, tagY - 4);
  }

  function isBlank() {
    const c = canvas();
    if (!c) return true;
    const ctx = c.getContext('2d');
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    for (let i = 0; i < d.length; i += 4) {
      if (d[i] !== 13 || d[i + 1] !== 17 || d[i + 2] !== 23) return false;
    }
    return true;
  }

  return { draw, isBlank, canvas, setResolution };
})();
