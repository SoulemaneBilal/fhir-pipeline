"""Tests E2E, unitaires et de validation du Moteur de Dégradation Contrôlée (Étape 4).

Conforme aux spécifications formelles de DISPATCH.md, SCOPE.md, Roadmap technique.md §4
et SYNTHESE_PROJET.md §3.1 (Étape 4).

Structure des tests :
- Tier 1 : Catalogue d'Erreurs & Configuration (chargement YAML, Pydantic, complétude des 11 règles, unicité, descriptions en français)
- Tier 2 : Mutateurs Unitaires (dates mixtes, âges approximatifs, coquilles patronymes, suppression accents,
          inversion nom/prénom, libellés cliniques libres, séparateur virgule, unités UCUM altérées,
          sentinelles, valeurs manquantes, mojibake encodage, noms de structures sanitaires)
- Tier 3 : Journal d'Altérations (schéma PyArrow strict, modèle Pydantic, sérialisation Parquet et JSONL,
          réversibilité / corrigé de référence, absence de mutation non tracée)
- Tier 4 : Moteur de Dégradation Global (exécution sur les 6 tables cliniques, respect du taux cible +/- 5%,
          injection de doublons patients pour Splink, déterminisme bit-à-bit SHA-256 sous seed fixe,
          divergence entre graines distinctes, robustesse aux cas limites)
- Tier 5 : Exportateurs Multi-Formats (Excel .xlsx multi-onglets, CSV délimiteur point-virgule,
          JSON/FHIR altéré avec anomalies documentées, agrégats DHIS2 dégradés)
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd
import pyarrow as pa
import pytest
import yaml

IS_STRICT = os.environ.get("STRICT_E2E") == "1"

# Chemins des données de référence (Étape 3)
TRUTH_DIR = Path("data/truth")
TRUTH_DHIS2_JSON = Path("data/truth/dhis2/dhis2_data_values.json")
TRUTH_DHIS2_PARQUET = Path("data/truth/dhis2/dhis2_data_values.parquet")

CONFIG_RULES_PATH = Path("config/degradation_rules.yaml")

CLINICAL_TABLES = [
    "patients",
    "encounters",
    "conditions",
    "observations",
    "prescriptions",
    "immunizations",
]

# Identifiants de règles requis par la spécification formelle
MANDATORY_RULE_IDS = {
    "RULE-DATE-001",  # Formats de dates hétérogènes
    "RULE-DATE-002",  # Date de naissance vers âge approximatif textuel
    "RULE-NAME-001",  # Coquilles typographiques et orthographe des patronymes togolais
    "RULE-NAME-002",  # Suppression des diacritiques et accents
    "RULE-NAME-003",  # Inversion ordre nom / prénom
    "RULE-NAME-004",  # Variantes phonétiques et translittérations locales
    "RULE-CLIN-001",  # Diagnostics en texte libre ou abréviations médicales
    "RULE-MEAS-001",  # Séparateur décimal virgule au lieu du point
    "RULE-MEAS-002",  # Unités de mesure non conformes ou omises
    "RULE-SENT-001",  # Codes sentinelles (-1, 999, NA, ND)
    "RULE-MISS-001",  # Injection de valeurs manquantes (NULL / vide)
    "RULE-DUPL-001",  # Doublons de patients inter-établissements pour Splink
    "RULE-ENCO-001",  # Corruption d'encodage Mojibake (UTF-8 / Latin-1)
    "RULE-FACI-001",  # Variations et abréviations des noms de formations sanitaires
    "RULE-FHIR-001",  # Anomalies de structure et références FHIR
    "RULE-DHIS-001",  # Altérations des agrégats statistiques DHIS2
}


# ==============================================================================
# Fonctions d'import et de résolution dynamique (Progressive Testability)
# ==============================================================================


def _require_catalog_module() -> Any:
    """Importe dynamiquement le module de catalogue."""
    try:
        import src.degradation.catalog as cat_mod

        return cat_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.degradation.catalog obligatoire manquant : {exc}")
        pytest.skip(f"src.degradation.catalog en attente d'implémentation : {exc}")


def _require_schemas_module() -> Any:
    """Importe dynamiquement le module de schémas."""
    try:
        import src.degradation.schemas as schemas_mod

        return schemas_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.degradation.schemas obligatoire manquant : {exc}")
        pytest.skip(f"src.degradation.schemas en attente d'implémentation : {exc}")


def _require_mutators_module() -> Any:
    """Importe dynamiquement le module de mutateurs unitaires."""
    try:
        import src.degradation.mutators as mut_mod

        return mut_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.degradation.mutators obligatoire manquant : {exc}")
        pytest.skip(f"src.degradation.mutators en attente d'implémentation : {exc}")


def _require_engine_module() -> Any:
    """Importe dynamiquement le module de moteur global."""
    try:
        import src.degradation.engine as eng_mod

        return eng_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.degradation.engine obligatoire manquant : {exc}")
        pytest.skip(f"src.degradation.engine en attente d'implémentation : {exc}")


def _require_exporters_module() -> Any:
    """Importe dynamiquement le module d'exportateurs multi-formats."""
    try:
        import src.degradation.exporters as exp_mod

        return exp_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.degradation.exporters obligatoire manquant : {exc}")
        pytest.skip(f"src.degradation.exporters en attente d'implémentation : {exc}")


