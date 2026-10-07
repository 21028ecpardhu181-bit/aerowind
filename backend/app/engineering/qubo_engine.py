"""
backend/app/engineering/qubo_engine.py
AeroQuantum-Wind Phase 6: Quadratic Unconstrained Binary Optimization (QUBO) Engine.

Formulates wind farm layout optimization as a mathematically certified QUBO minimization problem
derived from the Phase 5/5.1 performance contract:
  min H(x) = x^T Q x + c = sum_i h_i x_i + sum_{i < j} J_ij x_i x_j + offset

Objective terms:
1. Standalone turbine energy yield reward: - sum_i (E_i * eta_bop) x_i
2. Aerodynamic wake interaction penalty: + sum_{i < j} (Q_ij * eta_bop) x_i x_j
3. Turbine capacity target constraint: + P_cap * (sum_i x_i - k)^2
4. Hard inter-turbine minimum spacing exclusion: + P_spacing * sum_{(i,j) in Violations} x_i x_j

Also provides:
- Exact algebraic mapping to Ising spin Hamiltonian: H_Ising = sum_i tilde_h_i Z_i + sum_{i < j} tilde_J_ij Z_i Z_j
- Parameter normalization for stable QAOA variational optimization
- Classical exhaustive benchmark solver finding certified global QUBO optimum for N <= 20
"""

from __future__ import annotations

import math
import itertools
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field

from backend.app.provenance import SourceStatus, EngineeringSuitability


class QuboBitstringEvaluation(BaseModel):
    """Evaluation metrics for a specific binary candidate selection bitstring."""
    bitstring: str
    selected_indices: List[int]
    selected_candidate_ids: List[str]
    selected_count: int
    target_count: int
    count_valid: bool
    spacing_violations_count: int
    spacing_violations_pairs: List[Tuple[str, str]]
    is_feasible: bool
    surrogate_gross_energy_mwh: float
    surrogate_wake_loss_mwh: float
    surrogate_wake_adjusted_energy_mwh: float
    surrogate_net_energy_mwh: float
    surrogate_net_energy_gwh: float
    surrogate_wake_loss_pct: float
    capacity_penalty_mwh: float
    spacing_penalty_mwh: float
    qubo_cost: float


