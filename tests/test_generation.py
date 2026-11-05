"""Tests E2E et de validation unitaire du moteur de génération de Vérité Terrain et agrégats DHIS2 (Étape 3).

Conforme aux spécifications formelles d'ORIGINAL_REQUEST.md (R1, R2, R4), SCOPE.md,
ADR D-04 (Générateur contextuel Python), ADR D-08 (Territoire sanitaire),
ADR D-09 (Vocabulaires mock < 1 Mo), VAL-002 (Pathologies prioritaires) et VAL-003 (Âges estimés).

Structure en 4 Tiers :
- Tier 1 : Couverture des fonctionnalités
  - Génération des 6 tables cliniques Parquet (patients, encounters, conditions, observations, prescriptions, immunizations).
  - Génération des agrégats DHIS2 (JSON dataValueSets et Parquet tabulaire).
  - Non-vacuité et validité RFC 4122 des clés primaires (UUID v5).
  - Intégrité référentielle stricte (clés étrangères sans orphelins).
  - Présence et types stricts de toutes les colonnes requises.
- Tier 2 : Cas limites et intégrité clinique
  - Cohortes aux bornes : count=1 (minimale sans division par zéro), count=50, count=0/négatif (rejeté).
  - Mécanisme de repli hors-ligne (offline fallback) DHIS2 avec URL invalide/injoignable.
  - Règles d'intégrité clinique :
    * Zéro patient masculin avec grossesse/accouchement (CIM-10 Z34, O80, O82).
    * Zéro adulte avec vaccins pédiatriques du PEV Togo (< 5 ans).
    * Pathologies chroniques (HTA, Diabète) réservées aux adultes (zéro chez nourrissons).
    * VAL-003 : Date de naissance au 1er juillet (-07-01) et age_precision='approximate-year' pour estimated_age_flag=True.
- Tier 3 : Déterminisme strict
  - Reproductibilité binaire bit-à-bit (SHA-256 identiques et DataFrames égaux pour seed identique).
  - Divergence garantie entre graines distinctes (seed=42 vs seed=43).
  - Déterminisme des agrégats DHIS2 hors ligne.
- Tier 4 : Adhérence 100% aux référentiels réels
  - 100% des établissements, districts et régions concordent avec togo_health_geography.parquet.
  - 100% des codes CIM-10, SNOMED CT, LOINC et ATC concordent avec sample_vocabularies.parquet.
  - Distribution de la pyramide sanitaire (majorité en niveau 1 CMS/USP, traçabilité des transferts).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

IS_STRICT = os.environ.get("STRICT_E2E") == "1"

# Chemins des référentiels d'autorité (Étape 2)
GEOGRAPHY_PARQUET_PATH = Path("data/reference/togo_health_geography.parquet")
VOCAB_PARQUET_PATH = Path("terminology/sample_vocabularies.parquet")

# Chemins des modules attendus pour l'Étape 3
GENERATOR_MODULE_PATH = Path("src/generation/contextual_generator.py")
DHIS2_MODULE_PATH = Path("src/generation/dhis2_generator.py")

# Les 6 fichiers Parquet cliniques attendus dans data/truth/
EXPECTED_CLINICAL_FILES = [
    "patients.parquet",
    "encounters.parquet",
    "conditions.parquet",
    "observations.parquet",
    "prescriptions.parquet",
    "immunizations.parquet",
]

# Les 9 pathologies prioritaires du Togo (VAL-002)
PRIORITY_PATHOLOGIES = {
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


# ==============================================================================
# Fonctions d'import et de résolution dynamique (Progressive Testability)
# ==============================================================================


def _require_generator_engine() -> Any:
    """Vérifie la disponibilité du module de génération contextuelle."""
    if not GENERATOR_MODULE_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Module obligatoire manquant : {GENERATOR_MODULE_PATH}")
        pytest.skip(f"Module {GENERATOR_MODULE_PATH} non encore implémenté (Jalon M1 en attente)")
    try:
        import src.generation.contextual_generator as gen_mod

        return gen_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Erreur d'import de {GENERATOR_MODULE_PATH} : {exc}")
        pytest.skip(f"Import {GENERATOR_MODULE_PATH} impossible : {exc}")


def _require_dhis2_engine() -> Any:
    """Vérifie la disponibilité du module d'agrégats statistiques DHIS2."""
    if not DHIS2_MODULE_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Module obligatoire manquant : {DHIS2_MODULE_PATH}")
        pytest.skip(f"Module {DHIS2_MODULE_PATH} non encore implémenté (Jalon M2 en attente)")
    try:
        import src.generation.dhis2_generator as dhis2_mod

        return dhis2_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Erreur d'import de {DHIS2_MODULE_PATH} : {exc}")
        pytest.skip(f"Import {DHIS2_MODULE_PATH} impossible : {exc}")


