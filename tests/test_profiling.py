"""Tests E2E, unitaires et de validation du Moteur de Profilage et Diagnostic Initial (Étape 6).

Conforme aux spécifications formelles de DISPATCH.md, SCOPE.md, Roadmap technique.md §6
et SYNTHESE_PROJET.md §3.1 (Étape 6).

Structure de la suite de tests :
- Tier 1 : Modèles, Schémas & Enums de Profilage (QualityDimension, ColumnMetric, DimensionScore,
          TableQualitySummary, RecallMetric, ProfilingReport)
- Tier 2 : Évaluateurs Dimensionnels Unitaires (6 Dimensions normatives) :
          * Complétude (evaluate_completeness : nulls, sentinelles, chaînes vides)
          * Exactitude (evaluate_accuracy : dates hétérogènes, âges approximatifs, mojibake, virgules)
          * Cohérence (evaluate_consistency : grossesses masculines, dates inversées, discordance pyramide)
          * Unicité (evaluate_uniqueness : doublons stricts, quasi-doublons suspects Splink)
          * Validité (evaluate_validity : référentiels CIM-10, LOINC, ATC, géographie Togo, UCUM)
          * Actualité (evaluate_timeliness : dates futures, dates historiques aberrantes < 1900)
- Tier 3 : Moteur de Profilage Global (QualityProfiler, profilage par table, par dataset et par répertoire,
          score global de santé qualité, déterminisme, robustesse aux cas limites)
- Tier 4 : Confrontation au Corrigé d'Altérations (compare_with_alterations_log, TP/FN, matrice de rappel
          par règle, validation du seuil E2E rappel >= 80% sur données dégradées)
- Tier 5 : Générateur de Rapports (Markdown structuré avec synthèse exécutive, jauge, 6 dimensions,
          détail par table, matrice de rappel, et export JSON machine-readable)
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

IS_STRICT = os.environ.get("STRICT_E2E") == "1"

# Chemins des référentiels et données
DATA_DEGRADED_DIR = Path("data/degraded")
DATA_TRUTH_DIR = Path("data/truth")
ALTERATIONS_LOG_PATH = Path("data/degraded/alterations_log.parquet")
VOCABULARIES_PATH = Path("terminology/sample_vocabularies.parquet")
GEOGRAPHY_PATH = Path("data/reference/togo_health_geography.parquet")

CLINICAL_TABLES = [
    "patients",
    "encounters",
    "conditions",
    "observations",
    "prescriptions",
    "immunizations",
]

# Les 6 dimensions normatives de qualité de données
MANDATORY_DIMENSIONS = [
    "COMPLETENESS",
    "ACCURACY",
    "CONSISTENCY",
    "UNIQUENESS",
    "VALIDITY",
    "TIMELINESS",
]

# Règles d'altérations majeures attendues dans le journal
KEY_ALTERATION_RULES = [
    "RULE-DATE-001",  # Formats de dates hétérogènes
    "RULE-DATE-002",  # Âge approximatif textuel
    "RULE-NAME-001",  # Coquilles patronymes togolais
    "RULE-NAME-002",  # Suppression diacritiques
    "RULE-CLIN-001",  # Libellés cliniques libres
    "RULE-MEAS-001",  # Virgule décimale francophone
    "RULE-MEAS-002",  # Unités non UCUM
    "RULE-SENT-001",  # Codes sentinelles
    "RULE-MISS-001",  # Valeurs manquantes
    "RULE-DUPL-001",  # Doublons patients inter-établissements
    "RULE-ENCO-001",  # Mojibake encodage
    "RULE-FACI-001",  # Variantes formations sanitaires
]


# ==============================================================================
# Fonctions d'import et de résolution dynamique (Progressive Testability)
# ==============================================================================


def _require_schemas_module() -> Any:
    """Importe dynamiquement le module de schémas de profilage."""
    try:
        import src.profiling.schemas as schemas_mod

        return schemas_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.profiling.schemas obligatoire manquant : {exc}")
        pytest.skip(f"src.profiling.schemas en attente d'implémentation : {exc}")


def _require_dimensions_module() -> Any:
    """Importe dynamiquement le module des évaluateurs dimensionnels."""
    try:
        import src.profiling.dimensions as dim_mod

        return dim_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.profiling.dimensions obligatoire manquant : {exc}")
        pytest.skip(f"src.profiling.dimensions en attente d'implémentation : {exc}")


def _require_engine_module() -> Any:
    """Importe dynamiquement le module du moteur de profilage global."""
    try:
        import src.profiling.engine as eng_mod

        return eng_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.profiling.engine obligatoire manquant : {exc}")
        pytest.skip(f"src.profiling.engine en attente d'implémentation : {exc}")


def _require_reporter_module() -> Any:
    """Importe dynamiquement le module de génération des rapports."""
    try:
        import src.profiling.reporter as rep_mod

        return rep_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.profiling.reporter obligatoire manquant : {exc}")
        pytest.skip(f"src.profiling.reporter en attente d'implémentation : {exc}")


# ==============================================================================
# Fixtures de données synthétiques propres et dégradées
# ==============================================================================


@pytest.fixture
def clean_patients_df() -> pd.DataFrame:
    """DataFrame synthétique propre de patients (100% conforme)."""
    return pd.DataFrame(
        {
            "patient_id": [f"PAT-{i:04d}" for i in range(1, 11)],
            "family_name": [
                "Mensah",
                "Lawson",
                "Koffi",
                "Ablavi",
                "Adjamagbo",
                "Tchagbele",
                "Kodjo",
                "Ametowobla",
                "Ayeva",
                "Gbeho",
            ],
            "given_name": [
                "Koffi",
                "Afi",
                "Essi",
                "Kokou",
                "Yawovi",
                "Akossiwa",
                "Komla",
                "Afivi",
                "Enyonam",
                "Edoh",
            ],
            "gender": [
                "male",
                "female",
                "female",
                "male",
                "male",
                "female",
                "male",
                "female",
                "female",
                "male",
            ],
            "birth_date": [
                "1985-04-12",
                "1990-11-23",
                "1978-01-05",
                "2001-09-17",
                "1995-07-30",
                "1988-03-14",
                "1965-12-01",
                "2010-06-25",
                "1992-08-19",
                "1973-02-28",
            ],
            "address_city": [
                "Lomé",
                "Aného",
                "Kpalimé",
                "Atakpamé",
                "Sokodé",
                "Kara",
                "Dapaong",
                "Tsévié",
                "Notsé",
                "Bassar",
            ],
            "phone_number": [f"+2289000{i:04d}" for i in range(1, 11)],
        }
    )


@pytest.fixture
def degraded_patients_df() -> pd.DataFrame:
    """DataFrame synthétique de patients avec anomalies injectées représentatives."""
    return pd.DataFrame(
        {
            "patient_id": [
                "PAT-0001",
                "PAT-0002",
                "PAT-0003",
                "PAT-0004",
                "PAT-0005",
                "PAT-0006",
                "PAT-0007",
                "PAT-0008",
                "PAT-0001",  # Doublon strict de clé primaire
                "PAT-0010",
            ],
            "family_name": [
                "Mensah",
                "Mensa",  # Coquille patronyme (RULE-NAME-001)
                "Koffi",
                "Ablavi",
                "Adjamagbo",
                "TchagbÃ©lÃ©",  # Mojibake UTF-8 (RULE-ENCO-001)
                "Kodjo",
                "Ametowobla",
                "Mensah",  # Doublon
                None,  # Valeur manquante (RULE-MISS-001)
            ],
            "given_name": [
                "Koffi",
                "Afi",
                "Essi",
                "",  # Chaîne vide (RULE-MISS-001)
                "Yawovi",
                "Akossiwa",
                "Komla",
                "Afivi",
                "Koffi",
                "Edoh",
            ],
            "gender": [
                "male",
                "female",
                "female",
                "male",
                "male",
                "female",
                "male",
                "female",
                "male",
                "INCONNU",  # Genre non standard / sentinelle
            ],
            "birth_date": [
                "1985-04-12",
                "23/11/1990",  # Date non standard JJ/MM/AAAA (RULE-DATE-001)
                "environ 45 ans",  # Âge approximatif textuel (RULE-DATE-002)
                "2001-09-17",
                "1850-01-01",  # Date aberrante historique < 1900
                "2050-03-14",  # Date future
                "1965-12-01",
                "25-06-2010",  # Date non standard JJ-MM-AAAA (RULE-DATE-001)
                "1985-04-12",
                "999",  # Sentinelle (RULE-SENT-001)
            ],
            "address_city": [
                "Lomé",
                "Aného",
                "NA",  # Sentinelle (RULE-SENT-001)
                "Atakpamé",
                "Sokodé",
                "Kara",
                "-1",  # Sentinelle (RULE-SENT-001)
                "Tsévié",
                "Lomé",
                None,
            ],
            "phone_number": [
                "+22890000001",
                "-1",  # Sentinelle (RULE-SENT-001)
                "+22890000003",
                None,
                "+22890000005",
                "ND",  # Sentinelle (RULE-SENT-001)
                "+22890000007",
                "",
                "+22890000001",
                "999",
            ],
        }
    )


@pytest.fixture
def clean_encounters_df() -> pd.DataFrame:
    """DataFrame synthétique propre de consultations/séjours."""
    return pd.DataFrame(
        {
            "encounter_id": [f"ENC-{i:04d}" for i in range(1, 6)],
            "patient_id": [f"PAT-{i:04d}" for i in range(1, 6)],
            "facility_id": [
                "6f0d022e-716e-570d-ba5d-568ddc671c83",
                "23b939ee-3710-5cd7-af26-18c41d29e9b9",
                "6f0d022e-716e-570d-ba5d-568ddc671c83",
                "23b939ee-3710-5cd7-af26-18c41d29e9b9",
                "6f0d022e-716e-570d-ba5d-568ddc671c83",
            ],
            "facility_name": [
                "CHU Sylvanus Olympio",
                "CHR Tsévié",
                "CHU Sylvanus Olympio",
                "CHR Tsévié",
                "CHU Sylvanus Olympio",
            ],
            "facility_category": ["CHU", "CHR", "CHU", "CHR", "CHU"],
            "pyramid_level": [3, 2, 3, 2, 3],
            "district_code": ["TG-GOL", "TG-TSE", "TG-GOL", "TG-TSE", "TG-GOL"],
            "region_code": ["TG-M", "TG-M", "TG-M", "TG-M", "TG-M"],
            "start_date": [
                "2023-01-10",
                "2023-02-15",
                "2023-03-20",
                "2023-04-05",
                "2023-05-12",
            ],
            "end_date": [
                "2023-01-12",
                "2023-02-16",
                "2023-03-20",
                "2023-04-10",
                "2023-05-15",
            ],
        }
    )


@pytest.fixture
def degraded_encounters_df() -> pd.DataFrame:
    """DataFrame synthétique de consultations avec incohérences temporelles et géographiques."""
    return pd.DataFrame(
        {
            "encounter_id": ["ENC-0001", "ENC-0002", "ENC-0003", "ENC-0004", "ENC-0005"],
            "patient_id": ["PAT-0001", "PAT-0002", "PAT-0003", "PAT-0004", "PAT-0005"],
            "facility_id": [
                "6f0d022e-716e-570d-ba5d-568ddc671c83",
                "INVALID-FACILITY-UUID",  # Identifiant formation invalide
                "6f0d022e-716e-570d-ba5d-568ddc671c83",
                "23b939ee-3710-5cd7-af26-18c41d29e9b9",
                "6f0d022e-716e-570d-ba5d-568ddc671c83",
            ],
            "facility_name": [
                "CHU Sylvanus Olympio",
                "CHR Tsévié",
                "CHU SO",  # Sigle informel (RULE-FACI-001)
                "CHR Tsévié",
                "CHU Sylvanus Olympio",
            ],
            "facility_category": [
                "CHU",
                "CHR",
                "CHU",
                "USP",
                "CHU",
            ],
            "pyramid_level": [
                3,
                2,
                1,  # Incohérence : CHU classé niveau 1 au lieu de 3
                3,  # Incohérence : USP classé niveau 3 au lieu de 1
                3,
            ],
            "district_code": [
                "TG-GOL",
                "TG-INVALID-CODE",  # Code district invalide
                "TG-GOL",
                "TG-TSE",
                "TG-GOL",
            ],
            "region_code": ["TG-M", "TG-INCONNU", "TG-M", "TG-M", "TG-M"],
            "start_date": [
                "2023-01-10",
                "2023-05-20",  # Inversion temporelle : début > fin
                "2023-03-20",
                "2099-01-01",  # Date future
                "2023-05-12",
            ],
            "end_date": [
                "2023-01-12",
                "2023-05-15",  # Fin antérieure au début
                "2023-03-20",
                "2099-01-05",
                "2023-05-15",
            ],
        }
    )


@pytest.fixture
def observations_df() -> pd.DataFrame:
    """DataFrame synthétique d'observations (virgules décimales et unités)."""
    return pd.DataFrame(
        {
            "observation_id": [f"OBS-{i:04d}" for i in range(1, 7)],
            "patient_id": [f"PAT-{i:04d}" for i in range(1, 7)],
            "loinc_code": [
                "8310-5",
                "8480-6",
                "8310-5",
                "INVALID-LOINC",
                "8480-6",
                "8310-5",
            ],
            "loinc_display": [
                "Body temperature",
                "Systolic blood pressure",
                "Body temperature",
                "Unknown lab",
                "Systolic blood pressure",
                "Body temperature",
            ],
            "value_quantity": [
                "37.2",
                "120",
                "38,5",  # Virgule décimale (RULE-MEAS-001)
                "999",  # Sentinelle (RULE-SENT-001)
                "135,0",  # Virgule décimale (RULE-MEAS-001)
                "39.1",
            ],
            "value_numeric": [37.2, 120.0, None, -1.0, None, 39.1],
            "value_unit": [
                "Cel",
                "mm[Hg]",
                "°C",  # Unité non UCUM (RULE-MEAS-002)
                "NA",
                "mm[Hg]",
                "deg C",  # Unité non UCUM (RULE-MEAS-002)
            ],
        }
    )


