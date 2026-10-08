"""
core/aerodynamics.py — Vectorized Jensen (Park) Wake Deficit Model.

Implements the Katic-Højstrup-Jensen analytical aerodynamic wake model
for wind farm micro-siting and layout optimization.
Reference:
- Jensen, N. O. (1983). A note on wind generator interaction. Risø-M-2411.
- Katic, I., Højstrup, J., & Jensen, N. O. (1986). A simple model for cluster efficiency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import numpy as np


def wake_deficit(
    x: Union[float, np.ndarray],
    D: float = 120.0,
    Ct: float = 0.8,
    k: float = 0.075,
) -> Union[float, np.ndarray]:
    """
    Computes normalized velocity deficit Δv / v0 via the Jensen (Park) model.

    Formula:
        Δv / v0 = (1 - sqrt(1 - Ct)) / (1 + 2 * k * x / D)^2   for x > 0
        Δv / v0 = 0.0                                          for x <= 0

    Parameters:
        x: Downwind distance in meters (scalar float or numpy array).
        D: Turbine rotor diameter in meters (default: 120.0 m).
        Ct: Thrust coefficient of the turbine (default: 0.8).
        k: Empirical wake decay constant (default: 0.075, onshore standard).

    Returns:
        Fractional velocity deficit Δv / v0 (dimensionless, scalar or ndarray).
    """
    if D <= 0:
        raise ValueError(f"Rotor diameter D must be positive, got {D}")
    if Ct < 0 or Ct >= 1.0:
        raise ValueError(f"Thrust coefficient Ct must be in [0, 1.0), got {Ct}")
    if k <= 0:
        raise ValueError(f"Wake decay constant k must be positive, got {k}")

    is_scalar = np.isscalar(x)
    x_arr = np.asarray(x, dtype=np.float64)

    numerator = 1.0 - np.sqrt(1.0 - Ct)
    # Use positive distance for denominator to safely prevent division by zero
    # when x <= -D / (2 * k) during vectorized evaluation
    x_pos = np.maximum(0.0, x_arr)
    denominator = (1.0 + 2.0 * k * x_pos / D) ** 2

    # Only downstream points (x > 0) experience a wake deficit
    deficit = np.where(x_arr > 0.0, numerator / denominator, 0.0)

    if is_scalar:
        return float(deficit.item())
    return deficit


def wind_direction_vector(
    wind_angle_deg: float,
    angle_convention: str = "compass",
) -> np.ndarray:
    """
    Computes the 2D unit vector indicating the direction wind is flowing towards.

    Parameters:
        wind_angle_deg: Prevailing wind angle in degrees.
        angle_convention:
            - 'compass': Meteorological convention (0° North, 90° East, 180° South, 270° West).
                         Wind FROM angle θ blows TOWARDS (θ + 180°).
            - 'cartesian': Standard math polar angle (0° = +x, 90° = +y).

    Returns:
        np.ndarray: [u_x, u_y] unit vector.
    """
    rad = np.radians(wind_angle_deg)
    if angle_convention == "compass":
        # Wind blowing FROM wind_angle_deg travels towards (wind_angle_deg + 180°)
        # North (0°) blows towards South (0, -1)
        # East (90°) blows towards West (-1, 0)
        # South (180°) blows towards North (0, 1)
        # West (270°) blows towards East (1, 0)
        u_x = -np.sin(rad)
        u_y = -np.cos(rad)
    elif angle_convention in ("cartesian", "polar"):
        u_x = np.cos(rad)
        u_y = np.sin(rad)
    else:
        raise ValueError(
            f"Unknown angle_convention: {angle_convention}. Use 'compass' or 'cartesian'."
        )

    norm = np.hypot(u_x, u_y)
    if norm < 1e-12:
        return np.array([1.0, 0.0], dtype=np.float64)
    return np.array([u_x / norm, u_y / norm], dtype=np.float64)


def pairwise_wake_matrix(
    coords: np.ndarray,
    wind_angle_deg: float,
    D: float = 120.0,
    Ct: float = 0.8,
    k: float = 0.075,
    cutoff_m: float = 600.0,
    angle_convention: str = "compass",
    use_wake_cone: bool = True,
) -> np.ndarray:
    """
    Computes the N×N velocity deficit interaction matrix W_ij.

    W_ij is the velocity deficit Δv / v0 inflicted by upstream turbine i on
    downstream turbine j. If j is not downwind of i, or lies outside the
    cutoff distance or conical wake zone, W_ij = 0.

    Parameters:
        coords: (N, 2) array of turbine coordinates [x, y] in meters.
        wind_angle_deg: Prevailing wind direction in degrees.
        D: Rotor diameter in meters (default: 120.0 m).
        Ct: Thrust coefficient (default: 0.8).
        k: Wake decay constant (default: 0.075).
        cutoff_m: Maximum downwind / Euclidean interaction cutoff distance in meters (5D = 600m).
        angle_convention: 'compass' (default) or 'cartesian'.
        use_wake_cone: If True, checks that turbine j lies inside the expanding conical
                       wake zone R_wake(x) = D/2 + k*x. If False, projects purely along wind vector.

    Returns:
        np.ndarray: N×N matrix W of velocity deficits.
    """
    coords_arr = np.asarray(coords, dtype=np.float64)
    if coords_arr.ndim != 2 or coords_arr.shape[1] != 2:
        raise ValueError(f"coords must have shape (N, 2), got {coords_arr.shape}")

    n_turbines = coords_arr.shape[0]
    if n_turbines == 0:
        return np.zeros((0, 0), dtype=np.float64)

    # Unit vector in the direction of wind flow
    u = wind_direction_vector(wind_angle_deg, angle_convention=angle_convention)

    # Pairwise displacement vectors: diff[i, j] = coords[j] - coords[i] (vector from i to j)
    # diff has shape (N, N, 2)
    diff = coords_arr[None, :, :] - coords_arr[:, None, :]

    # Project displacement onto wind vector to get downwind distance x_downwind
    # x_downwind > 0 means turbine j is downwind of turbine i
    x_proj = diff[..., 0] * u[0] + diff[..., 1] * u[1]

    # Euclidean distance
    dist = np.linalg.norm(diff, axis=-1)

    # Crosswind distance: y_cross = sqrt(dist^2 - x_proj^2)
    y_cross_sq = np.maximum(0.0, dist**2 - x_proj**2)
    y_cross = np.sqrt(y_cross_sq)

    # Conical wake expansion: R_wake(x) = D/2 + k * x
    r_wake = (D / 2.0) + k * np.maximum(0.0, x_proj)

    # Base velocity deficit
    deficit = wake_deficit(x_proj, D=D, Ct=Ct, k=k)

    # Selection mask:
    # 1. Must be downwind (x_proj > 0)
    # 2. Must be within spatial cutoff distance (x_proj <= cutoff_m)
    mask = (x_proj > 0.0) & (x_proj <= cutoff_m)

    if use_wake_cone:
        # Crosswind distance must lie inside wake radius
        mask = mask & (y_cross <= r_wake)

    W = np.where(mask, deficit, 0.0)

    # Turbine does not wake itself
    np.fill_diagonal(W, 0.0)

    return W


def load_wind_rose_fixture(fixture_path: Optional[Union[str, Path]] = None) -> dict:
    """
    Loads and returns the Anantapur 16-bin wind rose fixture.
    """
    if fixture_path is None:
        fixture_path = (
            Path(__file__).resolve().parent.parent / "data" / "anantapur_wind_rose_16bin.json"
        )
    path = Path(fixture_path)
    if not path.is_file():
        raise FileNotFoundError(f"Wind rose fixture not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_candidate_grid(
    n_rows: int = 4,
    n_cols: int = 4,
    spacing_m: float = 300.0,
    origin: tuple[float, float] = (0.0, 0.0),
) -> np.ndarray:
    """
    Generates an (N, 2) candidate coordinate grid for wind turbine micro-siting.

    Parameters:
        n_rows: Number of grid rows (default: 4).
        n_cols: Number of grid columns (default: 4).
        spacing_m: Grid spacing in meters between candidate sites (default: 300.0 m).
        origin: (x0, y0) origin coordinate in meters.

    Returns:
        np.ndarray: Shape (n_rows * n_cols, 2) array of coordinates.
    """
    xs = np.arange(n_cols, dtype=np.float64) * spacing_m + origin[0]
    ys = np.arange(n_rows, dtype=np.float64) * spacing_m + origin[1]
    xx, yy = np.meshgrid(xs, ys)
    return np.column_stack([xx.ravel(), yy.ravel()])
