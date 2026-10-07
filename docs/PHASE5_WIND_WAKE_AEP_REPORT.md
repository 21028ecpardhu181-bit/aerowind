# AeroQuantum-Wind — Phase 5 Engineering Report
## Engineering-Grade Wind Resource, Wake Modeling, Power Curves & Preliminary AEP Engine

### 1. Executive Summary

Phase 5 implements the physical wind-performance and energy yield assessment engine for AeroQuantum-Wind, strictly built on top of the verified Phase 4 candidate generation and Phase 3A regulatory/suitability foundation.

This layer replaces simplified demo energy calculations with an engineering-grade physical simulation pipeline:
1. Long-Term Climatological Wind Resource Ingestion (National Institute of Wind Energy / MNRE Technical Report 19).
2. Hub-Height Extrapolation & International Standard Atmosphere Barometric Air Density.
3. Authoritative Turbine Power P(u) and Thrust Coefficient Ct(u) Curve Evaluation with IEC 61400-12-1 Air Density Normalization.
4. Downwind Wake Propagation via NREL FLORIS Vectorized Bastankhah & Porte-Agel (2014, 2016) Gaussian Deficit Model.
5. Multi-Turbine Quadratic Wake Interaction (Katic et al., 1986 sum-of-squares deficit superposition).
6. 16-Sector Climatological Wind Rose Integration across the Full Operating Speed Regime.
7. IEC 61400-15 Loss Accounting Framework (Gross AEP -> Wake-Adjusted AEP -> Net AEP).
8. Physical Sanity Invariant Guards & Upstream Regulatory Status Propagation.
9. Machine-Readable Performance Contract for Phase 6 QUBO / QAOA Quantum Optimization.

---

### 2. Wind Resource Provenance & Climatology Dataset

#### 2.1 Provider & Dataset Specifications
- Provider: National Institute of Wind Energy (NIWE), Ministry of New and Renewable Energy (MNRE), Government of India.
- Dataset: NIWE 120m Wind Potential Atlas / Technical Report 19 (2024 Revision).
- Calibration Basis: Calibrated and validated across 406 reference wind monitoring masts across India.
- Numerical Model: 500m WRF (Weather Research and Forecasting) mesoscale simulation corridor ingestion.
- Temporal Scope: 15-year climatological reanalysis baseline (1999-2014) dynamically downscaled and calibrated.
- Operational Reference Height: 120 m Above Ground Level (AGL).

#### 2.2 Strict Separation of Climatology vs Live Weather
Live weather telemetry and short-term numerical forecasts (such as Open-Meteo GFS/ECMWF 7-day hourly forecast) are strictly prohibited from substituting for long-term wind resource. Live telemetry represents instantaneous weather, not the 20-year project climatology required for bankable annual energy yield.

#### 2.3 Non-Fabrication Invariant
If a queried coordinate lies outside verified NIWE calibration corridors or if wind resource records are missing, the engine strictly outputs status `UNKNOWN` / `UNAVAILABLE`. No synthetic Weibull distributions, random sinusoidal wind profiles, or fictitious capacity factors are generated.

---

### 3. Vertical Wind Shear & Atmospheric Density

#### 3.1 Hub-Height Shear Extrapolation
The reference wind speed at 120 m AGL is extrapolated to the turbine hub height using the standard IEC neutral atmospheric stability power law:

$$u(z_{\text{hub}}) = u(z_{\text{ref}}) \cdot \left(\frac{z_{\text{hub}}}{z_{\text{ref}}}\right)^\alpha$$

Where:
- $z_{\text{ref}} = 120.0\text{ m}$ (authoritative NIWE measurement height)
- $\alpha = 0.14$ (IEC 61400-1 standard onshore wind shear exponent)
- $z_{\text{hub}}$ is the hub height of the selected turbine model (e.g., 110 m for GE 2.5-120, 95 m for Vestas V110-2.0, 90 m for NREL 5-MW, 150 m for IEA 15-MW).

#### 3.2 Site Elevation & Barometric Air Density
Local dry air density $\rho(z)$ at site ground elevation $z$ (meters above sea level) is calculated using the international standard barometric atmosphere formula:

$$\rho(z) = \rho_0 \cdot \exp\left(-\frac{z}{8434.5}\right)$$

Where:
- $\rho_0 = 1.225\text{ kg/m}^3$ (sea level air density at 15 deg C, 1013.25 hPa)
- Scale height $H_b = 8434.5\text{ m}$
- For the Anantapur site (elevation 347 m ASL), dry air density is $\rho = 1.176\text{ kg/m}^3$.

---

### 4. Authoritative Turbine Catalogue & Power/Thrust Curves

#### 4.1 Turbine Models & Specifications
All aerodynamic calculations use authentic specifications from `TURBINE_CATALOG`:

