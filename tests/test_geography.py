"""Tests E2E de validation du référentiel géographique et des formations sanitaires du Togo (Étape 2).

Conforme aux spécifications R1 d'ORIGINAL_REQUEST.md, PROJECT.md, ADR D-08 et VAL-001.
Couvre les Tiers 1 à 4 :
- Tier 1 : Schéma Parquet, présence des 6 régions, 44 districts et 4 niveaux de la pyramide.
- Tier 2 : UUID v5 déterministe, zéro valeur nulle, unicité stricte de (district, normalized_name), règles de normalisation.
- Tier 3 : Intégrité hiérarchique parent-enfant (pays -> région -> district -> FOSA), zéro district orphelin.
- Tier 4 : Performance de filtrage/requêtage, statut actif, robustesse du validateur sur données corrompues.
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import pytest

GEOGRAPHY_PARQUET_PATH = Path("data/reference/togo_health_geography.parquet")
MODULE_PATH = Path("src/terminology/geography.py")
IS_STRICT = os.environ.get("STRICT_E2E") == "1"

# Regex stricte UUID v5 RFC 4122 (version '5' au 13e caractère hex, variant '8','9','a','b' au 17e)
UUID_V5_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# 6 Régions sanitaires officielles du Togo (ADR D-08, VAL-001)
EXPECTED_REGIONS: dict[str, str] = {
    "TG-SAV": "Savanes",
    "TG-KAR": "Kara",
    "TG-CEN": "Centrale",
    "TG-PLA": "Plateaux",
    "TG-MAR": "Maritime",
    "TG-LOM": "Grand Lomé",
}

# Découpage officiel des 44 districts sanitaires (ADR D-08)
EXPECTED_DISTRICTS_BY_REGION: dict[str, set[str]] = {
    "TG-SAV": {
        "TG-SAV-CIN",
        "TG-SAV-KPE",
        "TG-SAV-KPO",
        "TG-SAV-OTI",
        "TG-SAV-OTS",
        "TG-SAV-TAN",
        "TG-SAV-TON",
    },
    "TG-KAR": {
        "TG-KAR-ASS",
        "TG-KAR-BAS",
        "TG-KAR-BIN",
        "TG-KAR-DAN",
        "TG-KAR-DOU",
        "TG-KAR-KER",
        "TG-KAR-KOZ",
    },
    "TG-CEN": {
        "TG-CEN-BLI",
        "TG-CEN-MO",
        "TG-CEN-SOT",
        "TG-CEN-TCH",
        "TG-CEN-TCJ",
    },
    "TG-PLA": {
        "TG-PLA-AGU",
        "TG-PLA-AKE",
        "TG-PLA-AMO",
        "TG-PLA-ANI",
        "TG-PLA-DAN",
        "TG-PLA-EST",
        "TG-PLA-HAH",
        "TG-PLA-KLO",
        "TG-PLA-KPE",
        "TG-PLA-MOY",
        "TG-PLA-OGU",
        "TG-PLA-WAW",
    },
    "TG-MAR": {
        "TG-MAR-AVE",
        "TG-MAR-BAS",
        "TG-MAR-LAC",
        "TG-MAR-VO",
        "TG-MAR-YOT",
        "TG-MAR-ZIO",
    },
    "TG-LOM": {
        "TG-LOM-AGO",
        "TG-LOM-GOL",
        "TG-LOM-DS1",
        "TG-LOM-DS2",
        "TG-LOM-DS3",
        "TG-LOM-DS4",
        "TG-LOM-DS5",
    },
}

ALL_44_DISTRICT_CODES = {d for dists in EXPECTED_DISTRICTS_BY_REGION.values() for d in dists}


def _check_parquet_exists() -> bool:
    if not GEOGRAPHY_PARQUET_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Fichier Parquet obligatoire manquant : {GEOGRAPHY_PARQUET_PATH}")
        pytest.skip(f"Fichier {GEOGRAPHY_PARQUET_PATH} non encore généré (Jalon M2 en attente)")
    return True


@pytest.fixture
def geography_df() -> pd.DataFrame:
    """Charge le fichier Parquet de référence géographique en DataFrame pandas."""
    _check_parquet_exists()
    df = pd.read_parquet(GEOGRAPHY_PARQUET_PATH)
    assert not df.empty, f"Le fichier Parquet {GEOGRAPHY_PARQUET_PATH} est vide"
    return df


@pytest.fixture
def geography_module():
    """Importe le module src.terminology.geography si disponible."""
    if not MODULE_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Module obligatoire manquant : {MODULE_PATH}")
        pytest.skip(f"Module {MODULE_PATH} non encore implémenté (Jalon M2 en attente)")
    try:
        import src.terminology.geography as geo

        return geo
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Erreur d'import de {MODULE_PATH} : {exc}")
        pytest.skip(f"Import {MODULE_PATH} impossible : {exc}")


# ==============================================================================
# Tier 1 : Couverture des fonctionnalités (Schéma, Régions, Districts, Niveaux)
# ==============================================================================


def test_tier1_geography_schema(geography_df: pd.DataFrame) -> None:
    """Vérifie que la table Parquet contient toutes les colonnes requises."""
    required_columns = {
        "facility_id",
        "facility_code",
        "name",
        "normalized_name",
        "category",
        "pyramid_level",
        "district_code",
        "district_name",
        "region_code",
        "region_name",
        "country_code",
        "country_name",
    }
    missing = required_columns - set(geography_df.columns)
    assert not missing, f"Colonnes obligatoires manquantes dans le Parquet : {missing}"


def test_tier1_exactly_six_regions(geography_df: pd.DataFrame) -> None:
    """Vérifie la présence exacte des 6 régions sanitaires officielles de l'ADR D-08."""
    present_region_codes = set(geography_df["region_code"].unique())
    assert present_region_codes == set(EXPECTED_REGIONS.keys()), (
        f"Régions inattendues. Attendu {set(EXPECTED_REGIONS.keys())}, obtenu {present_region_codes}"
    )

    assert geography_df["region_code"].nunique() == 6, (
        f"Attendu exactement 6 régions, trouvé {geography_df['region_code'].nunique()}"
    )


