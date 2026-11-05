"""Schémas Pydantic et PyArrow pour le moteur de dégradation contrôlée.

Définit les contrats de données pour :
- La configuration des règles déclaratives (DegradationRuleConfig)
- Les paramètres globaux d'exécution du moteur (DegradationConfig)
- Les enregistrements du journal d'altérations exhaustif (AlterationRecord)
- Le schéma PyArrow strict pour la sérialisation Parquet (ALTERATION_LOG_SCHEMA)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pyarrow as pa
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from pathlib import Path


class DegradationRuleConfig(BaseModel):
    """Configuration d'une règle unitaire de dégradation."""

    rule_id: str
    name: str
    category: str
    description: str
    target_tables: list[str] = Field(default_factory=list)
    target_columns: list[str] = Field(default_factory=list)
    default_rate: float = 0.15
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("default_rate")
    @classmethod
    def validate_default_rate(cls, v: float) -> float:
        """Valide que le taux par défaut est borné entre 0.0 et 1.0."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"default_rate doit être compris entre 0.0 et 1.0, reçu: {v}")
        return v


class DegradationConfig(BaseModel):
    """Paramètres d'exécution pour le moteur de dégradation."""

    rate: float = 0.15
    seed: int = 42
    rules_config_path: Path | None = None
    enabled_rules: list[str] | None = None
    target_formats: list[str] | None = None
    tolerance: float = 0.05

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        """Valide rigoureusement le taux global d'altération [0.0, 1.0]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(
                f"Le taux d'altération (rate) doit être compris entre 0.0 et 1.0, reçu: {v}"
            )
        return v


class AlterationRecord(BaseModel):
    """Entrée unique dans le journal d'altérations et de traçabilité."""

    alteration_id: str
    table_name: str
    row_id: str
    column_name: str
    original_value: str | None = None
    altered_value: str | None = None
    rule_id: str
    description: str
    timestamp: str = "2024-01-01T00:00:00Z"

    @field_validator("original_value", "altered_value", mode="before")
    @classmethod
    def convert_to_str_or_none(cls, v: Any) -> str | None:
        """Convertit toute valeur source en chaîne ou None pour sérialisation uniforme."""
        if v is None:
            return None
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        if str(v) == "<NA>":
            return None
        return str(v)


ALTERATION_LOG_SCHEMA: pa.Schema = pa.schema(
    [
        ("alteration_id", pa.string()),
        ("table_name", pa.string()),
        ("row_id", pa.string()),
        ("column_name", pa.string()),
        ("original_value", pa.string()),
        ("altered_value", pa.string()),
        ("rule_id", pa.string()),
        ("description", pa.string()),
        ("timestamp", pa.string()),
    ]
)