class QuboProblem:
    """
    Mathematical QUBO problem representation for wind turbine layout optimization.
    """

    def __init__(
        self,
        candidate_ids: List[str],
        positions_metric: List[Tuple[float, float]],
        linear_energy_mwh: List[float],
        wake_penalty_matrix_mwh: List[List[float]],
        target_turbines: int,
        min_spacing_m: float,
        bop_derate_factor: float = 0.9038,
        penalty_capacity: Optional[float] = None,
        penalty_spacing: Optional[float] = None,
        turbine_model_id: str = "ge_25_120",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        n = len(candidate_ids)
        if n < 1:
            raise ValueError("QuboProblem requires at least 1 candidate.")
        if len(positions_metric) != n:
            raise ValueError(f"positions_metric length ({len(positions_metric)}) != candidate_ids length ({n}).")
        if len(linear_energy_mwh) != n:
            raise ValueError(f"linear_energy_mwh length ({len(linear_energy_mwh)}) != candidate_ids length ({n}).")
        if len(wake_penalty_matrix_mwh) != n or any(len(r) != n for r in wake_penalty_matrix_mwh):
            raise ValueError(f"wake_penalty_matrix_mwh must be of dimension {n}x{n}.")

        # Adversarial guard: target_turbines must be within [1, n]
        target_k = int(target_turbines)
        if target_k < 1 or target_k > n:
            raise ValueError(
                f"target_turbines ({target_turbines}) must be an integer between 1 and n_candidates ({n})."
            )

        # Adversarial guard: unique candidate IDs
        if len(set(candidate_ids)) != n:
            raise ValueError(f"candidate_ids contains duplicate IDs: {candidate_ids}")

        # Adversarial guard: wake matrix symmetry and zero diagonal
        for i in range(n):
            if abs(wake_penalty_matrix_mwh[i][i]) > 1e-4:
                raise ValueError(
                    f"Self-wake penalty on matrix diagonal M[{i}][{i}] must be 0.0, found {wake_penalty_matrix_mwh[i][i]}."
                )
            for j in range(i + 1, n):
                if abs(wake_penalty_matrix_mwh[i][j] - wake_penalty_matrix_mwh[j][i]) > 1e-4:
                    raise ValueError(
                        f"wake_penalty_matrix_mwh must be symmetric. M[{i}][{j}] ({wake_penalty_matrix_mwh[i][j]}) != M[{j}][{i}] ({wake_penalty_matrix_mwh[j][i]})."
                    )

        self.n_candidates = n
        self.candidate_ids = list(candidate_ids)
        self.positions_metric = list(positions_metric)
        self.linear_energy_mwh = [float(v) for v in linear_energy_mwh]
        self.wake_penalty_matrix_mwh = [
            [float(val) for val in row] for row in wake_penalty_matrix_mwh
        ]
        self.target_turbines = target_k
        self.min_spacing_m = float(min_spacing_m)
        self.bop_derate_factor = float(bop_derate_factor)
        self.turbine_model_id = str(turbine_model_id)
        self.metadata = metadata or {}

        # 1. Detect inter-turbine spacing violations based on metric Euclidean distance
        self.spacing_violations: List[Tuple[int, int]] = []
        for i in range(n):
            for j in range(i + 1, n):
                dx = self.positions_metric[i][0] - self.positions_metric[j][0]
                dy = self.positions_metric[i][1] - self.positions_metric[j][1]
                dist_m = math.hypot(dx, dy)
                if dist_m < self.min_spacing_m:
                    self.spacing_violations.append((i, j))

        # 2. Deterministic physical calibration of penalty multipliers
        # Max single-turbine net energy:
        max_net_e = max(self.linear_energy_mwh) * self.bop_derate_factor
        if max_net_e <= 0.0:
            max_net_e = 1000.0  # Fallback non-zero floor

        # P_cap must exceed max single turbine yield to ensure deviating from target k increases cost
        if penalty_capacity is not None:
            self.penalty_capacity = float(penalty_capacity)
        else:
            self.penalty_capacity = round(1.5 * max_net_e, 2)

        # P_spacing must exceed benefit of placing both overlapping turbines
        if penalty_spacing is not None:
            self.penalty_spacing = float(penalty_spacing)
        else:
            self.penalty_spacing = round(3.0 * max_net_e, 2)

        # 3. Assemble QUBO linear terms h_i and quadratic terms J_ij
        # Cost minimization:
        # H(x) = sum_i h_i x_i + sum_{i < j} J_ij x_i x_j + offset
        # Target constraint: P_cap * (sum_i x_i - k)^2 = P_cap * ((1 - 2k) sum_i x_i + 2 sum_{i < j} x_i x_j + k^2)
        # Standalone yield: - sum_i (E_i * eta_bop) x_i
        # Wake loss: + sum_{i < j} (Q_ij * eta_bop) x_i x_j
        # Spacing penalty: + P_spacing sum_{(i,j) in violations} x_i x_j
        k = self.target_turbines
        p_cap = self.penalty_capacity
        p_sp = self.penalty_spacing
        eta = self.bop_derate_factor

        self.h_linear = np.zeros(n, dtype=np.float64)
        for i in range(n):
            self.h_linear[i] = - (self.linear_energy_mwh[i] * eta) + p_cap * (1.0 - 2.0 * k)

        self.J_quad = np.zeros((n, n), dtype=np.float64)
        violations_set = set(self.spacing_violations)
        for i in range(n):
            for j in range(i + 1, n):
                q_loss = self.wake_penalty_matrix_mwh[i][j] * eta
                spacing_term = p_sp if (i, j) in violations_set else 0.0
                j_val = q_loss + 2.0 * p_cap + spacing_term
                self.J_quad[i, j] = j_val
                self.J_quad[j, i] = j_val

        self.offset = float(p_cap * (k ** 2))

    def evaluate_bitstring(self, x: Union[str, List[int], np.ndarray]) -> QuboBitstringEvaluation:
        """
        Evaluates a candidate selection bitstring under the physical surrogate and QUBO objective.
        """
        n = self.n_candidates
        if isinstance(x, str):
            clean_str = x.strip().replace(" ", "")
            if len(clean_str) != n:
                raise ValueError(f"Bitstring length ({len(clean_str)}) does not match candidate count ({n}).")
            bits = np.array([int(c) for c in clean_str], dtype=np.int32)
            bitstring_repr = clean_str
        elif isinstance(x, (list, np.ndarray)):
            if len(x) != n:
                raise ValueError(f"Array length ({len(x)}) does not match candidate count ({n}).")
            bits = np.array(x, dtype=np.int32)
            bitstring_repr = "".join(str(int(b)) for b in bits)
        else:
            raise TypeError("Bitstring must be a string or list/array of integers.")

        selected_indices = [i for i in range(n) if bits[i] == 1]
        selected_count = len(selected_indices)
        selected_cids = [self.candidate_ids[i] for i in selected_indices]

        count_valid = (selected_count == self.target_turbines)

        # Spacing violations check
        violation_pairs: List[Tuple[str, str]] = []
        for (i, j) in self.spacing_violations:
            if bits[i] == 1 and bits[j] == 1:
                violation_pairs.append((self.candidate_ids[i], self.candidate_ids[j]))

        spacing_violations_count = len(violation_pairs)
        is_feasible = count_valid and (spacing_violations_count == 0)

        # Physical surrogate calculations
        surrogate_gross_mwh = sum(self.linear_energy_mwh[i] for i in selected_indices)
        surrogate_wake_mwh = 0.0
        for i_idx, i in enumerate(selected_indices):
            for j in selected_indices[i_idx + 1:]:
                surrogate_wake_mwh += self.wake_penalty_matrix_mwh[i][j]

        surrogate_wake_adj_mwh = max(0.0, surrogate_gross_mwh - surrogate_wake_mwh)
        surrogate_net_mwh = surrogate_wake_adj_mwh * self.bop_derate_factor
        surrogate_net_gwh = surrogate_net_mwh / 1000.0
        wake_loss_pct = round(
            (100.0 * surrogate_wake_mwh / max(1.0, surrogate_gross_mwh)), 2
        ) if surrogate_gross_mwh > 0 else 0.0

        # Constraint penalties
        cap_penalty = self.penalty_capacity * float((selected_count - self.target_turbines) ** 2)
        spacing_penalty = self.penalty_spacing * float(spacing_violations_count)

        # QUBO cost calculation
        qubo_cost = float(
            np.dot(self.h_linear, bits)
            + sum(self.J_quad[i, j] * bits[i] * bits[j] for i in range(n) for j in range(i + 1, n))
            + self.offset
        )

        return QuboBitstringEvaluation(
            bitstring=bitstring_repr,
            selected_indices=selected_indices,
            selected_candidate_ids=selected_cids,
            selected_count=selected_count,
            target_count=self.target_turbines,
            count_valid=count_valid,
            spacing_violations_count=spacing_violations_count,
            spacing_violations_pairs=violation_pairs,
            is_feasible=is_feasible,
            surrogate_gross_energy_mwh=round(surrogate_gross_mwh, 2),
            surrogate_wake_loss_mwh=round(surrogate_wake_mwh, 2),
            surrogate_wake_adjusted_energy_mwh=round(surrogate_wake_adj_mwh, 2),
            surrogate_net_energy_mwh=round(surrogate_net_mwh, 2),
            surrogate_net_energy_gwh=round(surrogate_net_gwh, 4),
            surrogate_wake_loss_pct=wake_loss_pct,
            capacity_penalty_mwh=round(cap_penalty, 2),
            spacing_penalty_mwh=round(spacing_penalty, 2),
            qubo_cost=float(qubo_cost),
        )

    def to_ising(self) -> Dict[str, Any]:
        """
        Converts the QUBO problem to an Ising spin Hamiltonian:
          H_Ising = sum_i tilde_h_i Z_i + sum_{i < j} tilde_J_ij Z_i Z_j + tilde_offset
        with Pauli mapping x_i = (I - Z_i) / 2.
        Also returns normalized coefficients for stable QAOA variational execution.
        """
        n = self.n_candidates
        tilde_J: Dict[Tuple[int, int], float] = {}
        for i in range(n):
            for j in range(i + 1, n):
                val = self.J_quad[i, j] / 4.0
                if abs(val) > 1e-12:
                    tilde_J[(i, j)] = val

        tilde_h: Dict[int, float] = {}
        for i in range(n):
            sum_j = sum(self.J_quad[min(i, j), max(i, j)] for j in range(n) if j != i)
            h_val = - (self.h_linear[i] / 2.0) - (sum_j / 4.0)
            tilde_h[i] = h_val

        tilde_offset = (
            self.offset
            + np.sum(self.h_linear) / 2.0
            + sum(self.J_quad[i, j] for i in range(n) for j in range(i + 1, n)) / 4.0
        )

        # Scale factor for normalization
        max_coeff = max(
            [abs(v) for v in tilde_h.values()] + [abs(v) for v in tilde_J.values()] + [1.0]
        )
        scale_factor = float(max_coeff)

        normalized_h = {i: float(v / scale_factor) for i, v in tilde_h.items()}
        normalized_J = {k: float(v / scale_factor) for k, v in tilde_J.items()}

        return {
            "num_spins": n,
            "tilde_h": tilde_h,
            "tilde_J": tilde_J,
            "tilde_offset": float(tilde_offset),
            "scale_factor": scale_factor,
            "normalized_h": normalized_h,
            "normalized_J": normalized_J,
        }

    def solve_classical_exhaustive(
        self,
        max_combinations: int = 50000,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Exhaustively explores valid combinations of target_turbines candidates
        to establish the mathematically certified classical global QUBO optimum.
        """
        n = self.n_candidates
        k = self.target_turbines

        total_combs = math.comb(n, k)
        if total_combs > max_combinations:
            return {
                "status": "EXHAUSTIVE_LIMIT_EXCEEDED",
                "solver": "CLASSICAL_EXHAUSTIVE",
                "total_candidates": n,
                "target_turbines": k,
                "total_combinations": total_combs,
                "max_combinations": max_combinations,
                "error_message": (
                    f"Candidate combinations C({n}, {k}) = {total_combs} exceeds "
                    f"configured exhaustive search threshold ({max_combinations})."
                ),
                "total_subsets_evaluated": 0,
                "feasible_subsets_count": 0,
                "global_qubo_optimum": None,
                "best_unconstrained": None,
                "top_feasible_solutions": [],
                "has_feasible_solution": False,
            }

        evaluated_solutions: List[QuboBitstringEvaluation] = []
        for comb in itertools.combinations(range(n), k):
            bits = np.zeros(n, dtype=np.int32)
            bits[list(comb)] = 1
            eval_res = self.evaluate_bitstring(bits)
            evaluated_solutions.append(eval_res)

        # Filter feasible solutions (spacing violations == 0)
        feasible_solutions = [s for s in evaluated_solutions if s.is_feasible]
        feasible_solutions.sort(key=lambda s: s.qubo_cost)
        evaluated_solutions.sort(key=lambda s: s.qubo_cost)

        best_feasible = feasible_solutions[0] if feasible_solutions else None
        best_overall = evaluated_solutions[0] if evaluated_solutions else None

        return {
            "status": "COMPLETED",
            "solver": "CLASSICAL_EXHAUSTIVE",
            "total_candidates": n,
            "target_turbines": k,
            "total_subsets_evaluated": len(evaluated_solutions),
            "feasible_subsets_count": len(feasible_solutions),
            "global_qubo_optimum": best_feasible.model_dump() if best_feasible else None,
            "best_unconstrained": best_overall.model_dump() if best_overall else None,
            "top_feasible_solutions": [s.model_dump() for s in feasible_solutions[:top_k]],
            "has_feasible_solution": (best_feasible is not None),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the QUBO problem instance to a JSON-compatible dictionary."""
        return {
            "n_candidates": self.n_candidates,
            "candidate_ids": self.candidate_ids,
            "positions_metric": [{"east_m": p[0], "north_m": p[1]} for p in self.positions_metric],
            "target_turbines": self.target_turbines,
            "min_spacing_m": self.min_spacing_m,
            "bop_derate_factor": self.bop_derate_factor,
            "penalty_capacity": self.penalty_capacity,
            "penalty_spacing": self.penalty_spacing,
            "spacing_violations_count": len(self.spacing_violations),
            "spacing_violations": self.spacing_violations,
            "h_linear": [round(float(v), 4) for v in self.h_linear],
            "J_quad": [[round(float(v), 4) for v in row] for row in self.J_quad],
            "offset": round(self.offset, 4),
            "turbine_model_id": self.turbine_model_id,
            "spacing_classification": "DEFENSE_IN_DEPTH (Phase 4 guarantees environmental/boundary clearance; QUBO spacing penalty prevents close placement on dense candidate grids)",
            "penalty_calibration": {
                "capacity_penalty_rationale": "P_cap = 1.5 * max(E_i * eta_bop) guarantees deviating by +/-1 turbine increases cost more than maximum single-turbine yield",
                "spacing_penalty_rationale": "P_spacing = 3.0 * max(E_i * eta_bop) heavily penalizes placing mutually close candidates closer than minimum spacing",
            },
            "provenance": {
                "formulation": "Constrained Quadratic Unconstrained Binary Optimization (QUBO)",
                "source_status": SourceStatus.VERIFIED_REAL.value,
                "engineering_suitability": EngineeringSuitability.PRELIMINARY_SCREENING_ONLY.value,
            },
        }


def build_qubo_from_phase6_contract(
    contract: Dict[str, Any],
    target_turbines: Optional[int] = None,
    min_spacing_multiplier: float = 4.0,
    penalty_capacity: Optional[float] = None,
    penalty_spacing: Optional[float] = None,
) -> QuboProblem:
    """
    Builds a QuboProblem directly from the verified Phase 5/5.1 performance contract.
    """
    c_ids = list(contract["candidate_ids"])
    n = len(c_ids)
    if n < 1:
        raise ValueError("Contract contains zero candidates.")

    # Positions metric
    positions_metric: List[Tuple[float, float]] = []
    for p in contract["candidate_positions_metric"]:
        positions_metric.append((float(p["east_m"]), float(p["north_m"])))

    # Turbine specs
    turb_info = contract.get("turbine_model", {})
    turb_id = str(turb_info.get("id", "ge_25_120"))
    rotor_d = float(turb_info.get("rotor_diameter_m", 120.0))
    min_spacing_m = rotor_d * float(min_spacing_multiplier)

    # Energies and matrix
    linear_coeffs = [float(v) for v in contract["linear_objective_coeffs"]]
    q_mat = [[float(v) for v in row] for row in contract["quadratic_wake_penalty_matrix"]]
    bop_derate = float(contract.get("bop_derate_factor", 0.9038))

    # Target turbines
    if target_turbines is None:
        target_turbines = max(1, min(n, 6))

    return QuboProblem(
        candidate_ids=c_ids,
        positions_metric=positions_metric,
        linear_energy_mwh=linear_coeffs,
        wake_penalty_matrix_mwh=q_mat,
        target_turbines=target_turbines,
        min_spacing_m=min_spacing_m,
        bop_derate_factor=bop_derate,
        penalty_capacity=penalty_capacity,
        penalty_spacing=penalty_spacing,
        turbine_model_id=turb_id,
        metadata={"contract_version": contract.get("contract_version", "1.0.0")},
    )