def test_tier1_exactly_forty_four_districts(geography_df: pd.DataFrame) -> None:
    """Vérifie la présence exacte des 44 districts sanitaires de l'ADR D-08."""
    present_district_codes = set(geography_df["district_code"].unique())
    assert present_district_codes == ALL_44_DISTRICT_CODES, (
        f"Districts discordants. Manquants : {ALL_44_DISTRICT_CODES - present_district_codes}, En trop : {present_district_codes - ALL_44_DISTRICT_CODES}"
    )

    assert geography_df["district_code"].nunique() == 44, (
        f"Attendu exactement 44 districts, trouvé {geography_df['district_code'].nunique()}"
    )


def test_tier1_four_pyramid_levels(geography_df: pd.DataFrame) -> None:
    """Vérifie la présence des 4 niveaux opérationnels de la pyramide sanitaire."""
    levels = set(geography_df["pyramid_level"].unique())
    assert {1, 2, 3, 4}.issubset(levels), (
        f"Niveaux de pyramide manquants : {{1, 2, 3, 4}} vs {levels}"
    )

    categories = set(geography_df["category"].str.upper().unique())
    # Doit au moins contenir les types clés
    assert "CHU" in categories, "Catégorie CHU manquante (Niveau 4)"
    assert "CHR" in categories, "Catégorie CHR manquante (Niveau 3)"
    assert any(c in categories for c in ("HOSPITAL", "CHP")), (
        "Catégorie Hôpital de District / CHP manquante (Niveau 2)"
    )
    assert any(c in categories for c in ("CMS", "USP")), "Catégorie CMS ou USP manquante (Niveau 1)"


# ==============================================================================
# Tier 2 : Cas Limites et Contraintes d'Intégrité Stricte
# ==============================================================================


def test_tier2_facility_id_is_uuid_v5(geography_df: pd.DataFrame) -> None:
    """Vérifie que chaque facility_id est un UUID v5 déterministe conforme RFC 4122."""
    for fid in geography_df["facility_id"]:
        assert isinstance(fid, str), f"L'identifiant {fid} doit être une chaîne"
        assert UUID_V5_REGEX.match(fid), (
            f"L'identifiant {fid} n'est pas un UUID v5 valide (RFC 4122)"
        )