@pytest.fixture
def conditions_df() -> pd.DataFrame:
    """DataFrame synthétique de diagnostics (grossesse masculine et codes CIM-10)."""
    return pd.DataFrame(
        {
            "condition_id": [f"CON-{i:04d}" for i in range(1, 6)],
            "patient_id": [
                "PAT-0001",  # Homme (dans clean_patients_df)
                "PAT-0002",  # Femme
                "PAT-0003",  # Femme
                "PAT-0004",  # Homme
                "PAT-0005",  # Homme
            ],
            "gender": ["male", "female", "female", "male", "male"],
            "icd10_code": [
                "Z34.0",  # Grossesse normale chez un homme -> Incohérence clinique
                "B54",  # Paludisme non spécifié (valide)
                "O80",  # Accouchement unique spontané chez une femme (valide)
                "INVALID-ICD",  # Code non CIM-10
                "I10",  # Hypertension essentielle (valide)
            ],
            "icd10_display": [
                "Surveillance d'une première grossesse normale",
                "palu simple",  # Libellé clinique libre (RULE-CLIN-001)
                "Accouchement unique spontané",
                "Maladie indéterminée",
                "HTA stade 1",  # Abréviation (RULE-CLIN-001)
            ],
            "clinical_status": ["active", "active", "resolved", "active", "active"],
        }
    )


