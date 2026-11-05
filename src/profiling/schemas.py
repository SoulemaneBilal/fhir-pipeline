"""Modèles de données et schémas Pydantic v2 pour le profilage qualité (Étape 6).

Définit les 6 dimensions normatives de qualité (complétude, exactitude, cohérence,
unicité, validité, actualité), les métriques par colonne, les synthèses de tables,
les métriques de rappel face au corrigé d'altérations et le rapport global.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class QualityDimension(StrEnum):
    """Les 6 dimensions normatives de qualité de données de santé."""

    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    TIMELINESS = "timeliness"


class ColumnMetric(BaseModel):
    """Métriques statistiques et de qualité d'une colonne."""

    table_name: str
    column_name: str
    total_rows: int
    null_count: int = 0
    null_ratio: float = 0.0
    sentinel_count: int = 0
    sentinel_ratio: float = 0.0
    completeness_score: float = 100.0
    distinct_count: int = 0
    duplicate_count: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    sample_anomalies: list[Any] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DimensionScore(BaseModel):
    """Score d'évaluation d'une dimension de qualité (0.0 à 100.0%)."""

    dimension: QualityDimension | str
    score: float
    status: str | None = None
    description: str = ""
    issues_detected: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class TableQualitySummary(BaseModel):
    """Synthèse de la qualité globale d'une table clinique."""

    table_name: str
    total_rows: int
    columns_count: int
    dimension_scores: dict[QualityDimension | str, float]
    global_score: float
    columns: dict[str, ColumnMetric] = Field(default_factory=dict)
    issues_count: int = 0


class RecallMetric(BaseModel):
    """Métrique de rappel et précision de détection par règle d'altération."""

    rule_id: str
    rule_name: str = ""
    target_table: str = ""
    target_column: str = ""
    total_injected: int
    detected_count: int
    recall: float
    precision: float | None = None
    description: str = ""


class ProfilingReport(BaseModel):
    """Rapport d'évaluation complet de la qualité de la couche Bronze."""

    report_id: str
    generated_at: str
    overall_score: float
    dimensions: dict[QualityDimension | str, float]
    tables: dict[str, TableQualitySummary]
    total_rows_analyzed: int = 0
    total_issues_detected: int = 0
    recall_metrics: list[RecallMetric] | None = None
    summary_notes: list[str] = Field(default_factory=list)
