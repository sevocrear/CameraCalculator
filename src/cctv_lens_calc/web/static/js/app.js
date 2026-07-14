/** Main app — form state, API calls, URL share, UI updates. */

(function () {
  const DEBOUNCE_MS = 50;
  let cameras = [];
  let sensors = [];
  let objects = [];
  let cvThresholds = {};
  let selectedObjectId = 'cola_can';
  let lastResult = null;
  let debounceTimer = null;
  let viewMode = '3d';

  const $ = (id) => document.getElementById(id);

  function getSelectedSensor() {
    const id = $('sensorFormat').value;
    return sensors.find((s) => s.id === id) || null;
  }

  function updateSensorDimsLabel() {
    const s = getSelectedSensor();
    const el = $('sensorDimsMm');
    if (!el) return;
    if (!s) {
      el.textContent = '—';
      return;
    }
    el.textContent = `${s.width_mm} × ${s.height_mm} mm`;
  }

  function syncLensSegment() {
    const value = $('lensType').value;
    document.querySelectorAll('#lensSegment .segment-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.lens === value);
    });
    const fisheye = value === 'fisheye_equidistant';
    const fovField = $('fisheyeFovField');
    if (fovField) fovField.hidden = !fisheye;
    $('fisheyeDisclaimer').hidden = !fisheye;
    $('focal').disabled = fisheye;
    if ($('focalSlider')) $('focalSlider').disabled = fisheye;
    if (fisheye) syncFisheyeFocal();
  }

  function syncFisheyeFocal() {
    if ($('lensType').value !== 'fisheye_equidistant') return;
    const sensor = getSelectedSensor();
    const fovDeg = parseFloat($('fisheyeFov').value);
    if (!sensor || !Number.isFinite(fovDeg) || fovDeg <= 0) return;
    const halfAngleRad = (fovDeg * Math.PI) / 360.0;
    const effectiveFocal = (sensor.width_mm / 2.0) / halfAngleRad;
    $('focal').value = effectiveFocal.toFixed(3);
    if ($('focalSlider')) $('focalSlider').value = effectiveFocal;
  }

  function setLensType(value) {
    $('lensType').value = value;
    syncLensSegment();
    $('lensType').dispatchEvent(new Event('change', { bubbles: true }));
  }

  function setViewMode(mode) {
    viewMode = mode === '2d' ? '2d' : '3d';
    const v3 = $('viewport3d');
    const v2 = $('viewport2dWrap');
    if (v3) v3.hidden = viewMode !== '3d';
    if (v2) v2.hidden = viewMode !== '2d';
    document.querySelectorAll('.view-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === viewMode);
    });
    if (viewMode === '3d' && window.Scene3D && Scene3D.resize) {
      requestAnimationFrame(() => Scene3D.resize());
    }
  }

  function updateDoriBar(dori) {
    const bar = $('doriBar');
    if (!bar || !dori) return;
    const available = [
      dori.detection_m,
      dori.observation_m,
      dori.recognition_m,
      dori.identification_m,
    ].some((value) => value !== null);
    bar.hidden = !available;
    if (!available) return;
    const vals = [
      Math.max(dori.detection_m || 0, 0.01),
      Math.max(dori.observation_m || 0, 0.01),
      Math.max(dori.recognition_m || 0, 0.01),
      Math.max(dori.identification_m || 0, 0.01),
    ];
    const segs = bar.querySelectorAll('.dori-seg');
    segs.forEach((seg, i) => {
      seg.style.flex = String(vals[i]);
    });
  }

  function formatMetric(value, suffix = '') {
    return value === null || value === undefined ? 'N/A' : `${value}${suffix}`;
  }

  function renderDoriList(dori) {
    const list = $('doriList');
    list.replaceChildren();
    const entries = [
      ['det', 'doriDet', 'Detection', dori.detection_m],
      ['obs', 'doriObs', 'Observation', dori.observation_m],
      ['rec', 'doriRec', 'Recognition', dori.recognition_m],
      ['id', 'doriId', 'Identification', dori.identification_m],
    ];
    entries.forEach(([className, helpKey, label, value]) => {
      const item = document.createElement('li');
      item.className = className;
      item.dataset.help = helpKey;
      item.tabIndex = 0;
      item.textContent = `${label}: ${formatMetric(value, ' m')}`;
      list.appendChild(item);
    });
  }

  function showWarnings(warnings) {
    const element = $('metricWarnings');
    const messages = Array.isArray(warnings) ? warnings : [];
    element.hidden = messages.length === 0;
    element.textContent = messages.join(' ');
  }

  function readParams() {
    const sensorId = $('sensorFormat').value;
    const sensor = getSelectedSensor();
    return {
      camera: {
        sensor_format_id: sensorId,
        sensor_width_mm: sensor ? sensor.width_mm : undefined,
        sensor_height_mm: sensor ? sensor.height_mm : undefined,
        resolution_w: parseInt($('resW').value, 10),
        resolution_h: parseInt($('resH').value, 10),
        focal_length_mm: parseFloat($('focal').value),
        lens_type: $('lensType').value,
        fisheye_fov_deg:
          $('lensType').value === 'fisheye_equidistant'
            ? parseFloat($('fisheyeFov').value)
            : null,
        distance_m: parseFloat($('distance').value),
        mount_height_m: parseFloat($('mountHeight').value),
      },
      object: {
        object_id: selectedObjectId,
        object_distance_m: parseFloat($('objectDistance').value),
      },
    };
  }

  function updateShareUrl() {
    const q = new URLSearchParams({
      preset: $('cameraPreset').value,
      sensor: $('sensorFormat').value,
      rw: $('resW').value,
      rh: $('resH').value,
      focal: $('focal').value,
      lens: $('lensType').value,
      ffov: $('fisheyeFov').value,
      z: $('distance').value,
      mh: $('mountHeight').value,
      obj: selectedObjectId,
      oz: $('objectDistance').value,
    });
    history.replaceState(null, '', `/?${q.toString()}`);
  }

  async function fetchCalculate() {
    const body = readParams();
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => null);
      throw new Error(error && error.detail ? JSON.stringify(error.detail) : 'Calculation failed');
    }
    return res.json();
  }

  function applyResult(result) {
    lastResult = result;
    $('metricHfov').textContent = `${result.fov.hfov_deg}°`;
    $('metricVfov').textContent = `${result.fov.vfov_deg}°`;
    $('metricDfov').textContent = `${result.fov.dfov_deg}°`;
    $('metricCoverage').textContent =
      `${formatMetric(result.coverage.width_m)} × ${formatMetric(result.coverage.height_m)} m`;
    $('metricPpm').textContent = formatMetric(result.density.ppm);
    $('metricPpc').textContent = formatMetric(result.density.ppc);
    $('metricGsd').textContent = formatMetric(result.density.gsd_mm_per_px, ' mm/px');

    if (result.projection) {
      const p = result.projection;
      $('metricObjectPx').textContent = `${p.label}: ${p.width_px} × ${p.height_px} px @ ${p.object_distance_m} m`;
      const el = $('metricCvPass');
      el.textContent = p.cv_pass
        ? `✓ ≥ ${p.cv_threshold_px} px (CV OK)`
        : `✗ < ${p.cv_threshold_px} px (CV fail)`;
      el.className = 'cv-pass ' + (p.cv_pass ? 'pass' : 'fail');
    }

    renderDoriList(result.dori);
    updateDoriBar(result.dori);
    const warnings = [...(result.warnings || [])];
    if (result.coverage.width_m === null) {
      warnings.push('The finite 3D frustum is a display-only fallback and is not to scale.');
    }
    showWarnings(warnings);
    initTooltips();

    const obj = objects.find((o) => o.id === selectedObjectId);
    const cvTh = obj ? obj.cv_threshold_px : cvThresholds.embedder_min_px || 64;
    const camParams = readParams().camera;
    Viewport2D.draw(result, selectedObjectId, cvTh, camParams, obj);

    const mountH = parseFloat($('mountHeight').value);
    const objDist = parseFloat($('objectDistance').value);
    Scene3D.update(
      result,
      mountH,
      obj,
      objDist,
      $('lensType').value,
      selectedObjectId
    );

    syncLensSegment();
  }

  function scheduleRecalc() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        updateShareUrl();
        const result = await fetchCalculate();
        applyResult(result);
      } catch (e) {
        console.error(e);
        showWarnings([e.message || 'Calculation failed']);
      }
    }, DEBOUNCE_MS);
  }

  function applyCameraPreset(presetId) {
    const cam = cameras.find((c) => c.id === presetId);
    if (!cam || !cam.expanded) return;
    const e = cam.expanded;
    if (e.sensor_format_id) $('sensorFormat').value = e.sensor_format_id;
    updateSensorDimsLabel();
    $('resW').value = e.resolution_w;
    $('resH').value = e.resolution_h;
    $('focal').value = e.focal_length_mm;
    if ($('focalSlider')) $('focalSlider').value = e.focal_length_mm;
    $('lensType').value = e.lens_type;
    syncLensSegment();
    if (e.fisheye_fov_deg) $('fisheyeFov').value = e.fisheye_fov_deg;
    Viewport2D.setResolution(e.resolution_w, e.resolution_h);
  }

  function buildObjectTabs() {
    const container = $('objectTabs');
    container.innerHTML = '';
    objects.forEach((o) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className =
        'tab tab--' + o.id + (o.id === selectedObjectId ? ' active' : '');
      btn.textContent = o.label;
      btn.dataset.id = o.id;
      btn.addEventListener('click', () => {
        selectedObjectId = o.id;
        document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
        btn.classList.add('active');
        scheduleRecalc();
      });
      container.appendChild(btn);
    });
  }

  function buildSensorSelect() {
    const sel = $('sensorFormat');
    sel.innerHTML = '';
    sensors.forEach((s) => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.label;
      sel.appendChild(opt);
    });
    if (sensors.length > 0) {
      const defaultId = sensors.find((s) => s.id === '1_2_8_inch')
        ? '1_2_8_inch'
        : sensors[0].id;
      sel.value = defaultId;
    }
    updateSensorDimsLabel();
  }

  function bindInputs() {
    ['resW', 'resH', 'focal'].forEach((id) =>
      $(id).addEventListener('input', scheduleRecalc)
    );
    $('fisheyeFov').addEventListener('input', () => {
      syncFisheyeFocal();
      scheduleRecalc();
    });
    $('focal').addEventListener('input', () => {
      if ($('focalSlider')) $('focalSlider').value = $('focal').value;
    });
    if ($('focalSlider')) {
      $('focalSlider').addEventListener('input', () => {
        $('focal').value = $('focalSlider').value;
        scheduleRecalc();
      });
    }
    $('mountHeight').addEventListener('input', () => {
      if ($('mountHeightVal')) $('mountHeightVal').textContent = $('mountHeight').value;
      scheduleRecalc();
    });
    $('sensorFormat').addEventListener('change', () => {
      updateSensorDimsLabel();
      syncFisheyeFocal();
      scheduleRecalc();
    });
    $('lensType').addEventListener('change', () => {
      syncLensSegment();
      scheduleRecalc();
    });
    document.querySelectorAll('#lensSegment .segment-btn').forEach((btn) => {
      btn.addEventListener('click', () => setLensType(btn.dataset.lens));
    });
    document.querySelectorAll('.view-btn').forEach((btn) => {
      btn.addEventListener('click', () => setViewMode(btn.dataset.view));
    });
    $('resW').addEventListener('input', () => {
      Viewport2D.setResolution(
        parseInt($('resW').value, 10),
        parseInt($('resH').value, 10)
      );
    });
    $('resH').addEventListener('input', () => {
      Viewport2D.setResolution(
        parseInt($('resW').value, 10),
        parseInt($('resH').value, 10)
      );
    });
    $('distance').addEventListener('input', () => {
      $('distanceVal').textContent = $('distance').value;
      scheduleRecalc();
    });
    $('objectDistance').addEventListener('input', () => {
      $('objectDistanceVal').textContent = $('objectDistance').value;
      scheduleRecalc();
    });
    $('cameraPreset').addEventListener('change', () => {
      applyCameraPreset($('cameraPreset').value);
      scheduleRecalc();
    });
  }

  function parseUrlState() {
    const q = new URLSearchParams(window.location.search);
    if (q.has('preset')) $('cameraPreset').value = q.get('preset');
    if (q.has('obj')) selectedObjectId = q.get('obj');
    return q;
  }

  function applyUrlOverrides(q) {
    const directValues = {
      sensor: 'sensorFormat',
      rw: 'resW',
      rh: 'resH',
      focal: 'focal',
      lens: 'lensType',
      ffov: 'fisheyeFov',
      z: 'distance',
      mh: 'mountHeight',
      oz: 'objectDistance',
    };
    Object.entries(directValues).forEach(([queryKey, elementId]) => {
      if (q.has(queryKey)) $(elementId).value = q.get(queryKey);
    });
    if ($('focalSlider')) $('focalSlider').value = $('focal').value;
    $('distanceVal').textContent = $('distance').value;
    $('mountHeightVal').textContent = $('mountHeight').value;
    $('objectDistanceVal').textContent = $('objectDistance').value;
    syncLensSegment();
    if ($('lensType').value === 'fisheye_equidistant') {
      syncFisheyeFocal();
    }
  }

  async function init() {
    const [camRes, sensorRes, objRes, cvRes] = await Promise.all([
      fetch('/api/presets/cameras'),
      fetch('/api/presets/sensors'),
      fetch('/api/presets/objects'),
      fetch('/api/presets/cv_thresholds'),
    ]);
    cameras = await camRes.json();
    sensors = await sensorRes.json();
    objects = await objRes.json();
    cvThresholds = await cvRes.json();

    const sel = $('cameraPreset');
    cameras.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.label;
      sel.appendChild(opt);
    });

    buildSensorSelect();
    const query = parseUrlState();
    applyCameraPreset($('cameraPreset').value);
    applyUrlOverrides(query);
    buildObjectTabs();
    bindInputs();
    syncLensSegment();
    setViewMode('3d');
    initTooltips();
    Scene3D.init();
    Viewport2D.setResolution(parseInt($('resW').value, 10), parseInt($('resH').value, 10));
    if ($('focalSlider')) $('focalSlider').value = $('focal').value;
    if ($('mountHeightVal')) $('mountHeightVal').textContent = $('mountHeight').value;
    scheduleRecalc();
  }

  document.addEventListener('DOMContentLoaded', init);

  window.CctvLensApp = {
    readParams,
    fetchCalculate,
    getLastResult: () => lastResult,
    getMetricPpm: () => ($('metricPpm') ? $('metricPpm').textContent : null),
    getSensors: () => sensors,
    getSelectedSensor,
    setViewMode,
    getViewMode: () => viewMode,
  };
})();