# ==============================================================================
# TIER 1 : Modèles, Schémas & Enums de Profilage (schemas.py)
# ==============================================================================


def test_tier1_quality_dimension_enum() -> None:
    """Vérifie la définition formelle de l'Enum QualityDimension avec les 6 dimensions normatives."""
    schemas = _require_schemas_module()

    QualityDimension = getattr(schemas, "QualityDimension", None)
    assert QualityDimension is not None, "Enum 'QualityDimension' manquante dans schemas.py"

    expected_dimensions = {
        "COMPLETENESS",
        "ACCURACY",
        "CONSISTENCY",
        "UNIQUENESS",
        "VALIDITY",
        "TIMELINESS",
    }
    present_names = {item.name for item in QualityDimension}
    assert expected_dimensions.issubset(present_names), (
        f"Dimensions manquantes dans QualityDimension. Attendu={expected_dimensions}, "
        f"Trouvé={present_names}"
    )

    # Vérification que les valeurs peuvent être converties en minuscules
    for dim in QualityDimension:
        assert isinstance(dim.value, str), f"La valeur de {dim} doit être une chaîne"


def test_tier1_column_metric_model() -> None:
    """Vérifie le modèle Pydantic ColumnMetric et ses attributs statistiques essentiels."""
    schemas = _require_schemas_module()

    ColumnMetric = getattr(schemas, "ColumnMetric", None)
    assert ColumnMetric is not None, "Modèle 'ColumnMetric' manquant dans schemas.py"

    metric = ColumnMetric(
        table_name="patients",
        column_name="birth_date",
        total_rows=100,
        null_count=10,
        null_ratio=0.10,
        sentinel_count=5,
        completeness_score=85.0,
    )

    assert metric.table_name == "patients"
    assert metric.column_name == "birth_date"
    assert metric.total_rows == 100
    assert metric.null_count == 10
    assert metric.null_ratio == pytest.approx(0.10, rel=1e-3)
    assert metric.sentinel_count == 5
    assert 0.0 <= metric.completeness_score <= 100.0

    # Sérialisation Pydantic v2
    data_dict = metric.model_dump() if hasattr(metric, "model_dump") else metric.dict()
    assert data_dict["column_name"] == "birth_date"
    assert "completeness_score" in data_dict


def test_tier1_dimension_score_model() -> None:
    """Vérifie le modèle DimensionScore pour le scoring d'une dimension qualité."""
    schemas = _require_schemas_module()

    DimensionScore = getattr(schemas, "DimensionScore", None)
    QualityDimension = schemas.QualityDimension
    assert DimensionScore is not None, "Modèle 'DimensionScore' manquant dans schemas.py"

    score_obj = DimensionScore(
        dimension=QualityDimension.COMPLETENESS,
        score=92.5,
        description="Complétude élevée avec quelques sentinelles résiduelles",
        issues_detected=15,
        details={"nulls_total": 8, "sentinels_total": 7},
    )

    assert score_obj.dimension in (QualityDimension.COMPLETENESS, "completeness", "COMPLETENESS")
    assert score_obj.score == pytest.approx(92.5, rel=1e-3)
    assert score_obj.issues_detected == 15
    assert isinstance(score_obj.details, dict)


def test_tier1_table_quality_summary_model() -> None:
    """Vérifie le modèle TableQualitySummary synthétisant la qualité d'une table."""
    schemas = _require_schemas_module()

    TableQualitySummary = getattr(schemas, "TableQualitySummary", None)
    QualityDimension = schemas.QualityDimension
    assert TableQualitySummary is not None, "Modèle 'TableQualitySummary' manquant dans schemas.py"

    summary = TableQualitySummary(
        table_name="patients",
        total_rows=1015,
        columns_count=10,
        dimension_scores={
            QualityDimension.COMPLETENESS: 88.0,
            QualityDimension.ACCURACY: 79.5,
            QualityDimension.CONSISTENCY: 98.0,
            QualityDimension.UNIQUENESS: 95.0,
            QualityDimension.VALIDITY: 85.0,
            QualityDimension.TIMELINESS: 92.0,
        },
        global_score=89.58,
    )

    assert summary.table_name == "patients"
    assert summary.total_rows == 1015
    assert summary.columns_count == 10
    assert 0.0 <= summary.global_score <= 100.0


def test_tier1_recall_metric_model() -> None:
    """Vérifie le modèle RecallMetric mesurant le taux de détection par règle d'altération."""
    schemas = _require_schemas_module()

    RecallMetric = getattr(schemas, "RecallMetric", None)
    assert RecallMetric is not None, "Modèle 'RecallMetric' manquant dans schemas.py"

    metric = RecallMetric(
        rule_id="RULE-DATE-001",
        rule_name="Formats de dates hétérogènes",
        target_table="patients",
        target_column="birth_date",
        total_injected=100,
        detected_count=88,
        recall=0.88,
        precision=0.92,
    )

    assert metric.rule_id == "RULE-DATE-001"
    assert metric.total_injected == 100
    assert metric.detected_count == 88
    # Supporte rappel en ratio (0.88) ou pourcentage (88.0)
    effective_recall = metric.recall if metric.recall <= 1.0 else metric.recall / 100.0
    assert effective_recall == pytest.approx(0.88, rel=1e-2)