def _is_valid_uuid(val: Any) -> bool:
    """Vérifie la validité RFC 4122 d'un identifiant UUID."""
    if not isinstance(val, str) or not val:
        return False
    try:
        uuid.UUID(val)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _compute_file_sha256(path: Path) -> str:
    """Calcule l'empreinte SHA-256 d'un fichier binaire."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


# ==============================================================================
# Fixtures Pytest
# ==============================================================================


@pytest.fixture(scope="session")
def ground_truth_tables() -> dict[str, pd.DataFrame]:
    """Charge les 6 tables de vérité terrain générées à l'Étape 3."""
    assert TRUTH_DIR.exists(), f"Dossier de vérité terrain manquant : {TRUTH_DIR}"
    tables: dict[str, pd.DataFrame] = {}
    for table_name in CLINICAL_TABLES:
        table_path = TRUTH_DIR / f"{table_name}.parquet"
        assert table_path.exists(), f"Table de vérité terrain manquante : {table_path}"
        df = pd.read_parquet(table_path)
        assert not df.empty, f"Table {table_name} vide"
        tables[table_name] = df
    return tables


@pytest.fixture
def sample_patient_df() -> pd.DataFrame:
    """Mini jeu de données patients synthétiques pour tests unitaires et déterministes."""
    return pd.DataFrame(
        [
            {
                "patient_id": "00000000-0000-0000-0000-000000000001",
                "identifier_system": "urn:togo:patient",
                "identifier_value": "TG-PAT-1000001",
                "nni": "TG-NNI-1000001",
                "family_name": "Mensah",
                "given_name": "Koffi",
                "gender": "male",
                "birth_date": "1985-04-15",
                "is_estimated_birth_date": False,
                "estimated_age_flag": False,
                "age_precision": "exact",
                "phone_number": "+228 90 12 34 56",
                "address_region_code": "TG-MAR",
                "address_district_code": "TG-MAR-GOL",
                "address_city": "Lomé",
                "residence_district_code": "TG-MAR-GOL",
                "residence_region_code": "TG-MAR",
                "marital_status": "M",
                "ethnic_group": "Ewe",
                "created_at": "2024-01-01T08:00:00Z",
            },
            {
                "patient_id": "00000000-0000-0000-0000-000000000002",
                "identifier_system": "urn:togo:patient",
                "identifier_value": "TG-PAT-1000002",
                "nni": "TG-NNI-1000002",
                "family_name": "Lawson",
                "given_name": "Ablavi",
                "gender": "female",
                "birth_date": "1992-07-01",
                "is_estimated_birth_date": True,
                "estimated_age_flag": True,
                "age_precision": "approximate-year",
                "phone_number": "+228 91 23 45 67",
                "address_region_code": "TG-PLA",
                "address_district_code": "TG-PLA-KLU",
                "address_city": "Kpalimé",
                "residence_district_code": "TG-PLA-KLU",
                "residence_region_code": "TG-PLA",
                "marital_status": "U",
                "ethnic_group": "Mina",
                "created_at": "2024-01-02T09:30:00Z",
            },
            {
                "patient_id": "00000000-0000-0000-0000-000000000003",
                "identifier_system": "urn:togo:patient",
                "identifier_value": "TG-PAT-1000003",
                "nni": "TG-NNI-1000003",
                "family_name": "Adjamagbo",
                "given_name": "Kodjo",
                "gender": "male",
                "birth_date": "1978-11-23",
                "is_estimated_birth_date": False,
                "estimated_age_flag": False,
                "age_precision": "exact",
                "phone_number": "+228 92 34 56 78",
                "address_region_code": "TG-SAV",
                "address_district_code": "TG-SAV-TON",
                "address_city": "Dapaong",
                "residence_district_code": "TG-SAV-TON",
                "residence_region_code": "TG-SAV",
                "marital_status": "M",
                "ethnic_group": "Moba",
                "created_at": "2024-01-03T11:00:00Z",
            },
        ]
    )


@pytest.fixture
def sample_encounter_df() -> pd.DataFrame:
    """Mini jeu de données épisodes de soins synthétiques."""
    return pd.DataFrame(
        [
            {
                "encounter_id": "10000000-0000-0000-0000-000000000001",
                "patient_id": "00000000-0000-0000-0000-000000000001",
                "facility_id": "f0000000-0000-0000-0000-000000000001",
                "facility_code": "TG-FAC-001",
                "facility_name": "Centre Médico-Social d'Adidogomé",
                "facility_category": "CMS",
                "pyramid_level": 1,
                "district_code": "TG-MAR-GOL",
                "region_code": "TG-MAR",
                "encounter_class": "ambulatory",
                "encounter_type": "consultation",
                "start_date": "2024-02-10T08:30:00Z",
                "start_datetime": "2024-02-10T08:30:00Z",
                "end_date": "2024-02-10T09:15:00Z",
                "end_datetime": "2024-02-10T09:15:00Z",
                "reason_code": "B50",
                "reason_display": "Paludisme à Plasmodium falciparum",
                "status": "finished",
                "referral_from_facility_id": None,
            }
        ]
    )


@pytest.fixture
def sample_observation_df() -> pd.DataFrame:
    """Mini jeu de données observations biologiques et signes vitaux synthétiques."""
    return pd.DataFrame(
        [
            {
                "observation_id": "20000000-0000-0000-0000-000000000001",
                "patient_id": "00000000-0000-0000-0000-000000000001",
                "encounter_id": "10000000-0000-0000-0000-000000000001",
                "category": "vital-signs",
                "loinc_code": "8310-5",
                "loinc_display": "Température corporelle",
                "value_quantity": 38.5,
                "value_numeric": 38.5,
                "value_unit": "Cel",
                "unit": "Cel",
                "value_string": None,
                "interpretation": "H",
                "observation_datetime": "2024-02-10T08:35:00Z",
                "effective_date": "2024-02-10T08:35:00Z",
            },
            {
                "observation_id": "20000000-0000-0000-0000-000000000002",
                "patient_id": "00000000-0000-0000-0000-000000000001",
                "encounter_id": "10000000-0000-0000-0000-000000000001",
                "category": "laboratory",
                "loinc_code": "718-7",
                "loinc_display": "Hémoglobine [Masse/Volume] Sang",
                "value_quantity": 11.2,
                "value_numeric": 11.2,
                "value_unit": "g/dL",
                "unit": "g/dL",
                "value_string": None,
                "interpretation": "L",
                "observation_datetime": "2024-02-10T08:45:00Z",
                "effective_date": "2024-02-10T08:45:00Z",
            },
        ]
    )