| Model ID | Commercial Name | Category | Rotor D (m) | Hub H (m) | Rated Power (kW) | Cut-in (m/s) | Rated (m/s) | Cut-out (m/s) |
|---|---|---|---|---|---|---|---|---|
| `ge_25_120` | GE Vernova 2.5-120 | Commercial Onshore | 120.0 | 110.0 | 2500.0 | 3.0 | 11.5 | 25.0 |
| `vestas_v110_20` | Vestas V110-2.0 MW | Commercial Onshore | 110.0 | 95.0 | 2000.0 | 3.0 | 11.5 | 20.0 |
| `sg_34_132` | Siemens Gamesa SG 3.4-132 | Commercial Onshore | 132.0 | 114.0 | 3465.0 | 3.0 | 11.0 | 25.0 |
| `nrel_5mw` | NREL 5-MW Reference | Research Reference | 126.0 | 90.0 | 5000.0 | 3.0 | 11.4 | 25.0 |
| `iea_15mw` | IEA 15-MW Offshore Ref | Research Offshore | 240.0 | 150.0 | 15000.0 | 3.0 | 10.6 | 25.0 |

#### 4.2 Air Density Power Normalization (IEC 61400-12-1)
To account for local air density $\rho \neq 1.225\text{ kg/m}^3$ on pitch-regulated turbines in partial load, wind speed is normalized prior to curve interpolation:

$$u_{\text{norm}} = u \cdot \left(\frac{\rho}{1.225}\right)^{1/3}$$

Physical constraints strictly enforced:
- Electrical power is zero when $u_{\text{norm}} < u_{\text{cut-in}}$ or $u_{\text{norm}} > u_{\text{cut-out}}$.
- Electrical power is strictly clamped: $0.0 \le P(u) \le P_{\text{rated}}$. Generator capacity cannot be exceeded even in high-density cold air.
- Thrust coefficient is bounded: $0.05 \le C_t(u) \le 0.95$.

---

### 5. Vectorized FLORIS Bastankhah Gaussian Wake Engine

#### 5.1 Coordinate Frame & Wind Conventions
The engine strictly abides by the unified geometry conventions established in Phase 4:
- Meteorological Wind Arrival Direction: $\text{wind\_from\_deg} \in [0, 360)$
- Wake Downwind Propagation Azimuth: $\text{wind\_to\_deg} = (\text{wind\_from\_deg} + 180.0) \pmod{360}$
- HAWT Rotor Nacelle Yaw: $\text{yaw\_deg} = \text{wind\_from\_deg} \pmod{360}$ (faces directly upwind into oncoming wind)

Transforming candidate positions into downwind ($x$) and crosswind ($y$) axes:
$$\vec{u}_{\text{downwind}} = (\sin\theta_{\text{to}}, \cos\theta_{\text{to}})$$
$$\vec{v}_{\text{crosswind}} = (\cos\theta_{\text{to}}, -\sin\theta_{\text{to}})$$
Where $\theta_{\text{to}} = \text{radians}(\text{wind\_to\_deg})$.

#### 5.2 Bastankhah & Porte-Agel Gaussian Velocity Deficit
For a downstream turbine at downwind distance $\Delta x > 0$ and crosswind radial distance $r = |\Delta y|$ from an upstream turbine with thrust coefficient $C_t$:

$$\frac{\Delta u(x, r)}{u_\infty} = \left(1 - \sqrt{1 - \frac{C_t}{8 (\sigma(x) / D)^2}}\right) \cdot \exp\left(-\frac{r^2}{2 \sigma(x)^2}\right)$$

Where the wake width standard deviation $\sigma(x)$ expands linearly downwind:
$$\sigma(x) = k^* \cdot \Delta x + \epsilon \cdot D$$
$$k^* = 0.04\text{ (onshore wake expansion parameter)}$$
$$\epsilon = 0.2 \cdot \sqrt{\frac{1 + \sqrt{1 - C_t}}{2 \sqrt{1 - C_t}}}$$

#### 5.3 Quadratic Deficit Superposition
Multi-turbine wake interactions are combined using the Katic et al. (1986) sum-of-squares velocity deficit accumulation:

$$\delta_j = \min\left(0.65, \sqrt{\sum_{i \in \text{upstream}(j)} \delta_{ij}^2}\right)$$
$$u_{\text{eff}, j} = \min(u_\infty, \max(0.0, u_\infty \cdot (1 - \delta_j)))$$

Downstream turbines strictly cannot accelerate beyond freestream (no speed gains).

---

### 6. Climatological Directional Integration & AEP Computation

#### 6.1 Weibull Speed Bins & 16-Sector Wind Rose
Energy production is integrated across the full annual speed regime ($u \in [0.5, 25.5]\text{ m/s}$) with $1.0\text{ m/s}$ discretization and 16 compass sectors ($22.5^\circ$ bins):

$$\text{AEP}_{\text{gross}} = \sum_{d=1}^{16} \sum_{u=0.5}^{25.5} P_{\text{gross}}(u) \cdot 8760 \cdot f_d \cdot f(u; A, k)$$
$$\text{AEP}_{\text{wake-adjusted}} = \sum_{d=1}^{16} \sum_{u=0.5}^{25.5} \sum_{i=1}^N P_i(u_{\text{eff}, i}(u, \theta_d)) \cdot 8760 \cdot f_d \cdot f(u; A, k)$$