def test_tier1_profiling_report_model() -> None:
    """Vérifie le modèle complet ProfilingReport et sa sérialisation JSON."""
    schemas = _require_schemas_module()

    ProfilingReport = getattr(schemas, "ProfilingReport", None)
    TableQualitySummary = schemas.TableQualitySummary
    QualityDimension = schemas.QualityDimension
    assert ProfilingReport is not None, "Modèle 'ProfilingReport' manquant dans schemas.py"

    report = ProfilingReport(
        report_id="rep-20261105-001",
        generated_at=datetime.now(UTC).isoformat(),
        overall_score=85.4,
        dimensions={
            QualityDimension.COMPLETENESS: 88.0,
            QualityDimension.ACCURACY: 80.0,
            QualityDimension.CONSISTENCY: 95.0,
            QualityDimension.UNIQUENESS: 90.0,
            QualityDimension.VALIDITY: 82.0,
            QualityDimension.TIMELINESS: 87.4,
        },
        tables={
            "patients": TableQualitySummary(
                table_name="patients",
                total_rows=10,
                columns_count=7,
                dimension_scores={QualityDimension.COMPLETENESS: 88.0},
                global_score=88.0,
            )
        },
        total_rows_analyzed=10,
        total_issues_detected=8,
    )

    dump_data = report.model_dump() if hasattr(report, "model_dump") else report.dict()
    assert dump_data["report_id"] == "rep-20261105-001"
    assert dump_data["overall_score"] == pytest.approx(85.4, rel=1e-3)
    assert "tables" in dump_data
    assert "dimensions" in dump_data


# ==============================================================================
# TIER 2 : Évaluateurs Dimensionnels Unitaires (dimensions.py)
# ==============================================================================


# --- 2.1 Complétude ---


def test_tier2_completeness_perfect_data(clean_patients_df: pd.DataFrame) -> None:
    """Vérifie que des données 100% renseignées obtiennent un score de complétude maximal."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_completeness(clean_patients_df, table_name="patients")
    # Score 100.0% (ou 1.0)
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct == pytest.approx(100.0, rel=1e-2)
    assert res.issues_detected == 0


def test_tier2_completeness_detects_nulls_and_nans() -> None:
    """Vérifie la détection rigoureuse des None, np.nan et pd.NA."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "col_a": ["val1", None, "val3", np.nan],
            "col_b": [1, 2, pd.NA, 4],
        }
    )
    res = dim_mod.evaluate_completeness(df, table_name="test_nulls")
    assert res.issues_detected >= 3, (
        f"Attendu au moins 3 valeurs nulles détectées, trouvé : {res.issues_detected}"
    )
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct < 100.0


def test_tier2_completeness_detects_empty_strings() -> None:
    """Vérifie la détection des chaînes vides et espaces comme anomalies de complétude."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "col_str": ["Koffi", "", "   ", "\t", "Mensah"],
        }
    )
    res = dim_mod.evaluate_completeness(df, table_name="test_empty")
    assert res.issues_detected >= 3, "Les chaînes vides et espaces doivent être comptabilisées"


def test_tier2_completeness_detects_sentinel_codes() -> None:
    """Vérifie la détection des codes sentinelles (-1, 999, -999, NA, ND, N/A, INCONNU)."""
    dim_mod = _require_dimensions_module()

    sentinels = ["-1", "999", "-999", "9999", "NA", "ND", "N/A", "INCONNU", "?"]
    df = pd.DataFrame(
        {
            "val_str": sentinels,
            "val_num": [-1, 999, -999, 9999, 0, 10, 20, 30, 40],
        }
    )
    res = dim_mod.evaluate_completeness(df, table_name="test_sentinels")
    assert res.issues_detected >= len(sentinels), (
        f"Les codes sentinelles doivent être détectés. Détecté: {res.issues_detected}"
    )


# --- 2.2 Exactitude ---


def test_tier2_accuracy_clean_data(clean_patients_df: pd.DataFrame) -> None:
    """Vérifie que des données conformes obtiennent un score d'exactitude élevé."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_accuracy(clean_patients_df, table_name="patients")
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct >= 95.0
    assert res.issues_detected == 0


def test_tier2_accuracy_detects_non_standard_dates() -> None:
    """Vérifie la détection des dates aux formats non-ISO (JJ/MM/AAAA, JJ-MM-AAAA, etc.)."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "birth_date": [
                "1985-04-12",  # ISO valide
                "15/04/1985",  # Non-standard JJ/MM/AAAA (RULE-DATE-001)
                "15-04-1985",  # Non-standard JJ-MM-AAAA
                "1985/04/15",  # Non-standard AAAA/MM/JJ
                "15.04.85",  # Non-standard JJ.MM.AA
            ]
        }
    )
    res = dim_mod.evaluate_accuracy(df, table_name="patients")
    assert res.issues_detected >= 4, (
        f"Attendu au moins 4 dates non standard détectées, trouvé : {res.issues_detected}"
    )


def test_tier2_accuracy_detects_approximate_ages() -> None:
    """Vérifie la détection des approximations textuelles d'âge dans les dates."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "birth_date": [
                "1985-04-12",
                "environ 35 ans",  # RULE-DATE-002
                "~22 ans",  # RULE-DATE-002
                "vers 40 ans",  # RULE-DATE-002
                "né vers 1980",  # RULE-DATE-002
            ]
        }
    )
    res = dim_mod.evaluate_accuracy(df, table_name="patients")
    assert res.issues_detected >= 4, "Les âges approximatifs doivent être détectés"


def test_tier2_accuracy_detects_mojibake_encoding() -> None:
    """Vérifie la détection des corruptions d'encodage Mojibake (UTF-8 mal décodé)."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "family_name": [
                "Tchagbélé",  # Valide
                "TchagbÃ©lÃ©",  # Mojibake Ã© (RULE-ENCO-001)
                "AnÃ©ho",  # Mojibake Ã©
                "HÃ´pital",  # Mojibake Ã´
            ]
        }
    )
    res = dim_mod.evaluate_accuracy(df, table_name="patients")
    assert res.issues_detected >= 3, "Les séquences Mojibake doivent être détectées"


def test_tier2_accuracy_detects_comma_decimal_separators() -> None:
    """Vérifie la détection des virgules décimales francophones au lieu du point."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "value_quantity": ["37.5", "38,5", "120", "135,2", "0,8"],
        }
    )
    res = dim_mod.evaluate_accuracy(df, table_name="observations")
    assert res.issues_detected >= 3, (
        "Les virgules décimales francophones doivent être détectées (RULE-MEAS-001)"
    )


