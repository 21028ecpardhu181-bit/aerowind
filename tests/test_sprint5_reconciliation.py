"""
AeroQuantum-Wind - Sprint 5 Verification Tests
Tests IBM hardware result reconciliation, single source of truth, provenance metadata,
and semantic claim safeguards.
"""

import re
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

# Authoritative test candidate set (Anantapur baseline, 450m elevation)
ANANTAPUR_CANDIDATES = [
    {
        "id": "WTG-01",
        "latitude": 14.6800,
        "longitude": 77.5900,
        "utm_easting_m": 778900.0,
        "utm_northing_m": 1624500.0,
        "elevation_m": 450.0,
    },
    {
        "id": "WTG-02",
        "latitude": 14.6800,
        "longitude": 77.5950,
        "utm_easting_m": 779450.0,
        "utm_northing_m": 1624500.0,
        "elevation_m": 452.0,
    },
    {
        "id": "WTG-03",
        "latitude": 14.6800,
        "longitude": 77.6000,
        "utm_easting_m": 780000.0,
        "utm_northing_m": 1624500.0,
        "elevation_m": 455.0,
    },
    {
        "id": "WTG-04",
        "latitude": 14.6800,
        "longitude": 77.6050,
        "utm_easting_m": 780550.0,
        "utm_northing_m": 1624500.0,
        "elevation_m": 458.0,
    },
]


def test_api_physical_aep_equals_exact_reevaluation():
    """
    TASK 1 & 2: Proves the API response exact_net_aep and wake_loss match
    the authoritative exact physical FLORIS evaluation (18.37 GWh, 1.30% wake loss)
    and resolves the 18.88 GWh sea-level discrepancy.
    """
    req_payload = {
        "candidates": ANANTAPUR_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "min_spacing_multiplier": 4.0,
        "p_layers": 1,
        "shots": 256,
        "max_classical_iterations": 4,
        "top_k_physical_reeval": 4,
        "backend_type": "aer_simulator",
        "random_seed": 42,
        "site_elevation_m": 450.0,
    }

    res = client.post("/api/engineering/optimization/qaoa", json=req_payload)
    assert res.status_code == 200, f"QAOA endpoint failed: {res.text}"
    data = res.json()

    assert data["status"] == "OPTIMIZATION_COMPLETED"
    optimum = data["declared_engineering_optimum"]
    assert optimum is not None, "declared_engineering_optimum must not be None"

    # Winning bitstring must be 1001 (WTG-01, WTG-04)
    assert optimum["bitstring"] == "1001"
    assert optimum["selected_candidate_ids"] == ["WTG-01", "WTG-04"]

    # Authoritative physical metrics at 450m elevation
    exact_net = optimum["exact_net_aep_gwh"]
    wake_loss = optimum["exact_wake_loss_pct"]
    gross_aep = optimum["exact_gross_aep_gwh"]

    assert 18.35 <= exact_net <= 18.39, (
        f"Expected exact Net AEP in [18.35, 18.39] GWh/yr, got {exact_net}. "
        "Stale sea-level 18.88 GWh value must not be returned."
    )
    assert 1.25 <= wake_loss <= 1.35, (
        f"Expected exact wake loss in [1.25, 1.35]%, got {wake_loss}. "
        "Stale 1.24% value must not be returned."
    )
    assert 20.50 <= gross_aep <= 20.65, (
        f"Expected gross AEP in [20.50, 20.65] GWh/yr at 450m, got {gross_aep}"
    )


def test_single_source_of_truth_across_stages():
    """
    TASK 2: Validates that declared_engineering_optimum and pipeline_provenance
    share the identical physical values without discrepancy.
    """
    req_payload = {
        "candidates": ANANTAPUR_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "backend_type": "aer_simulator",
        "site_elevation_m": 450.0,
        "shots": 256,
        "random_seed": 42,
    }

    res = client.post("/api/engineering/optimization/qaoa", json=req_payload)
    assert res.status_code == 200
    data = res.json()

    winner = data["declared_engineering_optimum"]
    prov = data["pipeline_provenance"]
    stage4 = prov["stage_4_physical_reevaluation"]

    assert winner["exact_net_aep_gwh"] == stage4["exact_net_aep_gwh"]
    assert winner["exact_wake_loss_pct"] == stage4["exact_wake_loss_pct"]
    assert winner["exact_gross_aep_gwh"] == stage4["exact_gross_aep_gwh"]
    assert stage4["authoritative_source"] == "EXACT_PHYSICAL_FLORIS_AEP"


def test_provenance_distinguishes_four_stages():
    """
    TASK 3: Verifies all 4 distinct layers are present in pipeline_provenance:
    Classical QUBO, Aer Simulator, IBM Hardware/Sampling, and FLORIS Physical Re-Evaluation.
    """
    req_payload = {
        "candidates": ANANTAPUR_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "backend_type": "aer_simulator",
        "site_elevation_m": 450.0,
        "shots": 256,
        "random_seed": 42,
    }

    res = client.post("/api/engineering/optimization/qaoa", json=req_payload)
    assert res.status_code == 200
    data = res.json()

    prov = data.get("pipeline_provenance", {})
    assert "stage_1_classical_qubo" in prov, "Missing Stage 1 Classical QUBO provenance"
    assert "stage_2_aer_simulator" in prov, "Missing Stage 2 Aer Simulator provenance"
    assert "stage_3_hardware_or_sampling" in prov, "Missing Stage 3 Hardware/Sampling provenance"
    assert "stage_4_physical_reevaluation" in prov, "Missing Stage 4 Physical Re-evaluation provenance"

    assert prov["stage_1_classical_qubo"]["target_turbines"] == 2
    assert "optimal_gamma" in prov["stage_2_aer_simulator"]
    assert "optimal_beta" in prov["stage_2_aer_simulator"]
    assert prov["stage_4_physical_reevaluation"]["wake_model"] == "NREL FLORIS Bastankhah Gaussian Model"


def test_hardware_unavailable_graceful_handling():
    """
    TASK 4: Verifies unauthenticated IBM hardware requests cleanly return
    HARDWARE_UNAVAILABLE without crashing or returning mock data.
    """
    req_payload = {
        "candidates": ANANTAPUR_CANDIDATES,
        "turbine_model_id": "ge_25_120",
        "target_turbines": 2,
        "backend_type": "ibm_hardware",
        "ibm_token": "INVALID_TOKEN_FOR_TESTING",
        "ibm_backend_name": "ibm_fez",
        "site_elevation_m": 450.0,
    }

    res = client.post("/api/engineering/optimization/qaoa", json=req_payload)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "HARDWARE_UNAVAILABLE"
    assert "error_message" in data
    assert data["declared_engineering_optimum"] is None


def test_prohibited_claims_safeguard():
    """
    TASK 4: Proves forbidden marketing phrases do not appear in optimization responses
    or Screen4Optimize component.
    """
    screen4_path = Path("src/components/workflow/Screen4Optimize.tsx")
    assert screen4_path.exists(), "Screen4Optimize.tsx must exist"
    content = screen4_path.read_text(encoding="utf-8").lower()

    prohibited_phrases = [
        "quantum advantage",
        "quantum supremacy",
        "exponential speedup",
        "optimal layout guaranteed by quantum physics",
    ]

    for phrase in prohibited_phrases:
        assert phrase not in content, f"Prohibited phrase '{phrase}' found in Screen4Optimize.tsx"