def _get_ground_truth_generator() -> Callable[..., dict[str, Path]]:
    """Récupère la fonction principale de génération de la vérité terrain."""
    gen_mod = _require_generator_engine()
    fn_name = "generate_ground_truth"
    if hasattr(gen_mod, fn_name):
        return getattr(gen_mod, fn_name)
    try:
        import src.generation as pkg_gen

        if hasattr(pkg_gen, fn_name):
            return getattr(pkg_gen, fn_name)
    except ImportError:
        pass

    if IS_STRICT:
        pytest.fail(
            "Fonction 'generate_ground_truth' manquante dans src/generation/contextual_generator.py"
        )
    pytest.skip("Fonction 'generate_ground_truth' non exportée")


def _get_dhis2_generator() -> Callable[..., dict[str, Path]]:
    """Récupère la fonction de génération/extraction des agrégats DHIS2."""
    dhis2_mod = _require_dhis2_engine()
    for fn_name in [
        "extract_or_generate_dhis2_aggregates",
        "generate_dhis2_aggregates",
    ]:
        if hasattr(dhis2_mod, fn_name):
            return getattr(dhis2_mod, fn_name)
    try:
        import src.generation as pkg_gen

        for fn_name in [
            "extract_or_generate_dhis2_aggregates",
            "generate_dhis2_aggregates",
        ]:
            if hasattr(pkg_gen, fn_name):
                return getattr(pkg_gen, fn_name)
    except ImportError:
        pass

    if IS_STRICT:
        pytest.fail("Fonction de génération DHIS2 manquante dans src/generation/dhis2_generator.py")
    pytest.skip("Générateur DHIS2 non exporté")


def _is_valid_uuid_v5(val: Any) -> bool:
    """Vérifie si une chaîne représente un UUID v5 RFC 4122 valide."""
    if not isinstance(val, str) or not val:
        return False
    try:
        u = uuid.UUID(val)
        return u.version == 5
    except (ValueError, TypeError, AttributeError):
        return False


def _load_clinical_table(directory: Path, filename: str) -> pd.DataFrame:
    """Charge une table Parquet clinique avec tolérance de nommage secondaire."""
    path = directory / filename
    if not path.exists() and filename == "prescriptions.parquet":
        alt_path = directory / "medications.parquet"
        if alt_path.exists():
            path = alt_path
    assert path.exists(), f"Fichier Parquet obligatoire introuvable : {path}"
    return pd.read_parquet(path)


# ==============================================================================
# Fixtures Pytest
# ==============================================================================


@pytest.fixture(scope="session")
def geo_reference_df() -> pd.DataFrame:
    """Charge le référentiel géographique sanitaire officiel du Togo (Étape 2)."""
    assert GEOGRAPHY_PARQUET_PATH.exists(), (
        f"Référentiel géographique manquant : {GEOGRAPHY_PARQUET_PATH}"
    )
    df = pd.read_parquet(GEOGRAPHY_PARQUET_PATH)
    assert not df.empty
    return df


@pytest.fixture(scope="session")
def vocab_reference_df() -> pd.DataFrame:
    """Charge le référentiel terminologique mock (Étape 2)."""
    assert VOCAB_PARQUET_PATH.exists(), (
        f"Référentiel terminologique manquant : {VOCAB_PARQUET_PATH}"
    )
    df = pd.read_parquet(VOCAB_PARQUET_PATH)
    assert not df.empty
    return df


@pytest.fixture
def generated_cohort_dir(tmp_path: Path) -> Path:
    """Génère une cohorte standard (50 patients, seed=42) dans un dossier temporaire."""
    gen_fn = _get_ground_truth_generator()
    out_dir = tmp_path / "cohort_50"
    out_dir.mkdir(parents=True, exist_ok=True)
    gen_fn(count=50, seed=42, output_dir=out_dir)
    return out_dir


@pytest.fixture
def generated_dhis2_dir(tmp_path: Path) -> Path:
    """Génère les agrégats statistiques DHIS2 en mode hors-ligne."""
    dhis2_fn = _get_dhis2_generator()
    out_dir = tmp_path / "dhis2_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    dhis2_fn(
        api_url="https://play.dhis2.org/demo",
        output_dir=out_dir,
        offline=True,
        seed=42,
    )
    return out_dir


# ==============================================================================
# TIER 1 : Couverture des fonctionnalités (Feature Coverage)
# ==============================================================================


def test_tier1_clinical_parquet_files_exist_and_non_empty(
    generated_cohort_dir: Path,
) -> None:
    """Vérifie la génération des 6 tables Parquet cliniques avec contenu non vide."""
    for filename in EXPECTED_CLINICAL_FILES:
        target_path = generated_cohort_dir / filename
        # Tolérance pour prescriptions.parquet vs medications.parquet
        if not target_path.exists() and filename == "prescriptions.parquet":
            alt_path = generated_cohort_dir / "medications.parquet"
            if alt_path.exists():
                target_path = alt_path

        assert target_path.exists(), f"Fichier Parquet clinique attendu manquant : {filename}"
        assert target_path.stat().st_size > 0, f"Fichier Parquet vide : {filename}"

        df = pd.read_parquet(target_path)
        assert len(df) > 0, f"La table Parquet {filename} ne contient aucun enregistrement"


