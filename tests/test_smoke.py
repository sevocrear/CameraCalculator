"""Smoke tests for service startup and static assets."""

import httpx
import pytest


def test_health_returns_ok(httpx_client: httpx.Client):
    r = httpx_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["checks"]["static_index"] is True
    assert data["checks"]["presets_loaded"] is True


def test_index_html_served(httpx_client: httpx.Client):
    r = httpx_client.get("/")
    assert r.status_code == 200
    assert "id=\"app\"" in r.text
    assert "sensorFormat" in r.text
    assert "app.js" in r.text
    assert "OrbitControls" in r.text


def test_static_assets(httpx_client: httpx.Client):
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
        r = httpx_client.get(path)
        assert r.status_code == 200, path


def test_models_static(httpx_client: httpx.Client):
    # Models are optional, but if present they must be served.
    r = httpx_client.get("/models/README.md")
    assert r.status_code == 200


def test_openapi_available(httpx_client: httpx.Client):
    r = httpx_client.get("/docs")
    assert r.status_code == 200


def test_presets_endpoints(httpx_client: httpx.Client):
    for path in (
        "/api/presets/sensors",
        "/api/presets/cameras",
        "/api/presets/objects",
        "/api/presets/cv_thresholds",
    ):
        r = httpx_client.get(path)
        assert r.status_code == 200, path
        data = r.json()
        assert data, f"empty response for {path}"

    sensors = httpx_client.get("/api/presets/sensors").json()
    assert len(sensors) >= 15
    first = sensors[0]
    assert "aspect" in first
    assert "diagonal_mm" in first
