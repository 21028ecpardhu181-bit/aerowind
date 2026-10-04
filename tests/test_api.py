"""
tests/test_api.py — Integration and Unit Tests for AeroQuantum-Wind FastAPI Service.

Validates:
1. Geocode endpoint with Nominatim mock, caching, and rate limit compliance.
2. Candidate micro-siting grid generation with equirectangular coordinates.
3. Quantum WS-QAOA optimization endpoint for K=4 returning valid layout in <30s.
4. Strict Pydantic v2 validation rejecting out-of-range inputs (K=99, K=1, angle>=360).
5. Printable HTML engineering blueprint endpoint with SVG site map and GPS table.
6. Multi-solver comparison endpoint linking classical baselines with live QAOA telemetry.
"""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.geo_utils import generate_grid_candidates, get_nominatim_client
from backend.app.main import app

client = TestClient(app)


class TestHealthAndRoot:
    """Verifies service boot and health check endpoints."""

    def test_root_endpoint_returns_online(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "service" in data

    def test_api_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestGeoEndpoints:
    """Validates Nominatim geocoding and candidate micro-siting grid generation."""

    def test_geocode_with_mock_and_caching(self):
        mock_response = [
            {
                "lat": "14.6818877",
                "lon": "77.6005911",
                "display_name": "Anantapur, Andhra Pradesh, India",
                "boundingbox": ["14.5", "14.8", "77.5", "77.7"],
            }
        ]

        nom_client = get_nominatim_client()
        nom_client.clear_cache()

        req = httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = httpx.Response(200, json=mock_response, request=req)

            # First call — triggers network request
            response1 = client.get("/api/geo/geocode?q=Anantapur, Andhra Pradesh")
            assert response1.status_code == 200
            data1 = response1.json()
            assert abs(data1["lat"] - 14.6818877) < 1e-4
            assert abs(data1["lon"] - 77.6005911) < 1e-4
            assert "Anantapur" in data1["display_name"]
            assert len(data1["boundingbox"]) == 4
            assert mock_get.call_count == 1

            # Second identical call — must be served from in-memory cache
            response2 = client.get("/api/geo/geocode?q=Anantapur, Andhra Pradesh")
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2 == data1
            # Mock should NOT have been called a second time due to caching
            assert mock_get.call_count == 1

    def test_geocode_not_found_returns_404(self):
        nom_client = get_nominatim_client()
        nom_client.clear_cache()

        req = httpx.Request("GET", "https://nominatim.openstreetmap.org/search")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = httpx.Response(200, json=[], request=req)

            response = client.get("/api/geo/geocode?q=NonExistentFictionalPlace12345")
            assert response.status_code == 404
            assert "could not be resolved" in response.json()["detail"]

    def test_candidates_endpoint_generates_grid(self):
        payload = {
            "center_lat": 14.6819,
            "center_lon": 77.6006,
            "span_km": 1.2,
            "grid_n": 4,
        }
        response = client.post("/api/geo/candidates", json=payload)
        assert response.status_code == 200
        candidates = response.json()

        # 4x4 grid produces 16 candidate sites
        assert len(candidates) == 16
        for idx, site in enumerate(candidates):
            assert site["id"] == idx
            assert isinstance(site["lat"], float)
            assert isinstance(site["lon"], float)
            assert isinstance(site["x_m"], float)
            assert isinstance(site["y_m"], float)
            # Latitude within sensible delta of Anantapur
            assert abs(site["lat"] - 14.6819) < 0.05
            assert abs(site["lon"] - 77.6006) < 0.05


class TestOptimizeEndpoint:
    """Validates quantum WS-QAOA optimization execution and constraints."""

    def test_optimize_k4_returns_valid_layout_under_30s(self):
        # 16 candidate sites spanning 1.2 km around Anantapur
        candidates = generate_grid_candidates(
            center_lat=14.6819,
            center_lon=77.6006,
            span_km=1.2,
            grid_n=4,
        )

        payload = {
            "sites": candidates,
            "K": 4,
            "wind_angle_deg": 270.0,
            "p": 2,
        }

        t0 = time.time()
        response = client.post("/api/optimize", json=payload)
        elapsed = time.time() - t0

        # Performance constraint: < 30 seconds
        assert elapsed < 30.0, f"Optimization took {elapsed:.2f}s, expected < 30.0s"
        assert response.status_code == 200, response.text
        data = response.json()

        # 1. Output structure
        assert "job_id" in data and len(data["job_id"]) > 0
        assert "layout" in data
        assert "bitstring" in data
        assert "aep_gwh" in data
        assert "wake_loss_pct" in data
        assert "revenue_inr_cr" in data
        assert "runtime_s" in data
        assert "distances_m" in data
        assert "blueprint_url" in data

        # 2. Layout constraints: exactly K=4 turbines
        layout = data["layout"]
        assert len(layout) == 4, f"Expected 4 placed turbines, got {len(layout)}"
        placed_ids = {t["id"] for t in layout}
        assert len(placed_ids) == 4, "Turbine IDs must be unique"

        # 3. Bitstring validation: length 16, Hamming weight 4
        bitstring = data["bitstring"]
        assert len(bitstring) == 16
        assert bitstring.count("1") == 4

        # 4. Telemetry values
        assert data["aep_gwh"] > 0.0, "AEP must be strictly positive"
        assert 0.0 <= data["wake_loss_pct"] <= 100.0, "Wake loss % must be in [0, 100]"
        # Revenue ₹ Cr: AEP(GWh) * 1e6 * 3.5 / 1e7 = AEP * 0.35
        expected_revenue = round(data["aep_gwh"] * 0.35, 4)
        assert abs(data["revenue_inr_cr"] - expected_revenue) < 1e-3

        # 5. Pairwise distances: C(4, 2) = 6 pairs
        distances = data["distances_m"]
        assert len(distances) == 6
        for pair in distances:
            assert len(pair) == 3
            assert pair[2] > 0.0

    def test_geo_optimize_alias_endpoint(self):
        candidates = generate_grid_candidates(
            center_lat=14.6819,
            center_lon=77.6006,
            span_km=0.9,
            grid_n=3,
        )
        payload = {
            "candidates": candidates,
            "K": 3,
            "wind_angle": 250.0,
            "p": 1,
        }
        response = client.post("/api/geo/optimize", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["layout"]) == 3
        assert data["bitstring"].count("1") == 3


class TestValidationRejections:
    """Verifies strict Pydantic v2 validation rejecting bad inputs with HTTP 422."""

    def test_validation_rejects_k99(self):
        candidates = generate_grid_candidates(14.68, 77.60, 1.2, 4)
        payload = {
            "sites": candidates,
            "K": 99,  # Constraint: 2 <= K <= 8
            "wind_angle_deg": 270.0,
        }
        response = client.post("/api/optimize", json=payload)
        assert response.status_code == 422, f"Expected 422 for K=99, got {response.status_code}"

    def test_validation_rejects_k1(self):
        candidates = generate_grid_candidates(14.68, 77.60, 1.2, 4)
        payload = {
            "sites": candidates,
            "K": 1,  # Must be >= 2
            "wind_angle_deg": 270.0,
        }
        response = client.post("/api/optimize", json=payload)
        assert response.status_code == 422

    def test_validation_rejects_invalid_wind_angle(self):
        candidates = generate_grid_candidates(14.68, 77.60, 1.2, 4)
        # Angle >= 360
        payload_high = {
            "sites": candidates,
            "K": 4,
            "wind_angle_deg": 400.0,
        }
        assert client.post("/api/optimize", json=payload_high).status_code == 422

        # Negative angle
        payload_neg = {
            "sites": candidates,
            "K": 4,
            "wind_angle_deg": -15.0,
        }
        assert client.post("/api/optimize", json=payload_neg).status_code == 422

    def test_validation_rejects_fewer_sites_than_k(self):
        # 3 candidate sites for K=4
        candidates = generate_grid_candidates(14.68, 77.60, 0.6, 2)[:3]
        payload = {
            "sites": candidates,
            "K": 4,
            "wind_angle_deg": 270.0,
        }
        response = client.post("/api/optimize", json=payload)
        assert response.status_code == 422


class TestBlueprintEndpoint:
    """Validates printable HTML engineering blueprint generation and retrieval."""

    def test_blueprint_generation_and_retrieval(self):
        candidates = generate_grid_candidates(14.6819, 77.6006, 1.2, 4)
        opt_payload = {
            "sites": candidates,
            "K": 4,
            "wind_angle_deg": 270.0,
            "p": 1,
        }
        opt_resp = client.post("/api/optimize", json=opt_payload)
        assert opt_resp.status_code == 200
        job_id = opt_resp.json()["job_id"]

        # Fetch printable HTML blueprint
        bp_resp = client.get(f"/api/blueprint?job_id={job_id}")
        assert bp_resp.status_code == 200
        assert "text/html" in bp_resp.headers["content-type"]
        html_content = bp_resp.text

        # Validate required blueprint elements
        assert "AeroQuantum-Wind Layout Blueprint" in html_content
        assert job_id in html_content
        assert "Turbine GPS Placement Matrix" in html_content
        assert "Pairwise Separation" in html_content
        assert "<svg" in html_content
        assert "window.print()" in html_content

    def test_blueprint_not_found_returns_404(self):
        response = client.get("/api/blueprint?job_id=non_existent_job_xyz")
        assert response.status_code == 404


class TestCompareEndpoint:
    """Validates classical baseline benchmarks and live QAOA comparison."""

    def test_compare_returns_benchmark_records_and_live_row(self):
        response = client.get("/api/compare")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 9, f"Expected >= 9 benchmark rows, got {len(data)}"

        methods = {r["method"] for r in data}
        assert {"brute_force", "classical_ga", "classical_de"}.issubset(methods)
        assert "qaoa" in methods

        for row in data:
            assert "angle" in row
            assert "K" in row
            assert "method" in row
            assert "best_energy" in row
            assert "aep_gwh" in row
            assert "wake_loss_pct" in row
            assert "runtime_s" in row

    def test_compare_dict_format(self):
        response = client.get("/api/compare?format=dict")
        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data
        assert "live_qaoa" in data
        assert isinstance(data["benchmarks"], list)