def test_tier1_dhis2_files_exist_and_match(generated_dhis2_dir: Path) -> None:
    """Vérifie la génération des fichiers DHIS2 (JSON et Parquet) et leur concordance."""
    json_path = generated_dhis2_dir / "dhis2_data_values.json"
    if not json_path.exists():
        json_path = generated_dhis2_dir / "dhis2" / "dhis2_data_values.json"

    parquet_path = generated_dhis2_dir / "dhis2_data_values.parquet"
    if not parquet_path.exists():
        parquet_path = generated_dhis2_dir / "dhis2" / "dhis2_data_values.parquet"

    assert json_path.exists(), f"Fichier JSON DHIS2 introuvable dans {generated_dhis2_dir}"
    assert parquet_path.exists(), f"Fichier Parquet DHIS2 introuvable dans {generated_dhis2_dir}"

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Doit contenir la clé racine standard DHIS2 dataValues ou être une liste
    data_values = data.get("dataValues", data) if isinstance(data, dict) else data
    assert isinstance(data_values, list) and len(data_values) > 0, (
        "Le JSON DHIS2 doit contenir une liste non vide d'agrégats (dataValues)"
    )

    df_parquet = pd.read_parquet(parquet_path)
    assert len(df_parquet) > 0, "La table Parquet DHIS2 est vide"
    assert len(df_parquet) == len(data_values), (
        f"Divergence de lignes entre JSON ({len(data_values)}) et Parquet ({len(df_parquet)})"
    )


def test_tier1_primary_keys_non_null_and_uuid_v5(generated_cohort_dir: Path) -> None:
    """Vérifie que les clés primaires de toutes les tables sont non-nulles, uniques et en UUID v5."""
    pk_mapping = {
        "patients.parquet": "patient_id",
        "encounters.parquet": "encounter_id",
        "conditions.parquet": "condition_id",
        "observations.parquet": "observation_id",
        "prescriptions.parquet": "prescription_id",
        "immunizations.parquet": "immunization_id",
    }

    for filename, expected_pk in pk_mapping.items():
        df = _load_clinical_table(generated_cohort_dir, filename)

        pk_col = expected_pk
        if (
            pk_col not in df.columns
            and filename == "prescriptions.parquet"
            and "medication_request_id" in df.columns
        ):
            pk_col = "medication_request_id"

        assert pk_col in df.columns, (
            f"Clé primaire '{expected_pk}' manquante dans {filename}. Colonnes: {list(df.columns)}"
        )

        # 1. Non-nullité
        assert df[pk_col].isnull().sum() == 0, (
            f"Valeurs nulles détectées dans la clé primaire '{pk_col}' de {filename}"
        )

        # 2. Unicité
        assert df[pk_col].is_unique, (
            f"Doublons détectés dans la clé primaire '{pk_col}' de {filename}"
        )

        # 3. Format UUID v5 RFC 4122
        invalid_uuids = [val for val in df[pk_col] if not _is_valid_uuid_v5(val)]
        assert not invalid_uuids, (
            f"{len(invalid_uuids)} clés primaires dans {filename} ne sont pas des UUID v5 valides. "
            f"Exemple invalide : {invalid_uuids[0]}"
        )


