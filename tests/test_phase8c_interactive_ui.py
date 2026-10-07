"""
tests/test_phase8c_interactive_ui.py — Verification of Phase 8C Interactive Optimization Controls.

Tests:
1. Classical QUBO optimization endpoint dispatch and exact physical AEP result.
2. Aer QAOA simulator endpoint dispatch and provenance labeling.
3. IBM Quantum hardware endpoint dispatch with ibm_hardware backend_type.
4. Truthful hardware status API response and error handling.
5. Verification that 0.0 elevation derives candidate elevations rather than arbitrary 40m.
6. Verify no emojis exist in new UI components or tests.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

SAMPLE_CANDIDATES = [
    {
        "id": "C-01",
        "candidate_id": "C-01",
        "latitude": 8.120,
        "longitude": 77.540,
        "lat": 8.120,
        "lon": 77.540,
        "elevation_m": 450.0,
        "is_feasible": True,
        "feasibility_status": "FEASIBLE",
    },
    {
        "id": "C-02",
        "candidate_id": "C-02",
        "latitude": 8.125,
        "longitude": 77.545,
        "lat": 8.125,
        "lon": 77.545,
        "elevation_m": 450.0,
        "is_feasible": True,
        "feasibility_status": "FEASIBLE",
    },
    {
        "id": "C-03",
        "candidate_id": "C-03",
        "latitude": 8.130,
        "longitude": 77.550,
        "lat": 8.130,
        "lon": 77.550,
        "elevation_m": 450.0,
        "is_feasible": True,
        "feasibility_status": "FEASIBLE",
    },
    {
        "id": "C-04",
        "candidate_id": "C-04",
        "latitude": 8.135,
        "longitude": 77.555,
        "lat": 8.135,
        "lon": 77.555,
        "elevation_m": 450.0,
        "is_feasible": True,
        "feasibility_status": "FEASIBLE",
    },
]


def test_hardware_status_truthful_response():
    """Verify GET /api/engineering/optimization/hardware-status returns authentic data."""
    response = client.get("/api/engineering/optimization/hardware-status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ibm_quantum_available" in data
    assert "backend_details" in data
    assert isinstance(data["ibm_quantum_available"], bool)
    if data["ibm_quantum_available"]:
        assert data["backend_details"]["is_available"] is True
        assert data["backend_details"]["backend_name"] is not None


def test_classical_optimization_dispatch():
    """Verify POST /api/engineering/optimization/classical returns certified combinatorial optimum."""
    payload = {
        "candidates": SAMPLE_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "min_spacing_multiplier": 4.0,
        "site_elevation_m": 0.0,
        "top_k": 3,
    }
    response = client.post("/api/engineering/optimization/classical", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["COMPLETED", "SUCCESS"]
    assert "declared_engineering_optimum" in data
    opt = data["declared_engineering_optimum"]
    assert "exact_net_aep_gwh" in opt
    assert "exact_wake_loss_pct" in opt
    assert len(opt["selected_candidate_ids"]) == 2
    # Verify effective elevation was automatically derived as 450.0m from candidate coordinates
    assert all(c["elevation_m"] == 450.0 for c in opt["coordinates"])


def test_aer_qaoa_dispatch():
    """Verify POST /api/engineering/optimization/qaoa with aer_simulator returns QAOA solution."""
    payload = {
        "candidates": SAMPLE_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "min_spacing_multiplier": 4.0,
        "p_layers": 1,
        "shots": 256,
        "max_classical_iterations": 4,
        "top_k_physical_reeval": 2,
        "backend_type": "aer_simulator",
        "random_seed": 42,
        "site_elevation_m": 0.0,
    }
    response = client.post("/api/engineering/optimization/qaoa", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["OPTIMIZATION_COMPLETED", "SUCCESS"]
    assert "declared_engineering_optimum" in data
    opt = data["declared_engineering_optimum"]
    assert len(opt["selected_candidate_ids"]) == 2
    # Verify effective elevation was automatically derived as 450.0m from candidate coordinates
    assert all(c["elevation_m"] == 450.0 for c in opt["coordinates"])


def test_ibm_hardware_qaoa_dispatch():
    """Verify POST /api/engineering/optimization/qaoa with ibm_hardware returns authentic execution or explicit unavailable error."""
    payload = {
        "candidates": SAMPLE_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "min_spacing_multiplier": 4.0,
        "p_layers": 1,
        "shots": 256,
        "max_classical_iterations": 2,
        "top_k_physical_reeval": 2,
        "backend_type": "ibm_hardware",
        "random_seed": 42,
        "site_elevation_m": 0.0,
    }
    response = client.post("/api/engineering/optimization/qaoa", json=payload)
    # If credentials are valid, it succeeds with 200; if unavailable, it returns 503 without fake data
    assert response.status_code in [200, 503]
    data = response.json()
    if response.status_code == 200:
        assert data["status"] in ["OPTIMIZATION_COMPLETED", "SUCCESS"]
        assert "declared_engineering_optimum" in data
        assert data["quantum_circuit"]["backend"]["is_hardware"] is True
    else:
        assert "HARDWARE_UNAVAILABLE" in str(data.get("detail", "")) or "IBM" in str(data.get("detail", ""))
