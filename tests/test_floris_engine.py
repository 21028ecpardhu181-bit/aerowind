"""
tests/test_floris_engine.py
Automated Verification Suite for NREL FLORIS Wake Modelling & Turbine Aerodynamics.
"""

import pytest
import math
import numpy as np

from backend.app.engineering.floris_engine import (
    FlorisWakeEngine,
    TURBINE_CATALOG,
    interpolate_turbine_power_and_ct,
)


def test_turbine_catalog_integrity():
    """Verify all 5 reference turbines have valid physical parameters and curves."""
    expected_keys = ["ge_25_120", "vestas_v110_20", "nrel_5mw", "iea_15mw", "sg_34_132"]
    for key in expected_keys:
        assert key in TURBINE_CATALOG, f"Missing turbine {key}"
        turb = TURBINE_CATALOG[key]
        assert turb["rotor_diameter_m"] > 50.0
        assert turb["hub_height_m"] > 50.0
        assert turb["rated_power_kw"] >= 2000.0
        assert turb["cut_in_mps"] < turb["rated_mps"] < turb["cut_out_mps"]
        assert len(turb["curves"]) >= 10


def test_power_and_ct_interpolation():
    """Verify cut-in, below-rated, rated, and cut-out behaviors."""
    # NREL 5-MW Reference Turbine
    p_cut_in_below, ct_cut_in_below = interpolate_turbine_power_and_ct("nrel_5mw", 2.0)
    assert p_cut_in_below == 0.0

    p_rated, ct_rated = interpolate_turbine_power_and_ct("nrel_5mw", 12.0)
    assert p_rated == 5000.0
    assert 0.2 <= ct_rated <= 0.5

    p_cut_out, _ = interpolate_turbine_power_and_ct("nrel_5mw", 26.0)
    assert p_cut_out == 0.0


def test_bastankhah_gaussian_wake_deficit():
    """Verify Bastankhah Gaussian deficit decays downwind and radially."""
    engine = FlorisWakeEngine("ge_25_120")
    
    # Direct centerline downwind at 5D (600m) and 10D (1200m)
    def_5d = engine.calculate_gaussian_wake_deficit(downwind_x_m=600.0, crosswind_r_m=0.0, ct=0.8)
    def_10d = engine.calculate_gaussian_wake_deficit(downwind_x_m=1200.0, crosswind_r_m=0.0, ct=0.8)

    assert 0.15 < def_5d < 0.40, f"Expected 5D deficit ~0.25-0.35, got {def_5d}"
    assert def_10d < def_5d, "Wake deficit must recover (decay) further downwind"

    # Radial decay
    def_radial = engine.calculate_gaussian_wake_deficit(downwind_x_m=600.0, crosswind_r_m=80.0, ct=0.8)
    assert def_radial < def_5d, "Wake deficit must decay radially off-center"


def test_floris_farm_wake_simulation():
    """Verify farm wake simulation for a 3-turbine inline array."""
    engine = FlorisWakeEngine("ge_25_120")
    coords = [(0.0, 0.0), (600.0, 0.0), (1200.0, 0.0)]
    
    # Wind blowing directly from West (270 deg) along the line
    res = engine.simulate_farm_wake(coords, wind_speed_mps=8.5, wind_direction_deg=270.0)
    
    speeds = res["effective_speeds"]
    deficits = res["wake_deficits_pct"]
    powers = res["powers_kw"]

    assert speeds[0] == 8.5, "Upstream turbine must see undisturbed freestream wind"
    assert deficits[0] == 0.0, "Upstream turbine must have zero wake deficit"
    assert speeds[1] < speeds[0], "Second turbine must experience velocity deficit"
    assert speeds[2] < speeds[0], "Third turbine must experience velocity deficit"
    assert res["instant_wake_loss_pct"] > 0.0, "Farm wake loss must be positive"


def test_aep_integration_weibull():
    """Verify AEP calculation integrates properly over Weibull wind distribution."""
    engine = FlorisWakeEngine("ge_25_120")
    coords = [(0.0, 0.0), (600.0, 0.0), (0.0, 600.0), (600.0, 600.0)]

    aep = engine.compute_annual_energy_production(coords, weibull_a=8.5, weibull_k=2.2)

    assert aep["gross_aep_gwh"] > 0.0
    assert aep["net_aep_gwh"] > 0.0
    assert aep["gross_aep_gwh"] >= aep["net_aep_gwh"], "Gross AEP must be >= Net AEP"
    assert 0.0 <= aep["wake_loss_pct"] <= 30.0, "Wake loss percentage should be realistic (0-30%)"


def test_qubo_wake_penalty_matrix():
    """Verify QUBO penalty matrix is symmetric with zero diagonal."""
    engine = FlorisWakeEngine("nrel_5mw")
    candidates = [(0.0, 0.0), (650.0, 0.0), (1300.0, 0.0), (0.0, 650.0)]

    Q = engine.build_qubo_wake_penalty_matrix(candidates, wind_speed_mps=9.0, wind_direction_deg=270.0)

    assert Q.shape == (4, 4)
    assert np.all(np.diag(Q) == 0.0), "Diagonal of QUBO wake matrix must be zero"
    assert np.allclose(Q, Q.T), "QUBO wake matrix must be symmetric"
