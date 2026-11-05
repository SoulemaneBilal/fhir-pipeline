"""Tests E2E de validation des vocabulaires terminologiques et pathologies prioritaires (Étape 2).

Conforme aux spécifications R3 d'ORIGINAL_REQUEST.md, PROJECT.md, ADR D-09 et VAL-002.
Couvre les Tiers 1 à 4 :
- Tier 1 : Schéma Parquet, présence des 9 pathologies prioritaires et des 4 vocabulaires cibles.
- Tier 2 : Vérification stricte de la taille de fichier (< 1 000 000 octets, ADR D-09), non-vacuité des codes.
- Tier 3 : Couverture exhaustive des constantes vitales LOINC et des médicaments essentiels ATC.
- Tier 4 : Performance de recherche hors-ligne (< 20ms), robustesse du validateur sur données corrompues.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import pytest

VOCAB_PARQUET_PATH = Path("terminology/sample_vocabularies.parquet")
MODULE_PATH = Path("src/terminology/pathologies.py")
IS_STRICT = os.environ.get("STRICT_E2E") == "1"

# Les 9 pathologies prioritaires du Togo (VAL-002, PROJECT.md)
EXPECTED_PATHOLOGY_GROUPS: set[str] = {
    "Malaria",
    "ARI",
    "Diarrhea",
    "HIV",
    "TB",
    "HTA",
    "Diabetes",
    "SMI",
    "Malnutrition",
}

# 4 Vocabulaires cibles obligatoires
EXPECTED_VOCABULARIES: set[str] = {"ICD10", "SNOMED", "LOINC", "ATC"}


def _check_parquet_exists() -> bool:
    if not VOCAB_PARQUET_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Fichier Parquet obligatoire manquant : {VOCAB_PARQUET_PATH}")
        pytest.skip(f"Fichier {VOCAB_PARQUET_PATH} non encore généré (Jalon M3 en attente)")
    return True


@pytest.fixture
def vocab_df() -> pd.DataFrame:
    """Charge le fichier Parquet des vocabulaires mock."""
    _check_parquet_exists()
    df = pd.read_parquet(VOCAB_PARQUET_PATH)
    assert not df.empty, f"Le fichier Parquet {VOCAB_PARQUET_PATH} est vide"
    return df


@pytest.fixture
def pathologies_module():
    """Importe le module src.terminology.pathologies si disponible."""
    if not MODULE_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Module obligatoire manquant : {MODULE_PATH}")
        pytest.skip(f"Module {MODULE_PATH} non encore implémenté (Jalon M3 en attente)")
    try:
        import src.terminology.pathologies as pathol

        return pathol
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Erreur d'import de {MODULE_PATH} : {exc}")
        pytest.skip(f"Import {MODULE_PATH} impossible : {exc}")


# ==============================================================================
# Tier 1 : Couverture des fonctionnalités (Schéma, 9 Pathologies, 4 Vocabulaires)
# ==============================================================================


def test_tier1_vocabularies_schema(vocab_df: pd.DataFrame) -> None:
    """Vérifie la conformité du schéma de la table sample_vocabularies."""
    required_columns = {
        "concept_name",
        "domain_id",
        "vocabulary_id",
        "concept_code",
        "pathology_group",
    }
    present_cols = set(vocab_df.columns)
    missing = required_columns - present_cols
    assert not missing, f"Colonnes obligatoires manquantes dans sample_vocabularies : {missing}"

    # Vérifie la présence d'une colonne ID (concept_id ou omop_concept_id)
    assert "concept_id" in present_cols or "omop_concept_id" in present_cols, (
        "Colonne d'identifiant concept (concept_id ou omop_concept_id) manquante"
    )


def test_tier1_nine_priority_pathologies_presence(
    vocab_df: pd.DataFrame,
) -> None:
    """Vérifie que les 9 pathologies prioritaires togolaises sont toutes représentées."""
    present_groups = set(vocab_df["pathology_group"].str.strip().unique())
    # Normalisation pour tolérer minuscules ou majuscules
    present_groups_upper = {g.upper() for g in present_groups}
    for expected in EXPECTED_PATHOLOGY_GROUPS:
        assert expected.upper() in present_groups_upper, (
            f"Pathologie prioritaire manquante : {expected}. Présentes : {present_groups}"
        )


def test_tier1_four_standard_vocabularies_presence(
    vocab_df: pd.DataFrame,
) -> None:
    """Vérifie la présence des 4 vocabulaires pivots : ICD-10, SNOMED, LOINC, ATC."""
    present_vocabs = set(vocab_df["vocabulary_id"].str.strip().unique())
    # Normalisation : tolérer 'ICD10' / 'ICD-10', 'SNOMED' / 'SNOMED CT'
    norm_vocabs = {v.replace("-", "").replace(" ", "").upper() for v in present_vocabs}
    for expected in {"ICD10", "SNOMED", "LOINC", "ATC"}:
        matched = any(expected in v for v in norm_vocabs)
        assert matched, (
            f"Vocabulaire standard obligatoire manquant : {expected}. Présents : {present_vocabs}"
        )


# ==============================================================================
# Tier 2 : Cas Limites et Contrainte de Poids (< 1 Mo, ADR D-09)
# ==============================================================================


def test_tier2_file_size_strictly_under_one_megabyte() -> None:
    """Vérifie formellement que le fichier Parquet pèse strictement moins de 1 Mo (ADR D-09)."""
    _check_parquet_exists()
    file_size_bytes = os.path.getsize(VOCAB_PARQUET_PATH)
    limit_bytes = 1_000_000  # 1 Mo = 1 000 000 octets
    assert file_size_bytes < limit_bytes, (
        f"VIOLATION ADR D-09 : la taille du mock terminologique ({file_size_bytes} octets) "
        f"dépasse la limite stricte de {limit_bytes} octets"
    )
    # Vérification bonus : le fichier ne doit pas non plus être vide
    assert file_size_bytes > 1_000, f"Taille anormalement faible ({file_size_bytes} octets)"


def test_tier2_non_empty_codes_and_names(vocab_df: pd.DataFrame) -> None:
    """Vérifie qu'aucun code concept ni nom de concept n'est vide ou nul."""
    for col in ["concept_code", "concept_name", "vocabulary_id"]:
        null_count = vocab_df[col].isnull().sum()
        assert null_count == 0, f"La colonne {col} contient {null_count} valeurs nulles"
        empty_count = (vocab_df[col].astype(str).str.strip() == "").sum()
        assert empty_count == 0, f"La colonne {col} contient {empty_count} chaînes vides"


def test_tier2_domain_assignments(vocab_df: pd.DataFrame) -> None:
    """Vérifie que chaque concept appartient à un domaine OMOP valide."""
    valid_domains = {
        "Condition",
        "Measurement",
        "Observation",
        "Drug",
        "Procedure",
    }
    present_domains = set(vocab_df["domain_id"].unique())
    invalid_domains = present_domains - valid_domains
    assert not invalid_domains, f"Domaines OMOP non reconnus dans le mock : {invalid_domains}"


# ==============================================================================
# Tier 3 : Intégrité Transverse et Mappings Cliniques Cibles
# ==============================================================================


def test_tier3_vital_signs_loinc_coverage(vocab_df: pd.DataFrame) -> None:
    """Vérifie que les constantes vitales clés sont couvertes par LOINC."""
    loinc_df = vocab_df[vocab_df["vocabulary_id"].str.contains("LOINC", case=False)]
    assert not loinc_df.empty, "Aucun concept LOINC trouvé dans sample_vocabularies"

    loinc_codes = set(loinc_df["concept_code"].str.strip())

    # 1. Pression artérielle systolique (8480-6)
    assert "8480-6" in loinc_codes, "LOINC 8480-6 (Pression systolique) manquant"
    # 2. Pression artérielle diastolique (8462-4)
    assert "8462-4" in loinc_codes, "LOINC 8462-4 (Pression diastolique) manquant"
    # 3. Température corporelle (8310-5)
    assert "8310-5" in loinc_codes, "LOINC 8310-5 (Température) manquant"
    # 4. Poids corporel (29463-7)
    assert "29463-7" in loinc_codes, "LOINC 29463-7 (Poids) manquant"
    # 5. Glycémie (1558-6 ou 2345-7 ou 2339-0)
    has_glycemia = any(c in loinc_codes for c in ("1558-6", "2345-7", "2339-0"))
    assert has_glycemia, (
        f"Code glycémie LOINC manquant (attendu 1558-6 ou 2345-7). Présents : {loinc_codes}"
    )
    # 6. Périmètre brachial / MUAC (89270-3 ou 56072-2)
    has_muac = any(c in loinc_codes for c in ("89270-3", "56072-2"))
    assert has_muac, (
        f"Code MUAC / Périmètre brachial manquant pour la malnutrition. Présents : {loinc_codes}"
    )


def test_tier3_essential_drugs_atc_coverage(vocab_df: pd.DataFrame) -> None:
    """Vérifie que les médicaments prioritaires du Togo sont couverts par l'ATC."""
    atc_df = vocab_df[vocab_df["vocabulary_id"].str.contains("ATC", case=False)]
    assert not atc_df.empty, "Aucun concept ATC trouvé dans sample_vocabularies"

    atc_codes = set(atc_df["concept_code"].str.strip())

    # 1. Paludisme : Artemether/Lumefantrine (P01BF01) ou Artesunate (P01BE03)
    has_malaria_drug = any(c in atc_codes for c in ("P01BF01", "P01BE03", "P01BD51"))
    assert has_malaria_drug, (
        f"Médicament antipaludique ATC (ex. P01BF01) manquant. Présents : {atc_codes}"
    )

    # 2. VIH : TLD (Tenofovir/Lamivudine/Dolutegravir J05AR13) ou Dolutegravir (J05AJ03)
    has_hiv_drug = any(c in atc_codes for c in ("J05AR13", "J05AJ03", "J05AR03"))
    assert has_hiv_drug, f"Traitement ARV VIH ATC (ex. J05AR13) manquant. Présents : {atc_codes}"

    # 3. Tuberculose : RHZE (J04AM06 ou J04AK02 ou J04AC01)
    has_tb_drug = any(c in atc_codes for c in ("J04AM06", "J04AK02", "J04AC01", "J04AB02"))
    assert has_tb_drug, f"Traitement anti-TB ATC (ex. J04AM06) manquant. Présents : {atc_codes}"

    # 4. Diarrhée : SRO (A07CA) ou Zinc (A12CB01)
    has_diarrhea_drug = any(c in atc_codes for c in ("A07CA", "A12CB01"))
    assert has_diarrhea_drug, (
        f"Traitement réhydratation / zinc ATC (A07CA) manquant. Présents : {atc_codes}"
    )

    # 5. HTA : Amlodipine (C08CA01) ou Énalapril (C09AA02) ou Losartan (C09CA01)
    has_hta_drug = any(c in atc_codes for c in ("C08CA01", "C09AA02", "C09CA01", "C03AA03"))
    assert has_hta_drug, (
        f"Traitement antihypertenseur ATC (ex. C08CA01) manquant. Présents : {atc_codes}"
    )

    # 6. Diabète : Metformine (A10BA02) ou Glibenclamide (A10BB01)
    has_diabetes_drug = any(c in atc_codes for c in ("A10BA02", "A10BB01", "A10AE04"))
    assert has_diabetes_drug, (
        f"Antidiabétique oral ATC (ex. A10BA02) manquant. Présents : {atc_codes}"
    )


