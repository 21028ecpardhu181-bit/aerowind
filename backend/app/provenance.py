"""
backend/app/provenance.py — Engineering Data Provenance & Source Metadata Architecture.

Core Principles:
1. NO ENGINEERING NUMBER WITHOUT TRACEABLE PROVENANCE.
2. MISSING DATA CAN NEVER YIELD "SAFE", "CLEAR", OR "FEASIBLE".
3. STRICT TAXONOMY:
   - VERIFIED_REAL
   - PARTIAL
   - MANUAL_REQUIRED
   - UNAVAILABLE
   - HARDCODED
   - MOCK
   - UNKNOWN
   - NOT_ENGINEERING_GRADE
"""

from __future__ import annotations

import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class SourceStatus(str, Enum):
    VERIFIED_REAL = "VERIFIED_REAL"
    PARTIAL = "PARTIAL"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    HARDCODED = "HARDCODED"
    MOCK = "MOCK"
    UNKNOWN = "UNKNOWN"
    NOT_ENGINEERING_GRADE = "NOT_ENGINEERING_GRADE"


class EngineeringSuitability(str, Enum):
    ENGINEERING_GRADE = "ENGINEERING_GRADE"
    PRELIMINARY_SCREENING_ONLY = "PRELIMINARY_SCREENING_ONLY"
    REAL_WEATHER_NOT_LONG_TERM_RESOURCE = "REAL_WEATHER_NOT_LONG_TERM_RESOURCE"
    NOT_ENGINEERING_GRADE = "NOT_ENGINEERING_GRADE"
    UNKNOWN = "UNKNOWN"


class ProvenanceMetadata(BaseModel):
    """
    Standard schema for any environmental, geographic, or engineering value.
    Ensures every number returned by the API carries rigorous source lineage.
    """
    model_config = ConfigDict(extra="ignore")

    value: Any = Field(..., description="The scalar or structured engineering measurement")
    unit: str = Field(..., description="Standard SI or engineering unit (e.g. 'm', 'm/s', 'kPa', 'deg', 'GWh')")
    source: str = Field(..., description="Authoritative organization or entity")
    source_url: Optional[str] = Field(None, description="Direct URL to official data portal or publication")
    dataset: str = Field(..., description="Official dataset name and tier")
    version: Optional[str] = Field(None, description="Dataset release version or model iteration")
    resolution: Optional[str] = Field(None, description="Spatial and/or temporal resolution")
    crs: Optional[str] = Field("EPSG:4326", description="Coordinate Reference System")
    retrieved_at: str = Field(..., description="ISO 8601 UTC timestamp of data retrieval")
    license: Optional[str] = Field(None, description="Data licensing terms and redistribution rights")
    status: SourceStatus = Field(..., description="Rigorous source status classification")
    engineering_suitability: EngineeringSuitability = Field(
        EngineeringSuitability.PRELIMINARY_SCREENING_ONLY,
        description="Applicability for formal micro-siting decisions"
    )
    is_authoritative: bool = Field(False, description="Flag indicating primary statutory/certified dataset")
    limitations: Optional[str] = Field(None, description="Known operational or scientific limitations")


class RegulatorySetbackRule(BaseModel):
    """
    Formal specification for an onshore wind statutory setback constraint.
    Replaces arbitrary assumptions with legal citations (e.g., MNRE 2024 Guidelines).
    """
    model_config = ConfigDict(extra="ignore")

    constraint_id: str
    target_feature: str
    statutory_authority: str = "Ministry of New and Renewable Energy (MNRE), India"
    governing_document: str = "Guidelines for Development of Onshore Wind Power Projects"
    section_reference: str
    effective_date: str = "2024-07-04"
    formula_or_fixed: str = "formula"
    distance_formula: Optional[str] = None
    fixed_distance_m: Optional[float] = None
    applicability_criteria: str
    legal_status: str = "MANDATORY"
    confidence: str = "VERIFIED_REGULATORY"

    def calculate_setback_m(self, hub_height_m: float, rotor_diameter_m: float) -> float:
        """Evaluates statutory formula: Hub Height + 0.5 * Rotor Diameter + 5 meters."""
        if self.fixed_distance_m is not None:
            return float(self.fixed_distance_m)
        return float(hub_height_m + 0.5 * rotor_diameter_m + 5.0)


