"""Module de profilage statistique et d'évaluation de la qualité (Étape 6).

Évalue la qualité selon les 6 dimensions normatives (complétude, validité,
exactitude, unicité, cohérence, actualité), confronte les anomalies au journal
d'altérations et produit le Rapport Avant (Markdown et JSON).
"""

from __future__ import annotations

from src.profiling.dimensions import (
    evaluate_accuracy,
    evaluate_completeness,
    evaluate_consistency,
    evaluate_timeliness,
    evaluate_uniqueness,
    evaluate_validity,
)
from src.profiling.engine import QualityProfiler
from src.profiling.reporter import generate_json_report, generate_markdown_report
from src.profiling.schemas import (
    ColumnMetric,
    DimensionScore,
    ProfilingReport,
    QualityDimension,
    RecallMetric,
    TableQualitySummary,
)

__all__ = [
    "QualityDimension",
    "ColumnMetric",
    "DimensionScore",
    "TableQualitySummary",
    "RecallMetric",
    "ProfilingReport",
    "evaluate_completeness",
    "evaluate_accuracy",
    "evaluate_consistency",
    "evaluate_uniqueness",
    "evaluate_validity",
    "evaluate_timeliness",
    "QualityProfiler",
    "generate_markdown_report",
    "generate_json_report",
]