# --- 2.3 Cohérence ---


def test_tier2_consistency_clean_data(clean_encounters_df: pd.DataFrame) -> None:
    """Vérifie qu'un jeu de consultations parfaitement cohérent valide à 100%."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_consistency(clean_encounters_df, table_name="encounters")
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct >= 95.0
    assert res.issues_detected == 0


def test_tier2_consistency_detects_male_pregnancy(conditions_df: pd.DataFrame) -> None:
    """Vérifie la détection d'incohérence clinique flagrante : grossesse chez un homme."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_consistency(conditions_df, table_name="conditions")
    assert res.issues_detected >= 1, (
        "La grossesse masculine (Z34.0 chez patient 'male') doit être signalée comme incohérence"
    )


def test_tier2_consistency_detects_temporal_inversion(
    degraded_encounters_df: pd.DataFrame,
) -> None:
    """Vérifie la détection des dates de début postérieures aux dates de fin."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_consistency(degraded_encounters_df, table_name="encounters")
    assert res.issues_detected >= 1, (
        "L'inversion start_date > end_date doit être signalée comme incohérence temporelle"
    )


def test_tier2_consistency_detects_pyramid_category_mismatch(
    degraded_encounters_df: pd.DataFrame,
) -> None:
    """Vérifie la détection de discordance entre niveau de pyramide et catégorie de structure."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_consistency(degraded_encounters_df, table_name="encounters")
    assert res.issues_detected >= 2, (
        "Les discordances catégorie vs niveau de pyramide doivent être détectées"
    )


# --- 2.4 Unicité ---


def test_tier2_uniqueness_clean_data(clean_patients_df: pd.DataFrame) -> None:
    """Vérifie qu'un DataFrame sans aucun doublon obtient un score d'unicité parfait."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_uniqueness(
        clean_patients_df, table_name="patients", primary_key="patient_id"
    )
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct == pytest.approx(100.0, rel=1e-2)
    assert res.issues_detected == 0


def test_tier2_uniqueness_detects_primary_key_duplicates(
    degraded_patients_df: pd.DataFrame,
) -> None:
    """Vérifie la détection des collisions de clés primaires sur la table patients."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_uniqueness(
        degraded_patients_df, table_name="patients", primary_key="patient_id"
    )
    assert res.issues_detected >= 1, "Le doublon de clé primaire 'PAT-0001' doit être détecté"
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct < 100.0


def test_tier2_uniqueness_detects_strict_row_duplicates() -> None:
    """Vérifie la détection des lignes strictement identiques redondantes."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2", "P1"],
            "name": ["Mensah", "Lawson", "Mensah"],
            "city": ["Lomé", "Kara", "Lomé"],
        }
    )
    res = dim_mod.evaluate_uniqueness(df, table_name="patients")
    assert res.issues_detected >= 1, "La ligne dupliquée doit être identifiée"


def test_tier2_uniqueness_detects_quasi_duplicate_patients() -> None:
    """Vérifie la détection des quasi-doublons de patients inter-établissements (RULE-DUPL-001)."""
    dim_mod = _require_dimensions_module()

    # Deux patients avec identifiants distincts mais même nom, prénom et date de naissance
    df = pd.DataFrame(
        {
            "patient_id": ["PAT-LOME-001", "PAT-KARA-002", "PAT-TSEV-003"],
            "family_name": ["Mensah", "Mensah", "Lawson"],
            "given_name": ["Koffi", "Kofi", "Afi"],
            "birth_date": ["1985-04-12", "1985-04-12", "1990-11-23"],
            "gender": ["male", "male", "female"],
        }
    )
    res = dim_mod.evaluate_uniqueness(df, table_name="patients", primary_key="patient_id")
    # Doit détecter la collision de clé ou le quasi-doublon patient
    assert res.issues_detected >= 1, (
        "Le quasi-doublon patient pour Splink doit être signalé dans l'évaluation d'unicité"
    )


# --- 2.5 Validité ---


def test_tier2_validity_clean_data(clean_patients_df: pd.DataFrame) -> None:
    """Vérifie qu'un jeu de données respectant tous les référentiels obtient un score de validité élevé."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_validity(clean_patients_df, table_name="patients")
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct >= 95.0


def test_tier2_validity_validates_icd10_codes(conditions_df: pd.DataFrame) -> None:
    """Vérifie la détection des codes CIM-10 invalides ou inconnus du référentiel."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_validity(
        conditions_df, table_name="conditions", vocabs_path=VOCABULARIES_PATH
    )
    assert res.issues_detected >= 1, (
        "Le code CIM-10 'INVALID-ICD' doit être détecté comme non conforme"
    )


def test_tier2_validity_validates_loinc_and_atc_codes(observations_df: pd.DataFrame) -> None:
    """Vérifie la détection des codes LOINC et unités de mesure non conformes."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_validity(
        observations_df, table_name="observations", vocabs_path=VOCABULARIES_PATH
    )
    assert res.issues_detected >= 1, (
        "Le code LOINC 'INVALID-LOINC' ou unité non conforme doit être détecté"
    )


def test_tier2_validity_validates_geography_districts_and_facilities(
    degraded_encounters_df: pd.DataFrame,
) -> None:
    """Vérifie la détection des codes districts et identifiants de formations inconnus."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_validity(
        degraded_encounters_df, table_name="encounters", geography_path=GEOGRAPHY_PATH
    )
    assert res.issues_detected >= 2, (
        "Les codes géographiques 'TG-INVALID-CODE' et formation invalide doivent être signalés"
    )


def test_tier2_validity_detects_non_ucum_units(observations_df: pd.DataFrame) -> None:
    """Vérifie la détection des unités non conformes au standard UCUM (°C, g/l, etc.)."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_validity(observations_df, table_name="observations")
    assert res.issues_detected >= 1, (
        "Les unités '°C' et 'deg C' doivent être identifiées comme non-UCUM (RULE-MEAS-002)"
    )


# --- 2.6 Actualité ---


def test_tier2_timeliness_clean_data(clean_patients_df: pd.DataFrame) -> None:
    """Vérifie que des dates réalistes contemporaines obtiennent un score d'actualité maximal."""
    dim_mod = _require_dimensions_module()

    res = dim_mod.evaluate_timeliness(clean_patients_df, table_name="patients")
    score_pct = res.score if res.score > 1.0 else res.score * 100.0
    assert score_pct >= 95.0
    assert res.issues_detected == 0