def test_tier1_referential_integrity_foreign_keys(generated_cohort_dir: Path) -> None:
    """Vérifie l'intégrité référentielle stricte entre toutes les tables cliniques."""
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")
    encounters_df = _load_clinical_table(generated_cohort_dir, "encounters.parquet")
    conditions_df = _load_clinical_table(generated_cohort_dir, "conditions.parquet")
    observations_df = _load_clinical_table(generated_cohort_dir, "observations.parquet")
    prescriptions_df = _load_clinical_table(generated_cohort_dir, "prescriptions.parquet")
    immunizations_df = _load_clinical_table(generated_cohort_dir, "immunizations.parquet")

    patient_ids = set(patients_df["patient_id"])
    encounter_ids = set(encounters_df["encounter_id"])

    # 1. Encounters -> Patients
    orphan_enc_pat = set(encounters_df["patient_id"]) - patient_ids
    assert not orphan_enc_pat, f"{len(orphan_enc_pat)} séjours référencent des patients inexistants"

    # 2. Conditions -> Patients & Encounters
    orphan_cond_pat = set(conditions_df["patient_id"]) - patient_ids
    assert not orphan_cond_pat, (
        f"{len(orphan_cond_pat)} diagnostics référencent des patients inexistants"
    )
    orphan_cond_enc = set(conditions_df["encounter_id"]) - encounter_ids
    assert not orphan_cond_enc, (
        f"{len(orphan_cond_enc)} diagnostics référencent des séjours inexistants"
    )

    # 3. Observations -> Patients & Encounters
    orphan_obs_pat = set(observations_df["patient_id"]) - patient_ids
    assert not orphan_obs_pat, (
        f"{len(orphan_obs_pat)} observations référencent des patients inexistants"
    )
    orphan_obs_enc = set(observations_df["encounter_id"]) - encounter_ids
    assert not orphan_obs_enc, (
        f"{len(orphan_obs_enc)} observations référencent des séjours inexistants"
    )

    # 4. Prescriptions -> Patients & Encounters
    orphan_presc_pat = set(prescriptions_df["patient_id"]) - patient_ids
    assert not orphan_presc_pat, (
        f"{len(orphan_presc_pat)} prescriptions référencent des patients inexistants"
    )
    orphan_presc_enc = set(prescriptions_df["encounter_id"]) - encounter_ids
    assert not orphan_presc_enc, (
        f"{len(orphan_presc_enc)} prescriptions référencent des séjours inexistants"
    )

    # 5. Immunizations -> Patients
    orphan_imm_pat = set(immunizations_df["patient_id"]) - patient_ids
    assert not orphan_imm_pat, f"{len(orphan_imm_pat)} vaccins référencent des patients inexistants"

    if "encounter_id" in immunizations_df.columns:
        valid_imm_enc = immunizations_df["encounter_id"].dropna()
        orphan_imm_enc = set(valid_imm_enc) - encounter_ids
        assert not orphan_imm_enc, (
            f"{len(orphan_imm_enc)} vaccins référencent des séjours inexistants"
        )


def test_tier1_expected_columns_and_types(generated_cohort_dir: Path) -> None:
    """Vérifie la conformité des schémas et la présence des colonnes obligatoires."""
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")
    required_patient_cols = {
        "patient_id",
        "family_name",
        "given_name",
        "gender",
        "birth_date",
        "age_precision",
    }
    assert required_patient_cols.issubset(patients_df.columns), (
        f"Colonnes patient manquantes : {required_patient_cols - set(patients_df.columns)}"
    )
    assert (
        "estimated_age_flag" in patients_df.columns
        or "is_estimated_birth_date" in patients_df.columns
    ), "Colonne d'âge estimé manquante dans patients.parquet"

    encounters_df = _load_clinical_table(generated_cohort_dir, "encounters.parquet")
    required_encounter_cols = {
        "encounter_id",
        "patient_id",
        "facility_id",
        "pyramid_level",
        "district_code",
        "region_code",
    }
    assert required_encounter_cols.issubset(encounters_df.columns), (
        f"Colonnes séjour manquantes : {required_encounter_cols - set(encounters_df.columns)}"
    )

    conditions_df = _load_clinical_table(generated_cohort_dir, "conditions.parquet")
    required_condition_cols = {
        "condition_id",
        "patient_id",
        "encounter_id",
        "pathology_group",
        "icd10_code",
        "snomed_code",
    }
    assert required_condition_cols.issubset(conditions_df.columns), (
        f"Colonnes diagnostic manquantes : {required_condition_cols - set(conditions_df.columns)}"
    )

    observations_df = _load_clinical_table(generated_cohort_dir, "observations.parquet")
    required_obs_cols = {"observation_id", "patient_id", "encounter_id", "loinc_code"}
    assert required_obs_cols.issubset(observations_df.columns), (
        f"Colonnes observation manquantes : {required_obs_cols - set(observations_df.columns)}"
    )

    prescriptions_df = _load_clinical_table(generated_cohort_dir, "prescriptions.parquet")
    assert "atc_code" in prescriptions_df.columns
    assert "patient_id" in prescriptions_df.columns
    assert "encounter_id" in prescriptions_df.columns

    immunizations_df = _load_clinical_table(generated_cohort_dir, "immunizations.parquet")
    required_imm_cols = {
        "immunization_id",
        "patient_id",
        "vaccine_code",
        "atc_code",
        "lot_number",
    }
    assert required_imm_cols.issubset(immunizations_df.columns), (
        f"Colonnes vaccin manquantes : {required_imm_cols - set(immunizations_df.columns)}"
    )


# ==============================================================================
# TIER 2 : Cas limites, robustesse et intégrité clinique (Edge Cases)
# ==============================================================================


def test_tier2_boundary_count_minimal_cohort(tmp_path: Path) -> None:
    """Vérifie la génération d'une cohorte minimale count=1 sans division par zéro."""
    gen_fn = _get_ground_truth_generator()
    out_dir = tmp_path / "cohort_1"
    out_dir.mkdir(parents=True, exist_ok=True)

    gen_fn(count=1, seed=42, output_dir=out_dir)

    patients_df = pd.read_parquet(out_dir / "patients.parquet")
    assert len(patients_df) == 1, f"Attendu 1 patient, obtenu {len(patients_df)}"

    encounters_df = pd.read_parquet(out_dir / "encounters.parquet")
    assert len(encounters_df) >= 1, "Le patient doit avoir au moins un séjour"


