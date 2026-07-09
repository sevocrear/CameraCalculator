/** 2D вид камеры: pinhole-проекция на сенсор resolution_w × resolution_h.
 *
 * Внутренний canvas = размер сенсора в пикселях (1 px кадра = 1 px canvas).
 * CSS масштабирует отображение с сохранением aspect-ratio из resolution W/H.
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
  let _lastArgs = null;
  let _sensorW = 0;
  let _sensorH = 0;

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
  }

  function setResolution(width, height) {
    const c = canvas();
    if (!c) return;
    const w = Math.max(1, Math.round(width));
    const h = Math.max(1, Math.round(height));
    if (w !== _sensorW || h !== _sensorH) {
      _sensorW = w;
      _sensorH = h;
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
      _offscreenScene.add(new THREE.AmbientLight(0xffffff, 0.75));
      const dir = new THREE.DirectionalLight(0xffffff, 0.95);
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

    const doRender = (prepared) => {
      if (!prepared || !_offscreenMeshRoot) return;
      _offscreenMeshRoot.clear();
      const w = ModelPrep.worldPoseFromProjection(proj, cameraParams.mount_height_m);
      _offscreenMeshRoot.add(ModelPrep.placeInstance(prepared, w, objectPreset));
      _offscreenRenderer.render(_offscreenScene, _offscreenCamera);
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

  return { draw, isBlank, canvas, setResolution };
})();
