"""Module d'injection d'erreurs et de dégradation contrôlée.

Simule les imperfections du terrain togolais (formats disparates, fautes,
valeurs sentinelles, doublons patients) et produit le journal d'altérations exhaustif.
"""

from __future__ import annotations

from src.degradation.catalog import (
    DegradationCatalog,
    load_catalog,
    load_rules_catalog,
)
from src.degradation.engine import (
    DegradationEngine,
    apply_degradation,
)
from src.degradation.exporters import (
    export_degraded_csv,
    export_degraded_dhis2,
    export_degraded_excel,
    export_degraded_fhir,
)
from src.degradation.mutators import (
    mutate_approximate_age,
    mutate_clinical_freetext,
    mutate_date_format,
    mutate_encoding_mojibake,
    mutate_facility_name,
    mutate_invert_name_order,
    mutate_measurement_separator,
    mutate_measurement_unit,
    mutate_missing,
    mutate_name_spelling,
    mutate_sentinel,
    mutate_strip_accents,
)
from src.degradation.schemas import (
    ALTERATION_LOG_SCHEMA,
    AlterationRecord,
    DegradationConfig,
    DegradationRuleConfig,
)

__all__ = [
    "ALTERATION_LOG_SCHEMA",
    "AlterationRecord",
    "DegradationCatalog",
    "DegradationConfig",
    "DegradationEngine",
    "DegradationRuleConfig",
    "apply_degradation",
    "export_degraded_csv",
    "export_degraded_dhis2",
    "export_degraded_excel",
    "export_degraded_fhir",
    "load_catalog",
    "load_rules_catalog",
    "mutate_approximate_age",
    "mutate_clinical_freetext",
    "mutate_date_format",
    "mutate_encoding_mojibake",
    "mutate_facility_name",
    "mutate_invert_name_order",
    "mutate_measurement_separator",
    "mutate_measurement_unit",
    "mutate_missing",
    "mutate_name_spelling",
    "mutate_sentinel",
    "mutate_strip_accents",
]