def test_tier2_zero_nulls_in_essential_columns(
    geography_df: pd.DataFrame,
) -> None:
    """Vérifie l'absence absolue de valeurs nulles ou vides dans les colonnes critiques."""
    essential_cols = [
        "facility_id",
        "facility_code",
        "name",
        "normalized_name",
        "category",
        "pyramid_level",
        "district_code",
        "region_code",
        "country_code",
    ]
    for col in essential_cols:
        null_count = geography_df[col].isnull().sum()
        assert null_count == 0, f"Colonne '{col}' contient {null_count} valeurs nulles"
        empty_count = (geography_df[col].astype(str).str.strip() == "").sum()
        assert empty_count == 0, f"Colonne '{col}' contient {empty_count} chaînes vides"


def test_tier2_facility_codes_are_unique(geography_df: pd.DataFrame) -> None:
    """Vérifie l'unicité globale des codes d'établissements de santé."""
    duplicated = geography_df[geography_df["facility_code"].duplicated()]
    assert duplicated.empty, (
        f"Codes d'établissements en doublon : {duplicated['facility_code'].tolist()}"
    )


def test_tier2_unique_normalized_name_per_district(
    geography_df: pd.DataFrame,
) -> None:
    """Vérifie qu'aucun doublon de nom normalisé n'existe au sein d'un même district."""
    duplicates = geography_df[
        geography_df.duplicated(subset=["district_code", "normalized_name"], keep=False)
    ]
    assert duplicates.empty, (
        f"Doublons de noms normalisés au sein d'un district détectés :\n"
        f"{duplicates[['district_code', 'normalized_name', 'name']]}"
    )


def test_tier2_normalized_name_rules(geography_df: pd.DataFrame) -> None:
    """Vérifie que normalized_name est en minuscules et sans diacritiques/accents."""
    for norm_name in geography_df["normalized_name"]:
        assert norm_name == norm_name.lower(), (
            f"Le nom normalisé '{norm_name}' doit être en minuscules"
        )
        # Vérifie l'absence de diacritiques (combining characters)
        decomposed = unicodedata.normalize("NFD", norm_name)
        has_combining = any(unicodedata.combining(c) for c in decomposed)
        assert not has_combining, (
            f"Le nom normalisé '{norm_name}' contient des accents ou diacritiques"
        )
        assert not norm_name.startswith(" ") and not norm_name.endswith(" "), (
            f"Le nom normalisé '{norm_name}' contient des espaces superflus"
        )


# ==============================================================================
# Tier 3 : Intégrité Transverse et Hiérarchie Sanitaire
# ==============================================================================


def test_tier3_district_to_region_parent_links(
    geography_df: pd.DataFrame,
) -> None:
    """Vérifie que chaque district_code est associé à sa région légitime sans orphelin."""
    for _, row in geography_df.iterrows():
        reg_code = row["region_code"]
        dist_code = row["district_code"]
        assert reg_code in EXPECTED_DISTRICTS_BY_REGION, f"Région inconnue : {reg_code}"
        assert dist_code in EXPECTED_DISTRICTS_BY_REGION[reg_code], (
            f"Le district {dist_code} n'appartient pas à la région {reg_code}"
        )


def test_tier3_country_is_strictly_togo(geography_df: pd.DataFrame) -> None:
    """Vérifie que l'entité pays est uniformément Togo (TG)."""
    assert set(geography_df["country_code"].unique()) == {"TG"}, (
        f"country_code invalide : {geography_df['country_code'].unique()}"
    )
    assert set(geography_df["country_name"].unique()) == {"Togo"}, (
        f"country_name invalide : {geography_df['country_name'].unique()}"
    )