def test_tier2_timeliness_detects_future_dates() -> None:
    """Vérifie la détection des dates situées dans le futur."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "encounter_date": [
                "2023-01-15",
                "2045-06-20",  # Futur lointain
                "2099-12-31",  # Futur
                "2022-11-05",
            ]
        }
    )
    res = dim_mod.evaluate_timeliness(df, table_name="encounters")
    assert res.issues_detected >= 2, "Les dates dans le futur doivent être détectées"


def test_tier2_timeliness_detects_aberrant_historical_dates() -> None:
    """Vérifie la détection des dates historiques aberrantes antérieures à 1900."""
    dim_mod = _require_dimensions_module()

    df = pd.DataFrame(
        {
            "birth_date": [
                "1985-04-12",
                "1850-01-01",  # Date < 1900 aberrante
                "0001-01-01",  # Date corrompue
                "1990-11-23",
            ]
        }
    )
    res = dim_mod.evaluate_timeliness(df, table_name="patients")
    assert res.issues_detected >= 2, "Les dates antérieures à 1900 doivent être détectées"


# ==============================================================================
# TIER 3 : Moteur de Profilage Global (engine.py / QualityProfiler)
# ==============================================================================


def test_tier3_profiler_instantiation() -> None:
    """Vérifie l'instanciation de la classe QualityProfiler avec chemins de référentiels."""
    eng_mod = _require_engine_module()

    QualityProfiler = getattr(eng_mod, "QualityProfiler", None)
    assert QualityProfiler is not None, "Classe 'QualityProfiler' manquante dans engine.py"

    profiler = QualityProfiler(
        vocabs_path=VOCABULARIES_PATH if VOCABULARIES_PATH.exists() else None,
        geography_path=GEOGRAPHY_PATH if GEOGRAPHY_PATH.exists() else None,
    )
    assert profiler is not None


def test_tier3_profiler_profile_single_table(clean_patients_df: pd.DataFrame) -> None:
    """Vérifie le profilage d'une table unique et la production du TableQualitySummary."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler()
    summary = profiler.profile_table(clean_patients_df, table_name="patients")

    assert summary.table_name == "patients"
    assert summary.total_rows == len(clean_patients_df)
    assert summary.columns_count == len(clean_patients_df.columns)
    assert 0.0 <= summary.global_score <= 100.0
    assert len(summary.dimension_scores) >= 6, "Les 6 dimensions doivent être évaluées"


def test_tier3_profiler_profile_dataset(
    clean_patients_df: pd.DataFrame,
    clean_encounters_df: pd.DataFrame,
    conditions_df: pd.DataFrame,
    observations_df: pd.DataFrame,
) -> None:
    """Vérifie le profilage complet d'un jeu de plusieurs tables cliniques."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler(
        vocabs_path=VOCABULARIES_PATH if VOCABULARIES_PATH.exists() else None,
        geography_path=GEOGRAPHY_PATH if GEOGRAPHY_PATH.exists() else None,
    )
    dataset = {
        "patients": clean_patients_df,
        "encounters": clean_encounters_df,
        "conditions": conditions_df,
        "observations": observations_df,
    }

    report = profiler.profile_dataset(dataset)

    assert report.total_rows_analyzed == sum(len(df) for df in dataset.values())
    assert len(report.tables) == len(dataset)
    assert 0.0 <= report.overall_score <= 100.0
    assert len(report.dimensions) >= 6


def test_tier3_profiler_profile_directory_parquet(tmp_path: Path) -> None:
    """Vérifie que profile_directory charge et profile un répertoire contenant des Parquet."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    # Écriture de 2 tables Parquet temporaires
    df_p = pd.DataFrame({"patient_id": ["P1", "P2"], "gender": ["male", "female"]})
    df_e = pd.DataFrame({"encounter_id": ["E1", "E2"], "patient_id": ["P1", "P2"]})
    df_p.to_parquet(tmp_path / "patients.parquet")
    df_e.to_parquet(tmp_path / "encounters.parquet")

    profiler = QualityProfiler()
    report = profiler.profile_directory(tmp_path)

    assert "patients" in report.tables
    assert "encounters" in report.tables
    assert report.total_rows_analyzed == 4


def test_tier3_profiler_calculates_global_score(
    clean_patients_df: pd.DataFrame,
    degraded_patients_df: pd.DataFrame,
) -> None:
    """Vérifie que le score global de la table dégradée est strictement inférieur à la table propre."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler()
    clean_summary = profiler.profile_table(clean_patients_df, "patients")
    degraded_summary = profiler.profile_table(degraded_patients_df, "patients")

    assert clean_summary.global_score > degraded_summary.global_score, (
        f"Le score global doit refléter la dégradation. Clean={clean_summary.global_score}, "
        f"Degraded={degraded_summary.global_score}"
    )


def test_tier3_profiler_determinism(degraded_patients_df: pd.DataFrame) -> None:
    """Garantit l'idempotence et le déterminisme strict du profilage (AGENT.md #3)."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler()
    res1 = profiler.profile_table(degraded_patients_df, "patients")
    res2 = profiler.profile_table(degraded_patients_df, "patients")

    assert res1.global_score == res2.global_score
    for dim_key in res1.dimension_scores:
        assert res1.dimension_scores[dim_key] == res2.dimension_scores[dim_key]


def test_tier3_profiler_handles_empty_dataframe() -> None:
    """Vérifie la robustesse aux tables vides (0 ligne) sans lever d'exception."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler()
    empty_df = pd.DataFrame(columns=["patient_id", "family_name", "birth_date"])
    summary = profiler.profile_table(empty_df, "patients_empty")

    assert summary.total_rows == 0
    assert summary.table_name == "patients_empty"
    assert 0.0 <= summary.global_score <= 100.0


def test_tier3_profiler_handles_single_column_dataframe() -> None:
    """Vérifie la robustesse aux tables mono-colonne."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler()
    single_col_df = pd.DataFrame({"id": ["A", "B", "C"]})
    summary = profiler.profile_table(single_col_df, "mono_col")

    assert summary.columns_count == 1
    assert summary.total_rows == 3


def test_tier3_profiler_handles_all_null_column() -> None:
    """Vérifie qu'une colonne 100% nulle ne provoque pas de division par zéro."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler()
    null_col_df = pd.DataFrame({"empty_col": [None, None, np.nan]})
    summary = profiler.profile_table(null_col_df, "all_null")

    assert summary.total_rows == 3