def test_tier3_pathology_catalog_in_module(pathologies_module) -> None:
    """Vérifie que la fonction get_priority_pathologies expose bien les 9 pathologies."""
    if not hasattr(pathologies_module, "get_priority_pathologies"):
        pytest.skip("Fonction get_priority_pathologies manquante dans le module")

    catalog = pathologies_module.get_priority_pathologies()
    assert isinstance(catalog, dict), "Le catalogue doit être un dictionnaire"
    assert len(catalog) >= 9, (
        f"Le catalogue doit contenir au moins 9 pathologies (trouvé {len(catalog)})"
    )


# ==============================================================================
# Tier 4 : Performance & Validation Hors-Ligne
# ==============================================================================


def test_tier4_offline_lookup_performance(vocab_df: pd.DataFrame) -> None:
    """Vérifie que la recherche locale dans le mock Parquet s'effectue en moins de 20ms."""
    start = time.perf_counter()

    # 1. Recherche par code concept
    res_code = vocab_df[vocab_df["concept_code"] == "8480-6"]
    # 2. Recherche par groupe pathologique
    res_malaria = vocab_df[vocab_df["pathology_group"].str.lower() == "malaria"]
    # 3. Recherche par vocabulaire
    res_atc = vocab_df[vocab_df["vocabulary_id"] == "ATC"]

    elapsed = time.perf_counter() - start

    assert elapsed < 0.02, f"Recherche hors-ligne trop lente : {elapsed * 1000:.2f}ms >= 20ms"
    assert not res_code.empty, "Recherche par code 8480-6 a échoué"
    assert not res_malaria.empty, "Recherche pathologie Malaria a échoué"
    assert not res_atc.empty, "Recherche vocabulaire ATC a échoué"


def test_tier4_adversarial_vocabularies_validator(pathologies_module) -> None:
    """Test adversarial : vérifie que le validateur du module rejette des vocabulaires non conformes."""
    if not hasattr(pathologies_module, "validate_sample_vocabularies"):
        pytest.skip("Fonction validate_sample_vocabularies non présente dans le module")

    # Donnée corrompue : absence d'un vocabulaire pivot et codes vides
    corrupt_df = pd.DataFrame(
        [
            {
                "concept_id": 1,
                "concept_name": "Test Invalide",
                "domain_id": "Condition",
                "vocabulary_id": "UNKNOWN_VOCAB",  # Vocabulaire non standard
                "concept_code": "",  # Code vide interdit
                "pathology_group": "Malaria",
            }
        ]
    )

    errors = pathologies_module.validate_sample_vocabularies(corrupt_df)
    assert len(errors) > 0, (
        "Le validateur aurait dû signaler des erreurs sur les vocabulaires inconnus ou codes vides"
    )