# Standard MNRE 2024 Regulatory Setback Catalog
MNRE_2024_SETBACKS: Dict[str, RegulatorySetbackRule] = {
    "habitation_cluster": RegulatorySetbackRule(
        constraint_id="MNRE-2024-HABITATION",
        target_feature="Habitation Cluster (>= 15 inhabited dwellings)",
        section_reference="Clause on Noise Mitigation & Habitation Setback (July 4, 2024 Amendment)",
        formula_or_fixed="fixed",
        fixed_distance_m=500.0,
        applicability_criteria="Applies to clusters of at least 15 inhabited buildings unless State norms prescribe higher.",
        legal_status="MANDATORY",
    ),
    "public_roads": RegulatorySetbackRule(
        constraint_id="MNRE-2024-PUBLIC-ROADS",
        target_feature="Notified Public Roads (State/National Highways and Major District Roads)",
        section_reference="Clause on Infrastructure Safety Distances (July 4, 2024 Amendment)",
        formula_or_fixed="formula",
        distance_formula="HH + 0.5 * RD + 5m",
        applicability_criteria="Public roads marked or notified by Central or State Government.",
        legal_status="MANDATORY",
    ),
    "railway_tracks": RegulatorySetbackRule(
        constraint_id="MNRE-2024-RAILWAYS",
        target_feature="Railway Tracks (Indian Railways Network)",
        section_reference="Clause on Infrastructure Safety Distances (July 4, 2024 Amendment)",
        formula_or_fixed="formula",
        distance_formula="HH + 0.5 * RD + 5m",
        applicability_criteria="All operational and notified railway alignments.",
        legal_status="MANDATORY",
    ),
    "buildings_institutions": RegulatorySetbackRule(
        constraint_id="MNRE-2024-PUBLIC-INSTITUTIONS",
        target_feature="Buildings & Public Institutions",
        section_reference="Clause on Infrastructure Safety Distances (July 4, 2024 Amendment)",
        formula_or_fixed="formula",
        distance_formula="HH + 0.5 * RD + 5m",
        applicability_criteria="Schools, hospitals, government offices, and permanent civil structures.",
        legal_status="MANDATORY",
    ),
    "ehv_transmission_lines": RegulatorySetbackRule(
        constraint_id="MNRE-2024-EHV-LINES",
        target_feature="Extra High Voltage (EHV) Transmission Lines",
        section_reference="Clause on Infrastructure Safety Distances (July 4, 2024 Amendment)",
        formula_or_fixed="formula",
        distance_formula="HH + 0.5 * RD + 5m",
        applicability_criteria="Lines above 66kV transmission voltage level.",
        legal_status="MANDATORY",
    ),
    "inter_developer_wind_perpendicular": RegulatorySetbackRule(
        constraint_id="MNRE-2024-INTER-DEV-5D",
        target_feature="Adjacent Developer Turbine (Perpendicular to Predominant Wind)",
        section_reference="Clause on Micrositing & Inter-Developer Distances (July 4, 2024 Amendment)",
        formula_or_fixed="formula",
        distance_formula="5.0 * max(RD_1, RD_2)",
        applicability_criteria="Between turbines of different developers perpendicular to dominant wind direction.",
        legal_status="MANDATORY",
    ),
    "inter_developer_wind_parallel": RegulatorySetbackRule(
        constraint_id="MNRE-2024-INTER-DEV-7D",
        target_feature="Adjacent Developer Turbine (In Line with Predominant Wind)",
        section_reference="Clause on Micrositing & Inter-Developer Distances (July 4, 2024 Amendment)",
        formula_or_fixed="formula",
        distance_formula="7.0 * max(RD_1, RD_2)",
        applicability_criteria="Between turbines of different developers along dominant wind direction.",
        legal_status="MANDATORY",
    ),
}


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Lightweight YAML parser for structured provider dictionaries without PyYAML dependency."""
    try:
        import yaml
        return yaml.safe_load(text)
    except ImportError:
        pass

    # Simple indented key-value parser for providers
    result: Dict[str, Any] = {"providers": {}}
    lines = text.splitlines()
    current_key: Optional[str] = None
    in_providers = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "providers:":
            in_providers = True
            continue
        if in_providers:
            # Check 2-space or 4-space indent
            if line.startswith("  ") and not line.startswith("    "):
                # Provider name
                m = re.match(r"^  ([a-zA-Z0-9_-]+):", line)
                if m:
                    current_key = m.group(1)
                    result["providers"][current_key] = {}
            elif line.startswith("    ") and current_key:
                # Field
                parts = line.strip().split(":", 1)
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")
                    if v.lower() == "true":
                        val: Any = True
                    elif v.lower() == "false":
                        val = False
                    else:
                        try:
                            val = float(v) if "." in v else int(v)
                        except ValueError:
                            val = v
                    result["providers"][current_key][k] = val
    return result


class ProviderRegistry:
    """Manages verified provider configuration loaded from providers.yaml or providers.json."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent / "data" / "providers.yaml"
        self.config_path = Path(config_path)
        self.providers: Dict[str, Any] = {}
        self.load_registry()

    def load_registry(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Provider registry configuration not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()
            data = parse_simple_yaml(content)
            self.providers = data.get("providers", {})

    def get_provider_metadata(self, key: str) -> Dict[str, Any]:
        """Returns registered provider metadata or raises error."""
        if key not in self.providers:
            raise KeyError(f"Provider '{key}' not registered in {self.config_path}")
        return self.providers[key]

    def get_status(self, key: str) -> SourceStatus:
        meta = self.get_provider_metadata(key)
        return SourceStatus(meta.get("status", "UNKNOWN"))


provider_registry = ProviderRegistry()