def test_tier3_profiler_ignores_audit_columns_in_business_dimensions() -> None:
    """Vérifie que les 4 métadonnées d'audit (AGENT.md #2) ne faussent pas la validité métier."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2"],
            "gender": ["male", "female"],
            # Colonnes d'audit obligatoires
            "source_file": ["extract.csv", "extract.csv"],
            "source_row": [1, 2],
            "ingested_at": ["2026-11-05T20:00:00Z", "2026-11-05T20:00:00Z"],
            "content_hash": [
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ],
        }
    )
    profiler = QualityProfiler()
    summary = profiler.profile_table(df, "patients")
    # L'audit ne doit pas faire chuter la validité
    assert summary.global_score >= 80.0


# ==============================================================================
# TIER 4 : Confrontation au Corrigé d'Altérations (compare_with_alterations_log)
# ==============================================================================


def test_tier4_load_alterations_log() -> None:
    """Vérifie la validité du journal d'altérations data/degraded/alterations_log.parquet."""
    if not ALTERATIONS_LOG_PATH.exists():
        pytest.skip(f"Fichier requis {ALTERATIONS_LOG_PATH} introuvable")

    df_log = pd.read_parquet(ALTERATIONS_LOG_PATH)
    assert len(df_log) > 0, "Le journal d'altérations ne doit pas être vide"
    expected_cols = {"alteration_id", "table_name", "column_name", "rule_id"}
    assert expected_cols.issubset(set(df_log.columns)), (
        f"Colonnes manquantes dans {ALTERATIONS_LOG_PATH}"
    )


def test_tier4_confrontation_calculates_metrics_per_rule(tmp_path: Path) -> None:
    """Vérifie le calcul des métriques de détection et du rappel par règle d'altération."""
    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    # Création d'un journal d'altérations synthétique
    log_df = pd.DataFrame(
        {
            "alteration_id": ["alt-1", "alt-2", "alt-3", "alt-4"],
            "table_name": ["patients", "patients", "observations", "observations"],
            "row_id": ["PAT-0002", "PAT-0003", "OBS-0003", "OBS-0004"],
            "column_name": ["birth_date", "birth_date", "value_quantity", "value_quantity"],
            "rule_id": [
                "RULE-DATE-001",
                "RULE-DATE-002",
                "RULE-MEAS-001",
                "RULE-SENT-001",
            ],
            "description": ["Date non-standard", "Age approx", "Virgule", "Sentinelle"],
        }
    )
    log_file = tmp_path / "test_alterations_log.parquet"
    log_df.to_parquet(log_file)

    profiler = QualityProfiler()
    test_tables = {
        "patients": pd.DataFrame(
            {
                "patient_id": ["PAT-0001", "PAT-0002", "PAT-0003"],
                "birth_date": ["1985-04-12", "15/04/1985", "environ 40 ans"],
            }
        ),
        "observations": pd.DataFrame(
            {
                "observation_id": ["OBS-0001", "OBS-0003", "OBS-0004"],
                "value_quantity": ["37.2", "38,5", "999"],
            }
        ),
    }

    recall_metrics = profiler.compare_with_alterations_log(test_tables, log_file)

    assert len(recall_metrics) > 0, "Doit retourner une liste de métriques de rappel par règle"
    rule_ids = {m.rule_id for m in recall_metrics}
    assert "RULE-DATE-001" in rule_ids or "RULE-MEAS-001" in rule_ids

    for m in recall_metrics:
        eff_recall = m.recall if m.recall <= 1.0 else m.recall / 100.0
        assert 0.0 <= eff_recall <= 1.0
        assert m.detected_count <= m.total_injected


def test_tier4_confrontation_zero_anomalies_on_truth_data() -> None:
    """Vérifie que les données de vérité terrain (data/truth/) ne signalent pas faussement les altérations."""
    if not DATA_TRUTH_DIR.exists() or not (DATA_TRUTH_DIR / "patients.parquet").exists():
        pytest.skip(f"Dossier vérité terrain {DATA_TRUTH_DIR} non trouvé")

    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    truth_patients = pd.read_parquet(DATA_TRUTH_DIR / "patients.parquet")
    profiler = QualityProfiler()
    summary = profiler.profile_table(truth_patients, "patients")

    # La vérité terrain doit avoir un score d'exactitude et complétude très élevé (> 90%)
    score = summary.global_score
    assert score >= 90.0, f"Le jeu vérité terrain doit avoir un score élevé. Score={score}"


def test_tier4_confrontation_e2e_degraded_dataset_overall_recall() -> None:
    """Test E2E Majeur : Vérifie que le rappel global de détection atteint >= 80% sur data/degraded/."""
    if not DATA_DEGRADED_DIR.exists() or not ALTERATIONS_LOG_PATH.exists():
        pytest.skip("Données dégradées ou journal d'altérations introuvables pour test E2E")

    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler(
        vocabs_path=VOCABULARIES_PATH if VOCABULARIES_PATH.exists() else None,
        geography_path=GEOGRAPHY_PATH if GEOGRAPHY_PATH.exists() else None,
    )

    # Chargement des tables dégradées existantes
    degraded_tables: dict[str, pd.DataFrame] = {}
    for table_name in CLINICAL_TABLES:
        table_path = DATA_DEGRADED_DIR / f"{table_name}.parquet"
        if table_path.exists():
            degraded_tables[table_name] = pd.read_parquet(table_path)

    assert len(degraded_tables) >= 4, "Au moins 4 tables dégradées requises pour l'évaluation E2E"

    recall_metrics = profiler.compare_with_alterations_log(degraded_tables, ALTERATIONS_LOG_PATH)
    assert len(recall_metrics) > 0, "La liste des métriques de rappel ne doit pas être vide"

    total_injected = sum(m.total_injected for m in recall_metrics)
    total_detected = sum(m.detected_count for m in recall_metrics)

    assert total_injected > 0, "Le total d'altérations injectées doit être supérieur à 0"
    overall_recall = total_detected / total_injected

    # Cible normative du projet (SCOPE.md §1.2 & DISPATCH.md) : Rappel >= 80% (0.80)
    assert overall_recall >= 0.80, (
        f"Le rappel global de détection face au corrigé doit être >= 80%. "
        f"Obtenu : {overall_recall * 100.2:.1f}% ({total_detected}/{total_injected})"
    )


def test_tier4_confrontation_high_recall_on_critical_rules() -> None:
    """Vérifie que les règles critiques (dates, sentinelles, virgules, mojibake) ont un rappel élevé."""
    if not DATA_DEGRADED_DIR.exists() or not ALTERATIONS_LOG_PATH.exists():
        pytest.skip("Données dégradées non disponibles pour ce test")

    eng_mod = _require_engine_module()
    QualityProfiler = eng_mod.QualityProfiler

    profiler = QualityProfiler(
        vocabs_path=VOCABULARIES_PATH if VOCABULARIES_PATH.exists() else None,
        geography_path=GEOGRAPHY_PATH if GEOGRAPHY_PATH.exists() else None,
    )

    degraded_tables: dict[str, pd.DataFrame] = {}
    for table_name in CLINICAL_TABLES:
        table_path = DATA_DEGRADED_DIR / f"{table_name}.parquet"
        if table_path.exists():
            degraded_tables[table_name] = pd.read_parquet(table_path)

    metrics = profiler.compare_with_alterations_log(degraded_tables, ALTERATIONS_LOG_PATH)
    metrics_by_rule = {m.rule_id: m for m in metrics}

    # Règles critiques à haute détectabilité
    critical_rules = ["RULE-DATE-001", "RULE-SENT-001", "RULE-MEAS-001", "RULE-ENCO-001"]
    for rule_id in critical_rules:
        if rule_id in metrics_by_rule:
            m = metrics_by_rule[rule_id]
            eff_recall = m.recall if m.recall <= 1.0 else m.recall / 100.0
            assert eff_recall >= 0.75, (
                f"Règle critique {rule_id} sous le seuil attendu de 75% : {eff_recall * 100:.1f}%"
            )