def test_tier2_boundary_count_zero_or_negative_raises_error(tmp_path: Path) -> None:
    """Vérifie que count=0 ou count négatif est refusé avec ValueError."""
    gen_fn = _get_ground_truth_generator()
    out_dir = tmp_path / "cohort_invalid"
    out_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError):
        gen_fn(count=0, seed=42, output_dir=out_dir)

    with pytest.raises(ValueError):
        gen_fn(count=-5, seed=42, output_dir=out_dir)


def test_tier2_dhis2_offline_fallback_with_invalid_url(tmp_path: Path) -> None:
    """Vérifie la bascule transparente sur repli hors-ligne en cas d'URL DHIS2 inaccessible."""
    dhis2_fn = _get_dhis2_generator()
    out_dir = tmp_path / "dhis2_fallback"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Appel avec URL invalide et offline=False : doit basculer sans exception non gérée
    dhis2_fn(
        api_url="http://invalid-dhis2-test-url.local",
        output_dir=out_dir,
        offline=False,
        seed=42,
    )

    json_path = out_dir / "dhis2_data_values.json"
    if not json_path.exists():
        json_path = out_dir / "dhis2" / "dhis2_data_values.json"
    assert json_path.exists(), "Le repli hors-ligne DHIS2 n'a pas produit de fichier JSON"


def test_tier2_clinical_no_male_with_pregnancy(generated_cohort_dir: Path) -> None:
    """Règle clinique absolue : AUCUN patient de sexe masculin ne peut avoir de grossesse/accouchement."""
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")
    conditions_df = _load_clinical_table(generated_cohort_dir, "conditions.parquet")

    # Jointure conditions avec patients pour vérifier le sexe
    merged = conditions_df.merge(patients_df[["patient_id", "gender"]], on="patient_id", how="left")
    male_conditions = merged[merged["gender"].str.lower() == "male"]

    # Codes de grossesse/accouchement (CIM-10 Z34, O80, O82, ou tout chapitre O)
    pregnancy_icd_codes = {"Z34", "Z34.0", "Z34.8", "Z34.9", "O80", "O82"}

    # Vérification par code CIM-10
    violations_icd = male_conditions[
        male_conditions["icd10_code"].isin(pregnancy_icd_codes)
        | male_conditions["icd10_code"].str.startswith("O")
    ]
    assert violations_icd.empty, (
        f"VIOLATION CLINIQUE : {len(violations_icd)} diagnostics de grossesse attribués à des hommes. "
        f"Exemples : {violations_icd[['patient_id', 'icd10_code']].to_dict(orient='records')}"
    )

    # Vérification par groupe pathologique SMI
    smi_male = male_conditions[male_conditions["pathology_group"] == "SMI"]
    assert smi_male.empty, (
        f"VIOLATION CLINIQUE : {len(smi_male)} diagnostics SMI attribués à des patients masculins"
    )


def test_tier2_clinical_no_adult_with_pediatric_pev_vaccines(
    generated_cohort_dir: Path,
) -> None:
    """Règle clinique : Les vaccins du PEV pédiatrique sont réservés aux enfants de moins de 5 ans."""
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")
    immunizations_df = _load_clinical_table(generated_cohort_dir, "immunizations.parquet")

    merged = immunizations_df.merge(
        patients_df[["patient_id", "birth_date"]], on="patient_id", how="left"
    )

    date_col = "administered_date" if "administered_date" in merged.columns else "occurrence_date"
    assert date_col in merged.columns

    # Calcul de l'âge au moment de la vaccination
    birth_dates = pd.to_datetime(merged["birth_date"])
    admin_dates = pd.to_datetime(merged[date_col])
    ages_at_vaccine_years = (admin_dates - birth_dates).dt.days / 365.25

    # Aucun vaccin pédiatrique pour un patient âgé de 5 ans ou plus
    adult_vaccinations = merged[ages_at_vaccine_years >= 5.0]
    assert adult_vaccinations.empty, (
        f"VIOLATION CLINIQUE : {len(adult_vaccinations)} vaccins PEV pédiatriques administrés à des patients >= 5 ans. "
        f"Exemples : {adult_vaccinations[['patient_id', 'vaccine_code', date_col]].to_dict(orient='records')}"
    )


