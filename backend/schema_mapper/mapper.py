"""
backend/schema_mapper/mapper.py
===============================
ReconPilot 2.0: Safe Schema Understanding & Column Mapping Engine.

Maps unpredictable merchant CSV column names to ReconPilot's canonical schema with
strict confidence threshold gating:
- >= 0.95: Auto-Map (automatically applied with 100% confidence)
- 0.80 - 0.94: Suggested Mapping (highlighted in UI for user confirmation)
- < 0.80: Rejected / Requires Manual Mapping (safe failure without guessing)
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from pydantic import BaseModel, Field

from backend.parser.csv_parser import EXPECTED_COLUMNS
from backend.schema_mapper.aliases import COLUMN_ALIASES
from backend.ai.llm_client import LLMClient


AUTO_MAP_CONFIDENCE_THRESHOLD: float = 0.95


class ColumnMappingResult(BaseModel):
    """Mapping result for a single input column."""
    original_name: str
    canonical_name: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    method: str  # "exact", "alias", "ai", "heuristic", "unmapped"
    tier: str = "auto_map"  # "auto_map" (>=0.95), "suggest" (0.80-0.94), "reject" (<0.80)
    notes: Optional[str] = None


class SchemaMapping(BaseModel):
    """Complete mapping from source CSV schema to canonical schema."""
    source_type: str
    column_mappings: List[ColumnMappingResult] = Field(default_factory=list)
    rename_dict: Dict[str, str] = Field(default_factory=dict)
    auto_rename_dict: Dict[str, str] = Field(default_factory=dict)
    suggested_mappings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    rejected_mappings: List[ColumnMappingResult] = Field(default_factory=list)
    missing_required: List[str] = Field(default_factory=list)
    is_valid: bool = False
    requires_user_confirmation: bool = False

    @property
    def mapped_canonical_columns(self) -> List[str]:
        return [m.canonical_name for m in self.column_mappings if m.canonical_name]


def _normalize_col_name(col: str) -> str:
    """Normalizes column names for matching (lowercase, alphanumeric + underscores)."""
    s = str(col).strip().lower()
    s = re.sub(r"[\s\-\./\\]+", "_", s)
    s = re.sub(r"[^\w_]", "", s)
    return s.strip("_")


class SchemaMapper:
    """
    AI & Safe Heuristic Schema Understanding Agent.
    Maps unpredictable merchant CSV column names to ReconPilot's canonical schema.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name or os.environ.get("AI_MODEL", "gpt-5.6-terra")

    def _call_llm_schema_detection(
        self,
        unmapped_cols: List[str],
        target_cols: List[str],
        sample_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        """Calls LLM to infer mapping for ambiguous/unknown columns."""
        if os.getenv("RECONPILOT_AI_MODE") == "offline":
            return {}

        has_creds = bool(self.gemini_api_key or self.openai_api_key)
        if not has_creds:
            return {}

        system_prompt = (
            "You are a financial data schema mapper. Given a list of CSV column names from a merchant's financial file "
            "and optional sample data, map each input column to its matching canonical column from the allowed target list.\n"
            f"Allowed target columns: {json.dumps(target_cols)}\n\n"
            "Return ONLY a JSON object mapping the input column name to the target column name (or null if unmapped):\n"
            '{"<input_column>": "<target_column_or_null>"}'
        )

        user_content = {
            "unmapped_columns": unmapped_cols,
            "target_candidate_columns": target_cols,
            "sample_rows": (sample_rows[:3] if sample_rows else []),
        }
        user_prompt = f"Map these financial columns to canonical targets:\n{json.dumps(user_content, indent=2)}"

        try:
            client = LLMClient(
                openai_api_key=self.openai_api_key,
                gemini_api_key=self.gemini_api_key,
                model_name=self.model_name,
            )
            llm_res = client.generate_json_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                fallback_simulation_fn=lambda: {},
            )
            return llm_res.parsed_json if isinstance(llm_res.parsed_json, dict) else {}
        except Exception:
            return {}

    def map_columns(
        self,
        columns: List[str],
        source_type: str,
        sample_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> SchemaMapping:
        """
        Maps a list of raw column names to the canonical schema for source_type with safety thresholds.
        """
        source_lower = source_type.strip().lower()
        if source_lower in ("bank", "bank_statement", "bank_statements"):
            expected_targets = EXPECTED_COLUMNS["bank"]
        elif source_lower == "settlement":
            expected_targets = EXPECTED_COLUMNS["settlement"]
        else:
            expected_targets = EXPECTED_COLUMNS["invoice"]

        results: List[ColumnMappingResult] = []
        rename_dict: Dict[str, str] = {}
        auto_rename_dict: Dict[str, str] = {}
        suggested: Dict[str, Dict[str, Any]] = {}
        rejected: List[ColumnMappingResult] = []
        assigned_targets: set = set()
        mapped_input_cols: set = set()

        # Step 1: Collect exact and alias candidate matches for all input columns
        target_candidates: Dict[str, List[Tuple[str, str, float, str]]] = {}
        for target in expected_targets:
            target_candidates[target] = []

        for col in columns:
            norm_col = _normalize_col_name(col)
            # Check exact match
            if norm_col in expected_targets:
                target_candidates[norm_col].append(
                    (col, "exact", 1.0, "Exact canonical name match.")
                )
            else:
                # Check dictionary alias
                matched_target = None
                for target, aliases in COLUMN_ALIASES.items():
                    if target in expected_targets and (norm_col in aliases or norm_col == target):
                        matched_target = target
                        break
                if matched_target:
                    target_candidates[matched_target].append(
                        (col, "alias", 0.96, f"Mapped via verified financial synonym dictionary to '{matched_target}'.")
                    )

        # Step 2: Resolve matches and detect ambiguities
        for target in expected_targets:
            candidates = target_candidates.get(target, [])
            if len(candidates) == 1:
                # Single unambiguous match -> auto_map
                col, method, conf, notes = candidates[0]
                res = ColumnMappingResult(
                    original_name=col,
                    canonical_name=target,
                    confidence=conf,
                    method=method,
                    tier="auto_map",
                    notes=notes,
                )
                results.append(res)
                rename_dict[col] = target
                auto_rename_dict[col] = target
                assigned_targets.add(target)
                mapped_input_cols.add(col)
            elif len(candidates) > 1:
                # Ambiguity: multiple columns match the same canonical target
                cand_names = [c[0] for c in candidates]
                suggested[target] = {
                    "source_column": ", ".join(cand_names),
                    "candidates": cand_names,
                    "confidence": 0.80,
                    "method": "ambiguous_match",
                    "notes": f"Multiple columns ({', '.join(cand_names)}) match canonical target '{target}'.",
                }
                for col, method, conf, notes in candidates:
                    res = ColumnMappingResult(
                        original_name=col,
                        canonical_name=target,
                        confidence=0.80,
                        method="ambiguous",
                        tier="suggest",
                        notes=f"Ambiguous match for target '{target}' with multiple candidates ({', '.join(cand_names)}).",
                    )
                    results.append(res)
                    mapped_input_cols.add(col)

        # Step 3: AI & Safe Heuristic Fallback for remaining unmapped input columns
        remaining_inputs = [col for col in columns if col not in mapped_input_cols]
        if remaining_inputs and (len(assigned_targets) < len(expected_targets)):
            available_targets = [t for t in expected_targets if t not in assigned_targets and t not in suggested]
            ai_mappings = self._call_llm_schema_detection(remaining_inputs, available_targets, sample_rows)

            for col in remaining_inputs:
                norm_col = _normalize_col_name(col)
                ai_target = ai_mappings.get(col) or ai_mappings.get(norm_col)

                if ai_target and ai_target in available_targets and ai_target not in assigned_targets:
                    # AI confidence 0.90 -> Tier: suggest (requires confirmation)
                    res = ColumnMappingResult(
                        original_name=col,
                        canonical_name=ai_target,
                        confidence=0.90,
                        method="ai",
                        tier="suggest",
                        notes=f"AI inferred column mapping to '{ai_target}'. Suggested for review.",
                    )
                    results.append(res)
                    suggested[ai_target] = {
                        "source_column": col,
                        "confidence": 0.90,
                        "method": "ai",
                    }
                else:
                    # Safe heuristic substring check
                    heuristic_target = None
                    for t in available_targets:
                        if t in norm_col or any(alias in norm_col for alias in COLUMN_ALIASES.get(t, [])):
                            heuristic_target = t
                            break
                    
                    if heuristic_target and heuristic_target not in assigned_targets:
                        # Heuristic confidence 0.85 -> Tier: suggest
                        res = ColumnMappingResult(
                            original_name=col,
                            canonical_name=heuristic_target,
                            confidence=0.85,
                            method="heuristic",
                            tier="suggest",
                            notes=f"Pattern similarity match to '{heuristic_target}'.",
                        )
                        results.append(res)
                        suggested[heuristic_target] = {
                            "source_column": col,
                            "confidence": 0.85,
                            "method": "heuristic",
                        }
                    else:
                        # Below threshold (<0.80) -> Tier: reject
                        res = ColumnMappingResult(
                            original_name=col,
                            canonical_name=None,
                            confidence=0.0,
                            method="unmapped",
                            tier="reject",
                            notes="Column could not be safely mapped to any expected schema column.",
                        )
                        results.append(res)
                        rejected.append(res)
        elif remaining_inputs:
            for col in remaining_inputs:
                res = ColumnMappingResult(
                    original_name=col,
                    canonical_name=None,
                    confidence=0.0,
                    method="unmapped",
                    tier="reject",
                    notes="Column could not be safely mapped to any expected schema column.",
                )
                results.append(res)
                rejected.append(res)

        missing = [target for target in expected_targets if target not in assigned_targets]
        is_valid = len(missing) == 0
        has_suggested_required = any(target in suggested for target in missing)

        return SchemaMapping(
            source_type=source_type,
            column_mappings=results,
            rename_dict=rename_dict,
            auto_rename_dict=auto_rename_dict,
            suggested_mappings=suggested,
            rejected_mappings=rejected,
            missing_required=missing,
            is_valid=is_valid,
            requires_user_confirmation=has_suggested_required or len(rejected) > 0,
        )

    def remap_dataframe(self, df: pd.DataFrame, source_type: str) -> Tuple[pd.DataFrame, SchemaMapping]:
        """
        Detects schema and returns a new DataFrame with canonical column names.
        """
        sample_rows = df.head(3).to_dict(orient="records") if not df.empty else None
        mapping = self.map_columns(list(df.columns), source_type, sample_rows=sample_rows)
        remapped_df = df.rename(columns=mapping.rename_dict)
        return remapped_df, mapping


default_schema_mapper = SchemaMapper()


def map_schema(columns: List[str], source_type: str, sample_rows: Optional[List[Dict[str, Any]]] = None) -> SchemaMapping:
    """Convenience helper for schema mapping."""
    return default_schema_mapper.map_columns(columns, source_type, sample_rows=sample_rows)


def remap_dataframe(df: pd.DataFrame, source_type: str) -> Tuple[pd.DataFrame, SchemaMapping]:
    """Convenience helper for DataFrame remapping."""
    return default_schema_mapper.remap_dataframe(df, source_type)