def test_tier3_pyramid_level_consistency(geography_df: pd.DataFrame) -> None:
    """Vérifie la cohérence stricte entre catégorie d'établissement et niveau de pyramide."""
    for _, row in geography_df.iterrows():
        cat = str(row["category"]).upper()
        lvl = int(row["pyramid_level"])
        if cat == "CHU":
            assert lvl == 4, f"CHU doit être de niveau 4, obtenu {lvl} pour {row['name']}"
        elif cat == "CHR":
            assert lvl == 3, f"CHR doit être de niveau 3, obtenu {lvl} pour {row['name']}"
        elif cat in ("HOSPITAL", "CHP"):
            assert lvl == 2, (
                f"Hôpital de district doit être de niveau 2, obtenu {lvl} pour {row['name']}"
            )
        elif cat in ("CMS", "USP"):
            assert lvl == 1, f"CMS/USP doit être de niveau 1, obtenu {lvl} pour {row['name']}"


def test_tier3_no_district_without_facilities(
    geography_df: pd.DataFrame,
) -> None:
    """Vérifie que chacun des 44 districts dispose d'au moins une formation sanitaire."""
    district_counts = geography_df["district_code"].value_counts()
    for d_code in ALL_44_DISTRICT_CODES:
        assert d_code in district_counts, (
            f"District orphelin : {d_code} n'a aucune formation sanitaire"
        )
        assert district_counts[d_code] >= 1, f"District {d_code} compte 0 structure"


# ==============================================================================
# Tier 4 : Performance, Requêtage & Validation Adversariale
# ==============================================================================


def test_tier4_query_performance(geography_df: pd.DataFrame) -> None:
    """Vérifie la rapidité de filtrage multi-critères (< 50ms par requête)."""
    start = time.perf_counter()
    # Requête 1 : structures par région
    savanes_facs = geography_df[geography_df["region_code"] == "TG-SAV"]
    # Requête 2 : structures par district
    lome_ds1_facs = geography_df[geography_df["district_code"] == "TG-LOM-DS1"]
    # Requête 3 : structures tertiaires et secondaires
    referral_facs = geography_df[geography_df["pyramid_level"] >= 3]
    elapsed = time.perf_counter() - start

    assert elapsed < 0.05, f"Performance de filtrage trop lente : {elapsed * 1000:.2f}ms >= 50ms"
    assert not savanes_facs.empty
    assert not lome_ds1_facs.empty
    assert not referral_facs.empty


def test_tier4_is_active_flag(geography_df: pd.DataFrame) -> None:
    """Si la colonne is_active est présente, vérifie que les formations sont actives."""
    if "is_active" in geography_df.columns:
        inactive_count = (geography_df["is_active"] == False).sum()  # noqa: E712
        assert inactive_count == 0, (
            f"{inactive_count} formations sanitaires sont inactives dans le référentiel officiel"
        )


def test_tier4_adversarial_validator(geography_module) -> None:
    """Test adversarial : vérifie que le validateur du module geography rejette des données invalides."""
    if not hasattr(geography_module, "validate_health_geography"):
        pytest.skip("Fonction validate_health_geography non présente dans le module")

    # 1. Donnée corrompue : doublon de nom normalisé dans le même district
    corrupt_df = pd.DataFrame(
        [
            {
                "facility_id": "c1a11111-1111-5111-8111-111111111111",
                "facility_code": "TG-FAC-001",
                "name": "Dispensaire A",
                "normalized_name": "dispensaire a",
                "category": "USP",
                "pyramid_level": 1,
                "district_code": "TG-LOM-DS1",
                "district_name": "District 1",
                "region_code": "TG-LOM",
                "region_name": "Grand Lomé",
                "country_code": "TG",
                "country_name": "Togo",
            },
            {
                "facility_id": "c2a22222-2222-5222-8222-222222222222",
                "facility_code": "TG-FAC-002",
                "name": "Dispensaire A Bis",
                "normalized_name": "dispensaire a",  # Doublon volontaire dans le même district
                "category": "USP",
                "pyramid_level": 1,
                "district_code": "TG-LOM-DS1",
                "district_name": "District 1",
                "region_code": "TG-LOM",
                "region_name": "Grand Lomé",
                "country_code": "TG",
                "country_name": "Togo",
            },
        ]
    )

    errors = geography_module.validate_health_geography(corrupt_df)
    assert len(errors) > 0, (
        "Le validateur aurait dû rejeter les doublons de (district_code, normalized_name)"
    )