def test_tier2_clinical_chronic_conditions_adults_only(
    generated_cohort_dir: Path,
) -> None:
    """Règle clinique : L'HTA et le Diabète de type 2 sont des affections d'adultes (zéro chez nourrissons < 5 ans)."""
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")
    conditions_df = _load_clinical_table(generated_cohort_dir, "conditions.parquet")

    merged = conditions_df.merge(
        patients_df[["patient_id", "birth_date"]], on="patient_id", how="left"
    )

    # Calcul de l'âge approximatif au diagnostic ou date de naissance
    ref_date = datetime.date(2025, 6, 1)
    birth_years = pd.to_datetime(merged["birth_date"]).dt.year
    merged["age_approx"] = ref_date.year - birth_years

    # Conditions chroniques HTA (I10) et Diabète (E11.9)
    chronic_conditions = merged[
        merged["icd10_code"].isin({"I10", "E11.9"})
        | merged["pathology_group"].isin({"HTA", "Diabetes"})
    ]

    if not chronic_conditions.empty:
        infant_chronics = chronic_conditions[chronic_conditions["age_approx"] < 5]
        assert infant_chronics.empty, (
            f"VIOLATION CLINIQUE : {len(infant_chronics)} cas d'HTA ou Diabète détectés chez des nourrissons (< 5 ans)."
        )


def test_tier2_val003_estimated_age_july_first_and_precision(
    generated_cohort_dir: Path,
) -> None:
    """Conformité VAL-003 : Date de naissance au 1er juillet (-07-01) et age_precision='approximate-year'."""
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")

    flag_col = (
        "estimated_age_flag"
        if "estimated_age_flag" in patients_df.columns
        else "is_estimated_birth_date"
    )
    assert flag_col in patients_df.columns

    estimated_patients = patients_df[patients_df[flag_col] == True]  # noqa: E712
    exact_patients = patients_df[patients_df[flag_col] == False]  # noqa: E712

    # Doit contenir une proportion d'âges estimés (au moins 1 patient sur 50)
    assert len(estimated_patients) > 0, (
        "La cohorte doit contenir des patients avec âge estimé (VAL-003)"
    )

    # 1. 100% des dates d'âges estimés se terminent par -07-01
    invalid_birth_dates = estimated_patients[
        ~estimated_patients["birth_date"].str.endswith("-07-01")
    ]
    assert invalid_birth_dates.empty, (
        f"{len(invalid_birth_dates)} patients avec âge estimé n'ont pas leur date fixée au 1er juillet (-07-01). "
        f"Exemples : {invalid_birth_dates[['patient_id', 'birth_date']].head(3).to_dict(orient='records')}"
    )

    # 2. Précision codifiée à 'approximate-year' ou 'year'
    invalid_precision = estimated_patients[
        ~estimated_patients["age_precision"].isin({"approximate-year", "year"})
    ]
    assert invalid_precision.empty, (
        f"{len(invalid_precision)} patients avec âge estimé ont une précision invalide : "
        f"{invalid_precision['age_precision'].unique()}"
    )

    # 3. Pour les âges exacts, précision fixée à 'exact' (ou 'day')
    if not exact_patients.empty and "age_precision" in exact_patients.columns:
        invalid_exact_precision = exact_patients[
            ~exact_patients["age_precision"].isin({"exact", "day"})
        ]
        assert invalid_exact_precision.empty, (
            f"Patients exacts avec précision inattendue : {invalid_exact_precision['age_precision'].unique()}"
        )


# ==============================================================================
# TIER 3 : Déterminisme strict (Strict Determinism)
# ==============================================================================


def test_tier3_determinism_identical_seed_identical_files_sha256(
    tmp_path: Path,
) -> None:
    """Deux exécutions successives avec la même graine (seed=42, count=50) produisent des fichiers bit-à-bit identiques."""
    gen_fn = _get_ground_truth_generator()

    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"
    run1_dir.mkdir(parents=True, exist_ok=True)
    run2_dir.mkdir(parents=True, exist_ok=True)

    gen_fn(count=50, seed=42, output_dir=run1_dir)
    gen_fn(count=50, seed=42, output_dir=run2_dir)

    for filename in EXPECTED_CLINICAL_FILES:
        f1 = run1_dir / filename
        f2 = run2_dir / filename
        if not f1.exists() and filename == "prescriptions.parquet":
            f1 = run1_dir / "medications.parquet"
            f2 = run2_dir / "medications.parquet"

        assert f1.exists() and f2.exists()

        # 1. Comparaison SHA-256 bit-à-bit
        sha1 = hashlib.sha256(f1.read_bytes()).hexdigest()
        sha2 = hashlib.sha256(f2.read_bytes()).hexdigest()
        assert sha1 == sha2, (
            f"Rupture de déterminisme binaire sur {filename} : SHA1={sha1} != SHA2={sha2}"
        )

        # 2. Comparaison stricte des DataFrames
        df1 = pd.read_parquet(f1)
        df2 = pd.read_parquet(f2)
        pd.testing.assert_frame_equal(df1, df2)