# ==============================================================================
# Tier 1 : Catalogue d'Erreurs & Configuration YAML
# ==============================================================================


class TestDegradationCatalog:
    """Vérifie le catalogue déclaratif d'altérations et sa validation formelle."""

    def test_catalog_file_exists(self) -> None:
        """Vérifie l'existence du fichier de configuration YAML du catalogue."""
        if not CONFIG_RULES_PATH.exists():
            if IS_STRICT:
                pytest.fail(f"Catalogue YAML manquant : {CONFIG_RULES_PATH}")
            pytest.skip(f"Catalogue {CONFIG_RULES_PATH} en attente (Jalon M1)")
        assert CONFIG_RULES_PATH.is_file()

    def test_catalog_yaml_syntax(self) -> None:
        """Vérifie que le catalogue est un YAML valide et parsable."""
        if not CONFIG_RULES_PATH.exists():
            pytest.skip("Fichier de règles non encore créé")
        with open(CONFIG_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "Le catalogue YAML doit être un dictionnaire racine"
        assert "rules" in data, "La clé racine 'rules' est obligatoire dans le catalogue"
        assert isinstance(data["rules"], list), "'rules' doit être une liste"
        assert len(data["rules"]) > 0, "Le catalogue ne peut pas être vide"

    def test_catalog_all_mandatory_rules_present(self) -> None:
        """Vérifie que toutes les règles canoniques requises par DISPATCH.md sont présentes."""
        if not CONFIG_RULES_PATH.exists():
            pytest.skip("Fichier de règles non encore créé")
        with open(CONFIG_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        rules = data.get("rules", [])
        rule_ids = {r.get("rule_id") for r in rules if isinstance(r, dict)}

        missing = MANDATORY_RULE_IDS - rule_ids
        assert not missing, f"Règles obligatoires manquantes dans le catalogue : {sorted(missing)}"

    def test_catalog_unique_rule_ids(self) -> None:
        """Vérifie l'unicité absolue de chaque rule_id dans le catalogue."""
        if not CONFIG_RULES_PATH.exists():
            pytest.skip("Fichier de règles non encore créé")
        with open(CONFIG_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        rules = data.get("rules", [])
        ids = [r.get("rule_id") for r in rules if isinstance(r, dict)]
        assert len(ids) == len(set(ids)), f"Doublons d'identifiants de règles détectés : {ids}"

    def test_catalog_french_descriptions(self) -> None:
        """Vérifie que chaque règle possède une description non vide et explicite en français."""
        if not CONFIG_RULES_PATH.exists():
            pytest.skip("Fichier de règles non encore créé")
        with open(CONFIG_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for rule in data.get("rules", []):
            desc = rule.get("description", "")
            rule_id = rule.get("rule_id", "UNKNOWN")
            assert isinstance(desc, str) and len(desc.strip()) >= 10, (
                f"Règle {rule_id} : description en français invalide ou trop courte ('{desc}')"
            )

    def test_catalog_valid_target_tables_and_columns(self) -> None:
        """Vérifie que chaque règle cible des tables et colonnes valides du pipeline."""
        if not CONFIG_RULES_PATH.exists():
            pytest.skip("Fichier de règles non encore créé")
        with open(CONFIG_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        allowed_tables = set(CLINICAL_TABLES) | {"dhis2", "all"}
        for rule in data.get("rules", []):
            rule_id = rule.get("rule_id")
            tables = rule.get("target_tables", [])
            assert isinstance(tables, list) and len(tables) > 0, (
                f"Règle {rule_id} : target_tables doit être une liste non vide"
            )
            for t in tables:
                assert t in allowed_tables, f"Règle {rule_id} cible une table inconnue : {t}"
            cols = rule.get("target_columns", [])
            assert isinstance(cols, list), f"Règle {rule_id} : target_columns doit être une liste"

    def test_catalog_default_rates_bounded(self) -> None:
        """Vérifie que les taux d'erreur déclarés sont strictement dans [0.0, 1.0]."""
        if not CONFIG_RULES_PATH.exists():
            pytest.skip("Fichier de règles non encore créé")
        with open(CONFIG_RULES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for rule in data.get("rules", []):
            rate = rule.get("default_rate")
            rule_id = rule.get("rule_id")
            if rate is not None:
                assert isinstance(rate, (int, float)), (
                    f"Règle {rule_id} : taux non numérique ({rate})"
                )
                assert 0.0 <= rate <= 1.0, f"Règle {rule_id} : taux hors bornes [0.0, 1.0] ({rate})"

    def test_catalog_loader_api(self) -> None:
        """Vérifie l'API de chargement du catalogue (classe DegradationCatalog ou load_rules)."""
        cat_mod = _require_catalog_module()
        loader = getattr(cat_mod, "load_rules_catalog", None) or getattr(
            cat_mod, "load_catalog", None
        )
        if loader is None and hasattr(cat_mod, "DegradationCatalog"):
            catalog = cat_mod.DegradationCatalog()
        elif callable(loader):
            catalog = loader()
        else:
            if IS_STRICT:
                pytest.fail("Fonction de chargement du catalogue introuvable dans catalog.py")
            pytest.skip("Loader de catalogue non encore implémenté")

        # Vérification des méthodes de consultation
        assert hasattr(catalog, "get_rule") or hasattr(catalog, "rules"), (
            "Le catalogue doit exposer les règles"
        )
        if hasattr(catalog, "get_rule"):
            rule = catalog.get_rule("RULE-DATE-001")
            assert rule is not None, (
                "get_rule('RULE-DATE-001') doit renvoyer la règle correspondante"
            )


# ==============================================================================
# Tier 2 : Mutateurs Unitaires
# ==============================================================================


class TestUnitMutators:
    """Vérifie chaque fonction mutatrice individuelle."""

    def test_mutate_date_format_variations(self) -> None:
        """Vérifie la conversion ISO YYYY-MM-DD en formats mixtes (DD/MM/YYYY, DD-MM-YYYY, etc.)."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_date_format", None)
        if not callable(fn):
            pytest.skip("mutate_date_format non exportée")

        original_date = "1985-04-15"
        altered = fn(original_date, seed=42)
        assert isinstance(altered, str), "La date altérée doit être une chaîne"
        assert altered != original_date, (
            f"La date altérée doit différer de l'ISO standard ({altered})"
        )
        # Formats admissibles : 15/04/1985, 15-04-1985, 1985/04/15, 15.04.85, 15041985, etc.
        assert any(sep in altered for sep in ["/", "-", "."]) or len(altered) == 8, (
            f"Format de date non conforme aux variantes attendues : {altered}"
        )
        assert "15" in altered and "04" in altered, "Le jour et le mois doivent être conservés"

    def test_mutate_date_format_determinism(self) -> None:
        """Vérifie le déterminisme strict de mutate_date_format sous graine fixe."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_date_format", None)
        if not callable(fn):
            pytest.skip("mutate_date_format non exportée")

        d1 = fn("1990-12-31", seed=100)
        d2 = fn("1990-12-31", seed=100)
        assert d1 == d2, "Deux appels avec la même graine doivent produire le même format de date"

    def test_mutate_date_format_handles_none_or_empty(self) -> None:
        """Vérifie la tolérance aux valeurs nulles ou vides."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_date_format", None)
        if not callable(fn):
            pytest.skip("mutate_date_format non exportée")

        res_none = fn(None, seed=42)
        assert res_none is None or res_none == "", "None doit renvoyer None ou chaîne vide"

    def test_mutate_approximate_age(self) -> None:
        """Vérifie le remplacement d'une date de naissance par un âge approximatif textuel."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_approximate_age", None)
        if not callable(fn):
            pytest.skip("mutate_approximate_age non exportée")

        # Test avec date ISO
        res = fn("1985-04-15", seed=42)
        assert isinstance(res, str)
        res_lower = res.lower()
        # Doit contenir "ans" ou "env" ou "~" ou "vers"
        assert any(kw in res_lower for kw in ["an", "env", "~", "vers", "né"]), (
            f"L'âge approximatif généré doit être textuel et réaliste : '{res}'"
        )

        # Test avec entier
        res_int = fn(35, seed=42)
        assert isinstance(res_int, str)
        assert any(kw in res_int.lower() for kw in ["an", "env", "~", "vers"]), (
            f"L'âge approximatif depuis entier doit être textuel : '{res_int}'"
        )

    def test_mutate_name_spelling_phonetic_and_typos(self) -> None:
        """Vérifie les coquilles typographiques et variantes phonétiques togolaises."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_name_spelling", None)
        if not callable(fn):
            pytest.skip("mutate_name_spelling non exportée")

        names = ["Mensah", "Lawson", "Adjamagbo", "Ametowobla", "Tchagbele"]
        for name in names:
            altered = fn(name, seed=42)
            assert isinstance(altered, str)
            assert altered != name, f"Le nom {name} doit être altéré (obtenu : {altered})"
            # Vérifie qu'il y a une ressemblance (distance raisonnable)
            assert len(altered) >= 3, f"Le nom altéré est trop court : {altered}"

    def test_mutate_name_spelling_determinism(self) -> None:
        """Vérifie le déterminisme sous graine de mutate_name_spelling."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_name_spelling", None)
        if not callable(fn):
            pytest.skip("mutate_name_spelling non exportée")

        r1 = fn("Lawson", seed=77)
        r2 = fn("Lawson", seed=77)
        assert r1 == r2, "Même graine = même altération de patronyme"

    def test_mutate_strip_accents(self) -> None:
        """Vérifie la suppression des accents et diacritiques."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_strip_accents", None)
        if not callable(fn):
            pytest.skip("mutate_strip_accents non exportée")

        samples = [
            ("Hôpital", "Hopital"),
            ("Émile", "Emile"),
            ("Adjoubé", "Adjoube"),
            ("Koffi Eugène", "Koffi Eugene"),
            ("Tsévié", "Tsevie"),
        ]
        for original, expected in samples:
            res = fn(original)
            assert res == expected, (
                f"Suppression d'accents erronée pour '{original}' : obtenu '{res}' attendu '{expected}'"
            )

    def test_mutate_invert_name_order(self) -> None:
        """Vérifie l'inversion de l'ordre nom / prénom."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_invert_name_order", None)
        if not callable(fn):
            pytest.skip("mutate_invert_name_order non exportée")

        # Test avec deux arguments ou une chaîne composite
        try:
            res = fn(family_name="Mensah", given_name="Koffi", seed=42)
            assert ("Koffi" in str(res)) and ("Mensah" in str(res))
        except TypeError:
            res = fn("Mensah Koffi", seed=42)
            assert res == "Koffi Mensah" or ("Koffi" in res and "Mensah" in res)

    def test_mutate_clinical_freetext(self) -> None:
        """Vérifie la conversion de diagnostics formels en libellés libres ou abréviations familières."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_clinical_freetext", None)
        if not callable(fn):
            pytest.skip("mutate_clinical_freetext non exportée")

        terms = [
            ("Paludisme grave à Plasmodium falciparum", ["palu", "accès", "palustre"]),
            ("Hypertension artérielle essentielle", ["hta", "tension"]),
            ("Gastro-entérite aiguë", ["gea", "gastro", "diarrhee", "diarrhée"]),
            ("Infection respiratoire aiguë", ["ira", "infection", "bronchite"]),
        ]
        for term, expected_keywords in terms:
            res = fn(term, seed=42)
            assert isinstance(res, str)
            assert res != term, f"Le terme formel '{term}' doit être transformé"
            res_lower = res.lower()
            assert any(kw in res_lower for kw in expected_keywords), (
                f"Libellé clinique libre '{res}' ne contient aucun des mots-clés attendus {expected_keywords}"
            )

    def test_mutate_measurement_separator(self) -> None:
        """Vérifie le remplacement du point décimal par la virgule."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_measurement_separator", None)
        if not callable(fn):
            pytest.skip("mutate_measurement_separator non exportée")

        assert fn(38.5) == "38,5" or fn("38.5") == "38,5"
        assert fn(12.0) == "12,0" or fn("12.0") == "12,0"

    def test_mutate_measurement_unit(self) -> None:
        """Vérifie l'altération ou la suppression des unités de mesure."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_measurement_unit", None)
        if not callable(fn):
            pytest.skip("mutate_measurement_unit non exportée")

        altered = fn("g/dL", seed=42)
        # Peut être g/l, g/L, "", None, etc.
        assert altered != "g/dL", "L'unité standard UCUM doit être altérée ou supprimée"

    def test_mutate_sentinel(self) -> None:
        """Vérifie l'injection de valeurs sentinelles réalistes (-1, 999, NA, ND)."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_sentinel", None)
        if not callable(fn):
            pytest.skip("mutate_sentinel non exportée")

        sentinels = {fn("original", seed=s) for s in range(20)}
        sentinels_str = {str(s).upper() for s in sentinels}
        valid_sentinels = {"-1", "999", "-999", "9999", "NA", "ND", "N/A", "INCONNU", "NONE"}
        assert sentinels_str.intersection(valid_sentinels), (
            f"Les valeurs sentinelles produites {sentinels_str} ne contiennent aucun code sentinelle standard"
        )

    def test_mutate_missing(self) -> None:
        """Vérifie l'injection de valeurs manquantes (None ou chaîne vide)."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_missing", None)
        if not callable(fn):
            pytest.skip("mutate_missing non exportée")

        res = fn("valeur_existante")
        assert res is None or res == "" or pd.isna(res), (
            f"mutate_missing doit renvoyer None, vide ou NA (obtenu : {res})"
        )

    def test_mutate_encoding_mojibake(self) -> None:
        """Vérifie la simulation d'altération d'encodage Mojibake (UTF-8 lu en Latin-1)."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_encoding_mojibake", None)
        if not callable(fn):
            pytest.skip("mutate_encoding_mojibake non exportée")

        text = "Hôpital de Tsévié"
        altered = fn(text, seed=42)
        assert isinstance(altered, str)
        # Mojibake typique : é -> Ã©, ô -> Ã´
        assert "Ã" in altered or altered != text, (
            f"Le texte doit présenter une altération d'encodage (obtenu : '{altered}')"
        )

    def test_mutate_facility_name(self) -> None:
        """Vérifie la génération de variantes pour les structures sanitaires togolaises."""
        mut_mod = _require_mutators_module()
        fn = getattr(mut_mod, "mutate_facility_name", None)
        if not callable(fn):
            pytest.skip("mutate_facility_name non exportée")

        name = "Centre Médico-Social d'Adidogomé"
        altered = fn(name, seed=42)
        assert isinstance(altered, str)
        assert altered != name
        assert any(kw in altered for kw in ["CMS", "Adidogome", "Adidogomé", "Centre"]), (
            f"Variante de structure sanitaire inattendue : '{altered}'"
        )


# ==============================================================================
# Tier 3 : Journal d'Altérations & Réversibilité (Corrigé de Référence)
# ==============================================================================


class TestAlterationLog:
    """Vérifie la structure, la sérialisation et la complétude du journal d'altérations."""

    def test_alteration_record_schema(self) -> None:
        """Vérifie le modèle Pydantic AlterationRecord."""
        schemas_mod = _require_schemas_module()
        record_cls = getattr(schemas_mod, "AlterationRecord", None)
        if record_cls is None:
            pytest.skip("AlterationRecord non défini dans schemas.py")

        rec = record_cls(
            alteration_id=str(uuid.uuid4()),
            table_name="patients",
            row_id="00000000-0000-0000-0000-000000000001",
            column_name="birth_date",
            original_value="1985-04-15",
            altered_value="15/04/1985",
            rule_id="RULE-DATE-001",
            description="Format de date altéré en DD/MM/YYYY",
        )
        assert rec.table_name == "patients"
        assert rec.rule_id == "RULE-DATE-001"
        assert _is_valid_uuid(rec.alteration_id)

    def test_alteration_log_pyarrow_schema(self) -> None:
        """Vérifie la conformité du schéma PyArrow ALTERATION_LOG_SCHEMA."""
        schemas_mod = _require_schemas_module()
        schema = getattr(schemas_mod, "ALTERATION_LOG_SCHEMA", None)
        if schema is None:
            pytest.skip("ALTERATION_LOG_SCHEMA non défini dans schemas.py")

        assert isinstance(schema, pa.Schema)
        expected_fields = [
            "alteration_id",
            "table_name",
            "row_id",
            "column_name",
            "original_value",
            "altered_value",
            "rule_id",
            "description",
        ]
        schema_names = schema.names
        for field in expected_fields:
            assert field in schema_names, f"Champ obligatoire '{field}' absent du schéma PyArrow"

    def test_alteration_log_serialization_parquet_and_jsonl(self, tmp_path: Path) -> None:
        """Vérifie que le journal d'altérations peut être sérialisé et relu en Parquet et JSONL."""
        schemas_mod = _require_schemas_module()
        record_cls = getattr(schemas_mod, "AlterationRecord", None)
        if record_cls is None:
            pytest.skip("AlterationRecord non disponible")

        records = [
            record_cls(
                alteration_id=str(uuid.uuid4()),
                table_name="patients",
                row_id=f"00000000-0000-0000-0000-00000000000{i}",
                column_name="family_name",
                original_value=f"Original_{i}",
                altered_value=f"Altered_{i}",
                rule_id="RULE-NAME-001",
                description="Coquille patronymique",
            )
            for i in range(1, 4)
        ]

        df = pd.DataFrame([r.model_dump() for r in records])

        # 1. Sauvegarde et relecture Parquet
        parquet_path = tmp_path / "alterations_log.parquet"
        df.to_parquet(parquet_path, index=False)
        assert parquet_path.exists()
        reloaded_parquet = pd.read_parquet(parquet_path)
        assert len(reloaded_parquet) == 3
        assert list(reloaded_parquet["column_name"]) == ["family_name"] * 3

        # 2. Sauvegarde et relecture JSONL
        jsonl_path = tmp_path / "alterations_log.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.model_dump_json() + "\n")
        assert jsonl_path.exists()

        reloaded_jsonl = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    reloaded_jsonl.append(json.loads(line))
        assert len(reloaded_jsonl) == 3
        assert reloaded_jsonl[0]["rule_id"] == "RULE-NAME-001"

    def test_alteration_log_reversibility_corrigé(self, sample_patient_df: pd.DataFrame) -> None:
        """Vérifie que le journal d'altérations permet de recalculer 100% de la Vérité Terrain."""
        # Simulation d'un état dégradé et d'un journal associé
        original_df = sample_patient_df.copy()
        degraded_df = sample_patient_df.copy()

        # Applique une altération simulée
        row_id = degraded_df.iloc[0]["patient_id"]
        orig_val = degraded_df.iloc[0]["family_name"]
        altered_val = "Mensa"
        degraded_df.loc[degraded_df["patient_id"] == row_id, "family_name"] = altered_val

        # Journal associé
        log_entry = {
            "alteration_id": str(uuid.uuid4()),
            "table_name": "patients",
            "row_id": row_id,
            "column_name": "family_name",
            "original_value": orig_val,
            "altered_value": altered_val,
            "rule_id": "RULE-NAME-001",
            "description": "Suppression h final",
        }
        log_df = pd.DataFrame([log_entry])

        # Processus de reconstitution inverse
        reconstructed_df = degraded_df.copy()
        for _, row in log_df.iterrows():
            mask = reconstructed_df["patient_id"] == row["row_id"]
            reconstructed_df.loc[mask, row["column_name"]] = row["original_value"]

        # L'état reconstitué doit être rigoureusement identique à l'original
        pd.testing.assert_frame_equal(original_df, reconstructed_df)


# ==============================================================================
# Tier 4 : Moteur de Dégradation Global
# ==============================================================================


class TestDegradationEngine:
    """Vérifie l'exécution globale du moteur d'altération contrôlée."""

    def test_engine_execution_on_ground_truth(self, tmp_path: Path) -> None:
        """Vérifie l'exécution du moteur sur les 6 tables de Vérité Terrain réelles."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.15, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            if IS_STRICT:
                pytest.fail("Moteur de dégradation non exporté")
            pytest.skip("Moteur de dégradation en attente d'implémentation")

        out_dir = tmp_path / "degraded_run"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Exécution avec rate=0.15 et seed=42
        runner(source_dir=TRUTH_DIR, output_dir=out_dir, rate=0.15, seed=42)

        # Vérifie que les 6 tables cliniques Parquet sont produites
        for table_name in CLINICAL_TABLES:
            out_file = out_dir / f"{table_name}.parquet"
            assert out_file.exists(), (
                f"Table dégradée manquante dans la sortie : {table_name}.parquet"
            )
            df = pd.read_parquet(out_file)
            assert not df.empty, f"Table dégradée vide : {table_name}.parquet"

        # Vérifie la présence du journal d'altérations
        log_parquet = out_dir / "alterations_log.parquet"
        assert log_parquet.exists(), "alterations_log.parquet obligatoire manquant"
        log_df = pd.read_parquet(log_parquet)
        assert not log_df.empty, "Le journal d'altérations ne doit pas être vide pour rate=0.15"

    def test_engine_target_rate_adherence(self, tmp_path: Path) -> None:
        """Vérifie que le taux d'erreur mesuré correspond au paramètre rate +/- 5%."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.15, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            pytest.skip("Moteur non disponible")

        out_dir = tmp_path / "rate_check"
        target_rate = 0.15
        runner(source_dir=TRUTH_DIR, output_dir=out_dir, rate=target_rate, seed=42)

        log_df = pd.read_parquet(out_dir / "alterations_log.parquet")
        orig_patients = pd.read_parquet(TRUTH_DIR / "patients.parquet")

        # Nombre de patients distincts touchés par au moins une altération
        patient_log = log_df[log_df["table_name"] == "patients"]
        altered_patient_ids = set(patient_log["row_id"].unique())
        measured_rate = len(altered_patient_ids) / len(orig_patients)

        # Marge de tolérance de +/- 5% (donc entre 10% et 20%)
        margin = 0.05
        lower_bound = max(0.0, target_rate - margin)
        upper_bound = min(1.0, target_rate + margin)
        assert lower_bound <= measured_rate <= upper_bound, (
            f"Taux mesuré {measured_rate * 100:.2f}% hors de la fenêtre tolérée "
            f"[{lower_bound * 100:.1f}%, {upper_bound * 100:.1f}%] pour cible {target_rate * 100:.1f}%"
        )

    def test_engine_zero_rate(self, tmp_path: Path) -> None:
        """Vérifie que pour rate=0.0, aucune altération n'est injectée et le journal est vide."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.0, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            pytest.skip("Moteur non disponible")

        out_dir = tmp_path / "zero_rate"
        runner(source_dir=TRUTH_DIR, output_dir=out_dir, rate=0.0, seed=42)

        log_path = out_dir / "alterations_log.parquet"
        if log_path.exists():
            log_df = pd.read_parquet(log_path)
            assert len(log_df) == 0, (
                f"Pour rate=0.0, le journal doit être vide (trouvé {len(log_df)} lignes)"
            )

    def test_engine_patient_duplicates_injection(self, tmp_path: Path) -> None:
        """Vérifie l'injection de doublons patients pour Splink avec identifiants distincts."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.15, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            pytest.skip("Moteur non disponible")

        out_dir = tmp_path / "duplicates_check"
        runner(source_dir=TRUTH_DIR, output_dir=out_dir, rate=0.15, seed=42)

        log_df = pd.read_parquet(out_dir / "alterations_log.parquet")
        dupl_log = log_df[log_df["rule_id"] == "RULE-DUPL-001"]

        assert not dupl_log.empty, (
            "Des doublons de patients (RULE-DUPL-001) doivent être injectés pour l'Étape 8 Splink"
        )

        degraded_patients = pd.read_parquet(out_dir / "patients.parquet")
        orig_patients = pd.read_parquet(TRUTH_DIR / "patients.parquet")

        # La table dégradée contient les patients originaux + les doublons injectés
        assert len(degraded_patients) >= len(orig_patients), (
            "La table dégradée doit contenir au moins autant de lignes que la vérité terrain"
        )

        # Vérifie que les IDs de tous les patients sont uniques (identifiants distincts)
        assert degraded_patients["patient_id"].is_unique, (
            "Les doublons patients doivent posséder des identifiants patient_id distincts"
        )

    def test_engine_bit_for_bit_determinism(self, tmp_path: Path) -> None:
        """Vérifie la reproductibilité binaire bit-à-bit absolue sous même graine (seed=42)."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.15, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            pytest.skip("Moteur non disponible")

        dir_a = tmp_path / "run_a"
        dir_b = tmp_path / "run_b"

        runner(source_dir=TRUTH_DIR, output_dir=dir_a, rate=0.15, seed=42)
        runner(source_dir=TRUTH_DIR, output_dir=dir_b, rate=0.15, seed=42)

        for filename in [
            "patients.parquet",
            "encounters.parquet",
            "conditions.parquet",
            "observations.parquet",
            "prescriptions.parquet",
            "immunizations.parquet",
            "alterations_log.parquet",
        ]:
            file_a = dir_a / filename
            file_b = dir_b / filename
            assert file_a.exists() and file_b.exists()
            sha_a = _compute_file_sha256(file_a)
            sha_b = _compute_file_sha256(file_b)
            assert sha_a == sha_b, (
                f"Déterminisme bit-à-bit violé pour {filename} (seed=42) : SHA A={sha_a} != B={sha_b}"
            )

    def test_engine_seed_divergence(self, tmp_path: Path) -> None:
        """Vérifie la divergence des résultats entre graines distinctes (seed=42 vs seed=43)."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.15, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            pytest.skip("Moteur non disponible")

        dir_42 = tmp_path / "run_42"
        dir_43 = tmp_path / "run_43"

        runner(source_dir=TRUTH_DIR, output_dir=dir_42, rate=0.15, seed=42)
        runner(source_dir=TRUTH_DIR, output_dir=dir_43, rate=0.15, seed=43)

        sha_42 = _compute_file_sha256(dir_42 / "alterations_log.parquet")
        sha_43 = _compute_file_sha256(dir_43 / "alterations_log.parquet")
        assert sha_42 != sha_43, (
            "Deux graines distinctes doivent produire des journaux d'altérations différents"
        )

    def test_engine_invalid_rate_rejection(self, tmp_path: Path) -> None:
        """Vérifie le rejet strict des taux hors bornes (< 0 ou > 1)."""
        eng_mod = _require_engine_module()
        runner = getattr(eng_mod, "apply_degradation", None) or getattr(
            eng_mod, "degrade_dataset", None
        )
        if runner is None and hasattr(eng_mod, "DegradationEngine"):
            engine_cls = eng_mod.DegradationEngine
            engine = engine_cls(rate=0.15, seed=42)
            runner = engine.run if hasattr(engine, "run") else engine.degrade_dataset
        elif not callable(runner):
            pytest.skip("Moteur non disponible")

        out_dir = tmp_path / "invalid_rate"
        with pytest.raises((ValueError, Exception)):
            runner(source_dir=TRUTH_DIR, output_dir=out_dir, rate=-0.1, seed=42)

        with pytest.raises((ValueError, Exception)):
            runner(source_dir=TRUTH_DIR, output_dir=out_dir, rate=1.5, seed=42)


# ==============================================================================
# Tier 5 : Exportateurs Multi-Formats
# ==============================================================================


class TestMultiFormatExporters:
    """Vérifie la génération des jeux de données dégradés dans les formats préparatoires (Étape 5)."""

    def test_export_excel_multi_sheets(
        self,
        tmp_path: Path,
        sample_patient_df: pd.DataFrame,
        sample_encounter_df: pd.DataFrame,
        sample_observation_df: pd.DataFrame,
    ) -> None:
        """Vérifie l'export d'un classeur Excel .xlsx valide multi-onglets."""
        exp_mod = _require_exporters_module()
        export_fn = getattr(exp_mod, "export_degraded_excel", None) or getattr(
            exp_mod, "export_excel", None
        )
        if not callable(export_fn):
            pytest.skip("export_degraded_excel non exportée")

        tables = {
            "patients": sample_patient_df,
            "encounters": sample_encounter_df,
            "observations": sample_observation_df,
        }
        excel_path = tmp_path / "degraded_cohort.xlsx"
        res_path = export_fn(tables, output_path=excel_path)
        actual_path = Path(res_path) if res_path else excel_path

        assert actual_path.exists(), f"Fichier Excel non créé : {actual_path}"

        # Ouverture et vérification avec openpyxl
        wb = openpyxl.load_workbook(actual_path)
        sheet_names = wb.sheetnames
        for table_name in ["patients", "encounters", "observations"]:
            assert table_name in sheet_names, (
                f"Feuille Excel '{table_name}' manquante dans le classeur"
            )

        # Vérifie la présence de lignes non vides
        ws_patients = wb["patients"]
        assert ws_patients.max_row >= 2, (
            "La feuille patients doit contenir au moins 2 lignes (entête + 1)"
        )
        headers = [
            ws_patients.cell(row=1, column=c).value for c in range(1, ws_patients.max_column + 1)
        ]
        assert "patient_id" in headers or "family_name" in headers

    def test_export_csv_proprietary_semicolon(
        self,
        tmp_path: Path,
        sample_patient_df: pd.DataFrame,
    ) -> None:
        """Vérifie l'export CSV propriétaire avec délimiteur point-virgule et encodage."""
        exp_mod = _require_exporters_module()
        export_fn = getattr(exp_mod, "export_degraded_csv", None) or getattr(
            exp_mod, "export_csv", None
        )
        if not callable(export_fn):
            pytest.skip("export_degraded_csv non exportée")

        csv_dir = tmp_path / "csv_out"
        csv_dir.mkdir(parents=True, exist_ok=True)
        res = export_fn({"patients": sample_patient_df}, output_dir=csv_dir, sep=";")

        patients_csv = csv_dir / "patients.csv"
        assert patients_csv.exists() or (res and Path(res[0]).exists())
        target_csv = patients_csv if patients_csv.exists() else Path(res[0])

        # Vérifie la présence du délimiteur ';'
        with open(target_csv, encoding="utf-8") as f:
            header_line = f.readline()
            assert ";" in header_line, (
                f"Le fichier CSV doit utiliser le séparateur ';' : '{header_line}'"
            )

        # Vérifie qu'on peut relire avec pandas
        df_read = pd.read_csv(target_csv, sep=";")
        assert len(df_read) == len(sample_patient_df)

    def test_export_fhir_degraded_json(
        self,
        tmp_path: Path,
        sample_patient_df: pd.DataFrame,
    ) -> None:
        """Vérifie l'export JSON FHIR dégradé avec anomalies structurelles traçables."""
        exp_mod = _require_exporters_module()
        export_fn = getattr(exp_mod, "export_degraded_fhir", None) or getattr(
            exp_mod, "export_fhir", None
        )
        if not callable(export_fn):
            pytest.skip("export_degraded_fhir non exportée")

        fhir_dir = tmp_path / "fhir_out"
        fhir_dir.mkdir(parents=True, exist_ok=True)
        export_fn(tables={"patients": sample_patient_df}, output_dir=fhir_dir)

        # Vérifie la création d'au moins un fichier JSON
        json_files = list(fhir_dir.glob("*.json"))
        assert len(json_files) > 0, "Aucun fichier JSON/FHIR dégradé produit"
        with open(json_files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Le fichier FHIR doit être un objet JSON valide"

    def test_export_dhis2_degraded_aggregates(self, tmp_path: Path) -> None:
        """Vérifie l'export des agrégats DHIS2 dataValueSets altérés."""
        exp_mod = _require_exporters_module()
        export_fn = getattr(exp_mod, "export_degraded_dhis2", None) or getattr(
            exp_mod, "export_dhis2", None
        )
        if not callable(export_fn):
            pytest.skip("export_degraded_dhis2 non exportée")

        dhis2_dir = tmp_path / "dhis2_out"
        dhis2_dir.mkdir(parents=True, exist_ok=True)

        if not TRUTH_DHIS2_PARQUET.exists():
            pytest.skip("Vérité terrain DHIS2 non disponible")

        df_dhis2 = pd.read_parquet(TRUTH_DHIS2_PARQUET)
        export_fn(dhis2_data=df_dhis2, output_dir=dhis2_dir)

        # Doit produire un fichier Parquet ou JSON altéré
        produced = list(dhis2_dir.glob("*.*"))
        assert len(produced) > 0, "Aucun agrégat DHIS2 dégradé exporté"