$$\text{Wake Loss (\%)} = \frac{\text{AEP}_{\text{gross}} - \text{AEP}_{\text{wake-adjusted}}}{\text{AEP}_{\text{gross}}} \cdot 100\%$$

#### 6.2 IEC 61400-15 Loss Accounting Framework
Non-wake balance-of-plant (BoP) technical losses are modeled explicitly:
- Electrical collection & array substation loss: 2.5%
- Turbine mechanical/electrical availability: 3.0%
- Grid curtailment & transmission outages: 1.5%
- Environmental blade soiling, degradation & icing: 1.5%
- Nacelle yaw misalignment & control hysteresis: 1.5%

$$\eta_{\text{BoP}} = (1 - 0.025) \cdot (1 - 0.030) \cdot (1 - 0.015) \cdot (1 - 0.015) \cdot (1 - 0.015) \approx 0.9038\text{ (9.62\% total BoP loss)}$$

$$\text{AEP}_{\text{net}} = \text{AEP}_{\text{wake-adjusted}} \cdot \eta_{\text{BoP}}$$

---

### 7. Physical Sanity Invariant Guards

The engine enforces strict runtime validation via `validate_aep_physical_sanity`:
1. Theoretical Maximum Ceiling: $\text{AEP}_{\text{gross}} \le \frac{P_{\text{rated, total}} \cdot 8760}{1000}\text{ GWh}$.
2. Yield Monotonicity: $0 \le \text{AEP}_{\text{net}} \le \text{AEP}_{\text{wake-adjusted}} \le \text{AEP}_{\text{gross}}$.
3. Wake Loss Invariant: $\text{Wake Loss} \ge 0.0\%$ (isolated single turbine has identically $0.0\%$).
4. Local Speed Invariant: $u_{\text{eff}, i} \le u_{\text{freestream}}$ for all turbines $i \in [1, N]$.
5. Status Preservation: Propagates upstream `PARTIAL` or `CONDITIONAL` regulatory flags.

---

### 8. Machine-Readable Phase 6 Performance Contract

The engine exports a standardized contract (`/api/engineering/aep/phase6-contract`) for Phase 6 QUBO/QAOA optimization:
- Candidate spatial array with local UTM metric coordinates.
- Individual unwaked energy yields $E_i$ (linear QUBO weights $h_i$).
- Symmetric pairwise wake loss matrix $Q_{ij} = \Delta E_{ij} + \Delta E_{ji}$ (quadratic penalty weights).
- Physical capacity factor bounds and spacing constraints ($d_{ij} \ge k \cdot D$).

---

### 9. Verification & Test Results

#### 9.1 Unit & Integration Test Suite (`tests/test_wind_wake_aep_engine.py`)
All 17 Phase 5 tests pass cleanly in 4.03 seconds:
1. `test_wind_from_to_convention_and_reversal_prevention`: Verified 180 deg reversal and upwind yaw.
2. `test_height_extrapolation_and_shear_scaling`: Verified power-law alpha=0.14 scaling across hub heights (90m, 110m, 150m).
3. `test_power_curve_interpolation_and_bounds`: Verified cut-in, partial load, rated clamping, and cut-out.
4. `test_single_turbine_baseline_zero_wake_loss`: Verified single turbine has exactly 0.0% wake loss and gross == wake-adjusted.
5. `test_two_turbines_downstream_wake_deficit`: Verified downstream turbine experiences velocity deficit > 10%.
6. `test_crosswind_separation_reduces_wake_interaction`: Verified lateral decay in Gaussian wake envelope.
7. `test_downwind_separation_causes_wake_deficit_recovery`: Verified recovery between 4D, 8D, and 12D downwind.
8. `test_direction_reversal_swaps_upstream_and_downstream_roles`: Verified swapping wake victim under 180 deg wind reversal.
9. `test_air_density_normalization`: Verified below-rated power scales with density and caps at rated generator capacity.
10. `test_loss_accounting_breakdown`: Verified electrical, availability, curtailment, environmental, and hysteresis losses.
11. `test_missing_resource_unknown_propagation`: Verified missing wind resource returns UNKNOWN without synthetic values.
12. `test_deterministic_aep_calculations`: Verified zero-entropy deterministic computation on identical inputs.
13. `test_different_turbine_models_produce_different_physical_results`: Verified distinct yields and capacities across turbine models.
14. `test_real_data_sample_anantapur_aep_integration`: Verified end-to-end integration with Anantapur real dataset (feasible candidates -> FLORIS -> Net AEP).
15. `test_engineering_physical_sanity_guards`: Verified rejection of unphysical conditions.
16. `test_phase6_performance_contract`: Verified machine-readable QUBO contract export.
17. `test_fastapi_wind_wake_aep_endpoints`: Verified FastAPI endpoints return 200 OK and valid JSON payloads.

#### 9.2 Full Backend Regression Suite
- Total Tests: 153 passed, 0 failed across all test modules in 20.17 seconds.

#### 9.3 Frontend Production Build
- Command: `npm run build`
- Output: 1,621 modules transformed, TypeScript compilation clean, Vite build clean in 42.27 seconds.