# ==============================================================================
# TIER 5 : Générateur de Rapports (Markdown & JSON) (reporter.py)
# ==============================================================================


@pytest.fixture
def sample_profiling_report() -> Any:
    """Fixture d'un rapport de profilage représentatif pour les tests d'export."""
    schemas = _require_schemas_module()

    ProfilingReport = schemas.ProfilingReport
    TableQualitySummary = schemas.TableQualitySummary
    QualityDimension = schemas.QualityDimension
    RecallMetric = schemas.RecallMetric

    dim_scores = {
        QualityDimension.COMPLETENESS: 85.5,
        QualityDimension.ACCURACY: 78.0,
        QualityDimension.CONSISTENCY: 94.2,
        QualityDimension.UNIQUENESS: 91.0,
        QualityDimension.VALIDITY: 82.5,
        QualityDimension.TIMELINESS: 89.0,
    }

    patients_summary = TableQualitySummary(
        table_name="patients",
        total_rows=1015,
        columns_count=10,
        dimension_scores=dim_scores,
        global_score=86.7,
    )

    recalls = [
        RecallMetric(
            rule_id="RULE-DATE-001",
            rule_name="Formats de dates hétérogènes",
            target_table="patients",
            target_column="birth_date",
            total_injected=150,
            detected_count=138,
            recall=0.92,
            precision=0.95,
        ),
        RecallMetric(
            rule_id="RULE-MEAS-001",
            rule_name="Virgules décimales francophones",
            target_table="observations",
            target_column="value_quantity",
            total_injected=80,
            detected_count=75,
            recall=0.9375,
            precision=0.98,
        ),
    ]

    return ProfilingReport(
        report_id="rep-sample-001",
        generated_at=datetime.now(UTC).isoformat(),
        overall_score=86.7,
        dimensions=dim_scores,
        tables={"patients": patients_summary},
        total_rows_analyzed=1015,
        total_issues_detected=213,
        recall_metrics=recalls,
        summary_notes=["Profilage initial de la couche Bronze avant normalisation Silver."],
    )


def test_tier5_generate_markdown_report_structure(
    sample_profiling_report: Any, tmp_path: Path
) -> None:
    """Vérifie la génération du rapport Markdown et la présence de toutes les sections requises."""
    rep_mod = _require_reporter_module()

    generate_md_fn = getattr(rep_mod, "generate_markdown_report", None)
    assert generate_md_fn is not None, (
        "Fonction 'generate_markdown_report' manquante dans reporter.py"
    )

    out_file = tmp_path / "profiling_bronze.md"
    result_path = generate_md_fn(sample_profiling_report, out_file)

    assert Path(result_path).exists(), f"Le fichier {out_file} n'a pas été produit"
    content = Path(result_path).read_text(encoding="utf-8")

    # 1. En-tête et Titre
    content_lower = content.lower()
    assert "rapport" in content_lower and (
        "qualité" in content_lower or "diagnostic" in content_lower or "bronze" in content_lower
    ), "Le titre du rapport Markdown doit être explicite en français"

    # 2. Synthèse exécutive et Score global
    assert (
        "synthèse" in content_lower
        or "exécutiv" in content_lower
        or "score global" in content_lower
    ), "La synthèse exécutive doit figurer dans le rapport"

    # 3. Tableau récapitulatif des 6 dimensions
    for dim_name in [
        "complétude",
        "exactitude",
        "cohérence",
        "unicité",
        "validité",
        "actualité",
    ]:
        assert dim_name in content_lower, (
            f"La dimension '{dim_name}' doit figurer dans le tableau récapitulatif Markdown"
        )

    # 4. Détail par table
    assert "patients" in content, "La table 'patients' doit être détaillée dans le rapport"

    # 5. Matrice de rappel face au corrigé
    assert "rule-date-001" in content_lower or "rappel" in content_lower, (
        "La matrice de rappel par règle doit figurer dans le rapport"
    )

    # 6. Recommandations pour l'Étape 7 (Nettoyage Silver)
    assert (
        "recommandation" in content_lower
        or "silver" in content_lower
        or "étape 7" in content_lower
        or "action" in content_lower
    ), "Les recommandations pour l'Étape 7 doivent figurer dans le rapport"


def test_tier5_generate_json_report_structure(sample_profiling_report: Any, tmp_path: Path) -> None:
    """Vérifie la génération du rapport JSON structuré machine-readable."""
    rep_mod = _require_reporter_module()

    generate_json_fn = getattr(rep_mod, "generate_json_report", None)
    assert generate_json_fn is not None, (
        "Fonction 'generate_json_report' manquante dans reporter.py"
    )

    out_file = tmp_path / "profiling_bronze.json"
    result_path = generate_json_fn(sample_profiling_report, out_file)

    assert Path(result_path).exists(), f"Le fichier {out_file} n'a pas été produit"
    raw_content = Path(result_path).read_text(encoding="utf-8")
    data = json.loads(raw_content)

    assert "report_id" in data
    assert "overall_score" in data
    assert "dimensions" in data
    assert "tables" in data
    assert "patients" in data["tables"]
    assert "recall_metrics" in data
    assert len(data["recall_metrics"]) >= 2


def test_tier5_reporter_handles_report_without_alterations(tmp_path: Path) -> None:
    """Vérifie la génération propre du rapport même lorsqu'aucun journal d'altérations n'est fourni."""
    schemas = _require_schemas_module()
    rep_mod = _require_reporter_module()

    ProfilingReport = schemas.ProfilingReport
    TableQualitySummary = schemas.TableQualitySummary
    QualityDimension = schemas.QualityDimension

    report_without_recall = ProfilingReport(
        report_id="rep-no-recall",
        generated_at=datetime.now(UTC).isoformat(),
        overall_score=90.0,
        dimensions={QualityDimension.COMPLETENESS: 90.0},
        tables={
            "patients": TableQualitySummary(
                table_name="patients",
                total_rows=10,
                columns_count=3,
                dimension_scores={QualityDimension.COMPLETENESS: 90.0},
                global_score=90.0,
            )
        },
        recall_metrics=None,
    )

    out_md = tmp_path / "report_no_recall.md"
    out_json = tmp_path / "report_no_recall.json"

    rep_mod.generate_markdown_report(report_without_recall, out_md)
    rep_mod.generate_json_report(report_without_recall, out_json)

    assert out_md.exists()
    assert out_json.exists()