def test_tier3_determinism_different_seeds_produce_different_data(
    tmp_path: Path,
) -> None:
    """Deux exécutions avec des graines différentes (seed=42 vs seed=43) produisent des données divergentes."""
    gen_fn = _get_ground_truth_generator()

    dir42 = tmp_path / "seed42"
    dir43 = tmp_path / "seed43"
    dir42.mkdir(parents=True, exist_ok=True)
    dir43.mkdir(parents=True, exist_ok=True)

    gen_fn(count=50, seed=42, output_dir=dir42)
    gen_fn(count=50, seed=43, output_dir=dir43)

    p42 = pd.read_parquet(dir42 / "patients.parquet")
    p43 = pd.read_parquet(dir43 / "patients.parquet")

    # Divergence des identifiants et des patronymes
    sha42 = hashlib.sha256((dir42 / "patients.parquet").read_bytes()).hexdigest()
    sha43 = hashlib.sha256((dir43 / "patients.parquet").read_bytes()).hexdigest()
    assert sha42 != sha43, "Graines différentes (42 et 43) doivent produire des fichiers distincts"

    common_ids = set(p42["patient_id"]).intersection(set(p43["patient_id"]))
    assert len(common_ids) == 0, (
        f"{len(common_ids)} patient_id identiques trouvés entre graines différentes"
    )


def test_tier3_dhis2_determinism_identical_seed(tmp_path: Path) -> None:
    """Le générateur DHIS2 avec la même graine produit des agrégats rigoureusement identiques."""
    dhis2_fn = _get_dhis2_generator()

    out_a = tmp_path / "dhis2_a"
    out_b = tmp_path / "dhis2_b"
    out_a.mkdir(parents=True, exist_ok=True)
    out_b.mkdir(parents=True, exist_ok=True)

    dhis2_fn(
        api_url="https://play.dhis2.org/demo",
        output_dir=out_a,
        offline=True,
        seed=42,
    )
    dhis2_fn(
        api_url="https://play.dhis2.org/demo",
        output_dir=out_b,
        offline=True,
        seed=42,
    )

    parquet_a = out_a / "dhis2_data_values.parquet"
    if not parquet_a.exists():
        parquet_a = out_a / "dhis2" / "dhis2_data_values.parquet"

    parquet_b = out_b / "dhis2_data_values.parquet"
    if not parquet_b.exists():
        parquet_b = out_b / "dhis2" / "dhis2_data_values.parquet"

    assert parquet_a.exists() and parquet_b.exists()
    sha_a = hashlib.sha256(parquet_a.read_bytes()).hexdigest()
    sha_b = hashlib.sha256(parquet_b.read_bytes()).hexdigest()
    assert sha_a == sha_b, "Déterminisme DHIS2 violé : SHA-256 distincts"


# ==============================================================================
# TIER 4 : Adhérence 100% aux Référentiels Réels et Pyramide Sanitaire
# ==============================================================================


def test_tier4_100_percent_geography_reference_adherence(
    generated_cohort_dir: Path,
    geo_reference_df: pd.DataFrame,
) -> None:
    """100% des établissements, districts et régions générés existent dans togo_health_geography.parquet."""
    encounters_df = _load_clinical_table(generated_cohort_dir, "encounters.parquet")
    patients_df = _load_clinical_table(generated_cohort_dir, "patients.parquet")

    valid_facilities = set(geo_reference_df["facility_id"])
    valid_districts = set(geo_reference_df["district_code"])
    valid_regions = set(geo_reference_df["region_code"])

    # 1. Vérification dans encounters.parquet
    invalid_fac = set(encounters_df["facility_id"]) - valid_facilities
    assert not invalid_fac, (
        f"{len(invalid_fac)} facility_id dans encounters n'existent pas dans le référentiel géographique. "
        f"Exemple invalide : {next(iter(invalid_fac))}"
    )

    invalid_dist = set(encounters_df["district_code"]) - valid_districts
    assert not invalid_dist, (
        f"{len(invalid_dist)} district_code dans encounters n'existent pas dans le référentiel. "
        f"Exemple invalide : {next(iter(invalid_dist))}"
    )

    invalid_reg = set(encounters_df["region_code"]) - valid_regions
    assert not invalid_reg, (
        f"{len(invalid_reg)} region_code dans encounters n'existent pas dans le référentiel"
    )

    # 2. Vérification dans patients.parquet (résidence)
    for dist_col in ["address_district_code", "residence_district_code", "district_code"]:
        if dist_col in patients_df.columns:
            invalid_pat_dist = set(patients_df[dist_col]) - valid_districts
            assert not invalid_pat_dist, (
                f"{len(invalid_pat_dist)} codes district de résidence patients inexistants"
            )

    for reg_col in ["address_region_code", "residence_region_code", "region_code"]:
        if reg_col in patients_df.columns:
            invalid_pat_reg = set(patients_df[reg_col]) - valid_regions
            assert not invalid_pat_reg, (
                f"{len(invalid_pat_reg)} codes région de résidence patients inexistants"
            )


