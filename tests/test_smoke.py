"""Smoke tests for service startup and static assets."""


def test_health_returns_ok(asgi_client):
    r = asgi_client.get("/health")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    data = r.json()
    assert data["status"] == "ok"
    assert data["checks"]["static_index"] is True
    assert data["checks"]["presets_loaded"] is True


def test_index_html_served(asgi_client):
    r = asgi_client.get("/")
    assert r.status_code == 200
    assert 'id="app"' in r.text
    assert "sensorFormat" in r.text
    assert "app.js" in r.text
    assert "OrbitControls" in r.text
    assert 'href="/models/README.md"' in r.text


def test_static_assets(asgi_client):
    for path in (
        "/static/js/app.js",
        "/static/js/scene3d.js",
        "/static/js/viewport2d.js",
        "/static/js/model_prep.js",
        "/static/js/help.js",
        "/static/js/three.min.js",
        "/static/js/OrbitControls.js",
        "/static/js/GLTFLoader.js",
    ):
        r = asgi_client.get(path)
        assert r.status_code == 200, path


def test_models_static(asgi_client):
    # Models are optional, but if present they must be served.
    r = asgi_client.get("/models/README.md")
    assert r.status_code == 200
    assert "CC BY" in r.text


def test_openapi_available(asgi_client):
    r = asgi_client.get("/docs")
    assert r.status_code == 200


def test_presets_endpoints(asgi_client):
    for path in (
        "/api/presets/sensors",
        "/api/presets/cameras",
        "/api/presets/objects",
        "/api/presets/cv_thresholds",
    ):
        r = asgi_client.get(path)
        assert r.status_code == 200, path
        data = r.json()
        assert data, f"empty response for {path}"

    sensors = asgi_client.get("/api/presets/sensors").json()
    assert len(sensors) >= 15
    first = sensors[0]
    assert "aspect" in first
    assert "diagonal_mm" in first
