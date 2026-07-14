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
    const preset = $('cameraPreset').value;
    const z = $('distance').value;
    const obj = selectedObjectId;
    const oz = $('objectDistance').value;
    const q = new URLSearchParams({ preset, z, obj, oz });
    history.replaceState(null, '', `/?${q.toString()}`);
  }

  async function fetchCalculate() {
    const body = readParams();
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('calculate failed');
    return res.json();
  }

  function applyResult(result) {
    lastResult = result;
    $('metricHfov').textContent = `${result.fov.hfov_deg}°`;
    $('metricVfov').textContent = `${result.fov.vfov_deg}°`;
    $('metricDfov').textContent = `${result.fov.dfov_deg}°`;
    $('metricCoverage').textContent = `${result.coverage.width_m} × ${result.coverage.height_m} m`;
    $('metricPpm').textContent = String(result.density.ppm);
    $('metricPpc').textContent = String(result.density.ppc);
    $('metricGsd').textContent = `${result.density.gsd_mm_per_px} mm/px`;

    if (result.projection) {
      const p = result.projection;
      $('metricObjectPx').textContent = `${p.label}: ${p.width_px} × ${p.height_px} px @ ${p.object_distance_m} m`;
      const el = $('metricCvPass');
      el.textContent = p.cv_pass
        ? `✓ ≥ ${p.cv_threshold_px} px (CV OK)`
        : `✗ < ${p.cv_threshold_px} px (CV fail)`;
      el.className = 'cv-pass ' + (p.cv_pass ? 'pass' : 'fail');
    }

    $('doriList').innerHTML = `
      <li class="det" data-help="doriDet" tabindex="0">Detection: ${result.dori.detection_m} m</li>
      <li class="obs" data-help="doriObs" tabindex="0">Observation: ${result.dori.observation_m} m</li>
      <li class="rec" data-help="doriRec" tabindex="0">Recognition: ${result.dori.recognition_m} m</li>
      <li class="id" data-help="doriId" tabindex="0">Identification: ${result.dori.identification_m} m</li>
    `;
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
      0,
      0,
      $('lensType').value,
      selectedObjectId
    );

    $('fisheyeDisclaimer').hidden = $('lensType').value !== 'fisheye_equidistant';
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
    $('lensType').value = e.lens_type;
    if (e.fisheye_fov_deg) $('fisheyeFov').value = e.fisheye_fov_deg;
    Viewport2D.setResolution(e.resolution_w, e.resolution_h);
  }

  function buildObjectTabs() {
    const container = $('objectTabs');
    container.innerHTML = '';
    objects.forEach((o) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'tab' + (o.id === selectedObjectId ? ' active' : '');
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
    ['resW', 'resH', 'focal', 'fisheyeFov', 'mountHeight'].forEach((id) =>
      $(id).addEventListener('input', scheduleRecalc)
    );
    // <select> в браузере шлёт change, не input — иначе FOV/frustum не пересчитываются.
    $('sensorFormat').addEventListener('change', () => {
      updateSensorDimsLabel();
      scheduleRecalc();
    });
    $('lensType').addEventListener('change', scheduleRecalc);
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
    if (q.has('z')) {
      $('distance').value = q.get('z');
      $('distanceVal').textContent = q.get('z');
    }
    if (q.has('obj')) selectedObjectId = q.get('obj');
    if (q.has('oz')) {
      $('objectDistance').value = q.get('oz');
      $('objectDistanceVal').textContent = q.get('oz');
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
    parseUrlState();
    applyCameraPreset($('cameraPreset').value);
    buildObjectTabs();
    bindInputs();
    initTooltips();
    Scene3D.init();
    Viewport2D.setResolution(parseInt($('resW').value, 10), parseInt($('resH').value, 10));
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
  };
})();
