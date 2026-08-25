import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any
import httpx
import pandas as pd
from pydantic import BaseModel, Field

from backend.parser.csv_parser import EXPECTED_COLUMNS
from backend.schema_mapper.aliases import COLUMN_ALIASES


class ColumnMappingResult(BaseModel):
    """Mapping result for a single input column."""
    original_name: str
    canonical_name: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    method: str  # "exact", "alias", "ai", "heuristic", "unmapped"
    notes: Optional[str] = None


class SchemaMapping(BaseModel):
    """Complete mapping from source CSV schema to canonical schema."""
    source_type: str
    column_mappings: List[ColumnMappingResult] = Field(default_factory=list)
    rename_dict: Dict[str, str] = Field(default_factory=dict)
    missing_required: List[str] = Field(default_factory=list)
    is_valid: bool = False

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
    AI & Heuristic Schema Understanding Agent.
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

        if self.gemini_api_key:
            try:
                active_model = self.model_name if "gemini" in self.model_name.lower() else "gemini-2.5-pro"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={self.gemini_api_key}"
                payload = {
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json", "temperature": 0.0},
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(raw_text)
            except Exception:
                pass

        elif self.openai_api_key:
            try:
                active_model = self.model_name if "gpt" in self.model_name.lower() else "gpt-5.6-terra"
                headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": active_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return json.loads(data["choices"][0]["message"]["content"])
            except Exception:
                pass

        return {}

    def map_columns(
        self,
        columns: List[str],
        source_type: str,
        sample_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> SchemaMapping:
        """
        Maps a list of raw column names to the canonical schema for source_type.
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
        assigned_targets: set = set()
        unmapped_inputs: List[str] = []

        # 1. Exact Match Phase
        for col in columns:
            norm_col = _normalize_col_name(col)
            if norm_col in expected_targets and norm_col not in assigned_targets:
                results.append(ColumnMappingResult(
                    original_name=col,
                    canonical_name=norm_col,
                    confidence=1.0,
                    method="exact",
                    notes="Exact canonical name match.",
                ))
                rename_dict[col] = norm_col
                assigned_targets.add(norm_col)
            else:
                unmapped_inputs.append(col)

        # 2. Dictionary Alias Phase
        remaining_inputs: List[str] = []
        for col in unmapped_inputs:
            norm_col = _normalize_col_name(col)
            matched_target = None

            for target, aliases in COLUMN_ALIASES.items():
                if target in expected_targets and target not in assigned_targets:
                    if norm_col in aliases or norm_col == target:
                        matched_target = target
                        break

            if matched_target:
                results.append(ColumnMappingResult(
                    original_name=col,
                    canonical_name=matched_target,
                    confidence=0.95,
                    method="alias",
                    notes=f"Mapped via known alias dictionary to '{matched_target}'.",
                ))
                rename_dict[col] = matched_target
                assigned_targets.add(matched_target)
            else:
                remaining_inputs.append(col)

        # 3. AI / Heuristic Fallback Phase for remaining columns
        if remaining_inputs and (len(assigned_targets) < len(expected_targets)):
            available_targets = [t for t in expected_targets if t not in assigned_targets]
            ai_mappings = self._call_llm_schema_detection(remaining_inputs, available_targets, sample_rows)

            for col in remaining_inputs:
                norm_col = _normalize_col_name(col)
                ai_target = ai_mappings.get(col) or ai_mappings.get(norm_col)

                if ai_target and ai_target in available_targets and ai_target not in assigned_targets:
                    results.append(ColumnMappingResult(
                        original_name=col,
                        canonical_name=ai_target,
                        confidence=0.90,
                        method="ai",
                        notes=f"AI inferred column mapping to '{ai_target}'.",
                    ))
                    rename_dict[col] = ai_target
                    assigned_targets.add(ai_target)
                else:
                    # Heuristic substring check
                    heuristic_target = None
                    for t in available_targets:
                        if t in norm_col or any(alias in norm_col for alias in COLUMN_ALIASES.get(t, [])):
                            heuristic_target = t
                            break
                    
                    if heuristic_target and heuristic_target not in assigned_targets:
                        results.append(ColumnMappingResult(
                            original_name=col,
                            canonical_name=heuristic_target,
                            confidence=0.75,
                            method="heuristic",
                            notes=f"Heuristic pattern match to '{heuristic_target}'.",
                        ))
                        rename_dict[col] = heuristic_target
                        assigned_targets.add(heuristic_target)
                    else:
                        results.append(ColumnMappingResult(
                            original_name=col,
                            canonical_name=None,
                            confidence=0.0,
                            method="unmapped",
                            notes="Column could not be mapped to any expected schema column.",
                        ))

        missing = [target for target in expected_targets if target not in assigned_targets]
        is_valid = len(missing) == 0

        return SchemaMapping(
            source_type=source_type,
            column_mappings=results,
            rename_dict=rename_dict,
            missing_required=missing,
            is_valid=is_valid,
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