def test_tier4_100_percent_terminology_reference_adherence(
    generated_cohort_dir: Path,
    vocab_reference_df: pd.DataFrame,
) -> None:
    """100% des codes CIM-10, SNOMED, LOINC et ATC générés existent dans sample_vocabularies.parquet."""
    conditions_df = _load_clinical_table(generated_cohort_dir, "conditions.parquet")
    observations_df = _load_clinical_table(generated_cohort_dir, "observations.parquet")
    prescriptions_df = _load_clinical_table(generated_cohort_dir, "prescriptions.parquet")
    immunizations_df = _load_clinical_table(generated_cohort_dir, "immunizations.parquet")

    valid_icd10 = set(
        vocab_reference_df[vocab_reference_df["vocabulary_id"] == "ICD10"]["concept_code"]
    )
    valid_snomed = set(
        vocab_reference_df[vocab_reference_df["vocabulary_id"] == "SNOMED"]["concept_code"]
    )
    valid_loinc = set(
        vocab_reference_df[vocab_reference_df["vocabulary_id"] == "LOINC"]["concept_code"]
    )
    valid_atc = set(
        vocab_reference_df[vocab_reference_df["vocabulary_id"] == "ATC"]["concept_code"]
    )

    # 1. Conditions -> ICD-10 et SNOMED CT
    invalid_icd10 = set(conditions_df["icd10_code"]) - valid_icd10
    assert not invalid_icd10, (
        f"{len(invalid_icd10)} codes CIM-10 non répertoriés dans sample_vocabularies.parquet : {invalid_icd10}"
    )

    invalid_snomed = set(conditions_df["snomed_code"]) - valid_snomed
    assert not invalid_snomed, (
        f"{len(invalid_snomed)} codes SNOMED CT non répertoriés dans sample_vocabularies.parquet : {invalid_snomed}"
    )

    # 2. Observations -> LOINC
    invalid_loinc = set(observations_df["loinc_code"]) - valid_loinc
    assert not invalid_loinc, (
        f"{len(invalid_loinc)} codes LOINC non répertoriés dans sample_vocabularies.parquet : {invalid_loinc}"
    )

    # 3. Prescriptions -> ATC
    invalid_atc_presc = set(prescriptions_df["atc_code"]) - valid_atc
    assert not invalid_atc_presc, (
        f"{len(invalid_atc_presc)} codes ATC non répertoriés dans prescriptions : {invalid_atc_presc}"
    )

    # 4. Immunizations -> ATC
    invalid_atc_imm = set(immunizations_df["atc_code"]) - valid_atc
    assert not invalid_atc_imm, (
        f"{len(invalid_atc_imm)} codes ATC vaccins non répertoriés dans immunizations : {invalid_atc_imm}"
    )


def test_tier4_healthcare_pyramid_distribution_and_referrals(
    generated_cohort_dir: Path,
    geo_reference_df: pd.DataFrame,
) -> None:
    """Vérifie la répartition pyramidale (majorité au niveau 1 CMS/USP) et la validité des transferts."""
    encounters_df = _load_clinical_table(generated_cohort_dir, "encounters.parquet")
    valid_facilities = set(geo_reference_df["facility_id"])

    # Distribution par niveau de la pyramide (1 à 4)
    level_counts = encounters_df["pyramid_level"].value_counts(normalize=True)

    # Niveau 1 (CMS / USP) doit concentrer la majorité des soins (entre 60% et 85%)
    level1_ratio = level_counts.get(1, 0.0)
    assert 0.60 <= level1_ratio <= 0.85, (
        f"Le Niveau 1 (CMS/USP) doit concentrer 60% à 85% des séjours, obtenu : {level1_ratio:.1%}"
    )

    # Niveau 2 (CHP / Hôpital préfectoral)
    level2_ratio = level_counts.get(2, 0.0)
    assert 0.08 <= level2_ratio <= 0.30, (
        f"Le Niveau 2 doit représenter entre 8% et 30% des séjours, obtenu : {level2_ratio:.1%}"
    )

    # Niveaux 3 et 4 (CHR et CHU)
    level3_4_ratio = level_counts.get(3, 0.0) + level_counts.get(4, 0.0)
    assert 0.02 <= level3_4_ratio <= 0.20, (
        f"Les Niveaux 3 et 4 doivent représenter entre 2% et 20% des séjours, obtenu : {level3_4_ratio:.1%}"
    )

    # Vérification des références / transferts (referral_from_facility_id)
    if "referral_from_facility_id" in encounters_df.columns:
        referrals = encounters_df["referral_from_facility_id"].dropna()
        if not referrals.empty:
            invalid_referrals = set(referrals) - valid_facilities
            assert not invalid_referrals, (
                f"{len(invalid_referrals)} structures émettrices de transferts invalides"
            )
