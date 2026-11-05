"""Référentiel géographique et sanitaire officiel du Togo (Étape 2).

Ce module modélise le découpage territorial de la santé au Togo conformément à
l'ADR D-08 et VAL-001 :
- 6 Régions sanitaires officielles (Savanes, Kara, Centrale, Plateaux, Maritime, Grand Lomé).
- 44 Districts sanitaires officiels sans aucun district orphelin.
- Pyramide des soins à 4 niveaux opérationnels (CHU niveau 4, CHR niveau 3,
  Hôpitaux de District / CHP niveau 2, CMS et USP niveau 1).
- Identifiants immuables déterministes par UUID v5 RFC 4122.
- Normalisation rigoureuse des libellés (minuscules, sans accents/diacritiques NFKD,
  espaces compactés).
- Unicité stricte des libellés normalisés au sein d'un même district.
- Fonctions publiques de chargement, validation et génération du référentiel Parquet.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Chemin par défaut du référentiel Parquet gelé
DEFAULT_GEOGRAPHY_PARQUET_PATH = Path("data/reference/togo_health_geography.parquet")

# Espace de noms UUID v5 déterministe pour les formations sanitaires du Togo
NAMESPACE_TOGO_FACILITY = uuid.uuid5(uuid.NAMESPACE_DNS, "facility.sante.gouv.tg")

# Expression régulière RFC 4122 pour la validation stricte d'UUID v5
UUID_V5_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Colonnes obligatoires du schéma Parquet
REQUIRED_COLUMNS: tuple[str, ...] = (
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
)

# Colonnes essentielles ne devant contenir aucune valeur nulle ni vide
ESSENTIAL_COLUMNS: tuple[str, ...] = (
    "facility_id",
    "facility_code",
    "name",
    "normalized_name",
    "category",
    "pyramid_level",
    "district_code",
    "region_code",
    "country_code",
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

ALL_44_DISTRICT_CODES: frozenset[str] = frozenset(
    d for dists in EXPECTED_DISTRICTS_BY_REGION.values() for d in dists
)

# Nomenclature administrative complète des 44 districts sanitaires
DISTRICTS_METADATA: list[dict[str, str]] = [
    # Savanes (7)
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-CIN",
        "district_name": "Cinkassé",
        "capital": "Cinkassé",
    },
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-KPE",
        "district_name": "Kpendjal",
        "capital": "Mandouri",
    },
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-KPO",
        "district_name": "Kpendjal-Ouest",
        "capital": "Naki-Est",
    },
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-OTI",
        "district_name": "Oti",
        "capital": "Mango",
    },
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-OTS",
        "district_name": "Oti-Sud",
        "capital": "Gando",
    },
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-TAN",
        "district_name": "Tandjouaré",
        "capital": "Tandjouaré",
    },
    {
        "region_code": "TG-SAV",
        "region_name": "Savanes",
        "district_code": "TG-SAV-TON",
        "district_name": "Tône",
        "capital": "Dapaong",
    },
    # Kara (7)
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-ASS",
        "district_name": "Assoli",
        "capital": "Bafilo",
    },
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-BAS",
        "district_name": "Bassar",
        "capital": "Bassar",
    },
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-BIN",
        "district_name": "Binah",
        "capital": "Pagouda",
    },
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-DAN",
        "district_name": "Dankpen",
        "capital": "Guérin-Kouka",
    },
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-DOU",
        "district_name": "Doufelgou",
        "capital": "Niamtougou",
    },
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-KER",
        "district_name": "Kéran",
        "capital": "Kantè",
    },
    {
        "region_code": "TG-KAR",
        "region_name": "Kara",
        "district_code": "TG-KAR-KOZ",
        "district_name": "Kozah",
        "capital": "Kara",
    },
    # Centrale (5)
    {
        "region_code": "TG-CEN",
        "region_name": "Centrale",
        "district_code": "TG-CEN-BLI",
        "district_name": "Blitta",
        "capital": "Blitta",
    },
    {
        "region_code": "TG-CEN",
        "region_name": "Centrale",
        "district_code": "TG-CEN-MO",
        "district_name": "Mô",
        "capital": "Djarkpanga",
    },
    {
        "region_code": "TG-CEN",
        "region_name": "Centrale",
        "district_code": "TG-CEN-SOT",
        "district_name": "Sotouboua",
        "capital": "Sotouboua",
    },
    {
        "region_code": "TG-CEN",
        "region_name": "Centrale",
        "district_code": "TG-CEN-TCH",
        "district_name": "Tchamba",
        "capital": "Tchamba",
    },
    {
        "region_code": "TG-CEN",
        "region_name": "Centrale",
        "district_code": "TG-CEN-TCJ",
        "district_name": "Tchaoudjo",
        "capital": "Sokodé",
    },
    # Plateaux (12)
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-AGU",
        "district_name": "Agou",
        "capital": "Agou-Gadjépé",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-AKE",
        "district_name": "Akébou",
        "capital": "Kougnohou",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-AMO",
        "district_name": "Amou",
        "capital": "Amlamé",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-ANI",
        "district_name": "Anié",
        "capital": "Anié",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-DAN",
        "district_name": "Danyi",
        "capital": "Danyi-Apéyémé",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-EST",
        "district_name": "Est-Mono",
        "capital": "Elavagnon",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-HAH",
        "district_name": "Haho",
        "capital": "Notsé",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-KLO",
        "district_name": "Kloto",
        "capital": "Kpalimé",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-KPE",
        "district_name": "Kpélé",
        "capital": "Kpélé-Adéta",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-MOY",
        "district_name": "Moyen-Mono",
        "capital": "Tohoun",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-OGU",
        "district_name": "Ogou",
        "capital": "Atakpamé",
    },
    {
        "region_code": "TG-PLA",
        "region_name": "Plateaux",
        "district_code": "TG-PLA-WAW",
        "district_name": "Wawa",
        "capital": "Badou",
    },
    # Maritime (6)
    {
        "region_code": "TG-MAR",
        "region_name": "Maritime",
        "district_code": "TG-MAR-AVE",
        "district_name": "Avé",
        "capital": "Kévé",
    },
    {
        "region_code": "TG-MAR",
        "region_name": "Maritime",
        "district_code": "TG-MAR-BAS",
        "district_name": "Bas-Mono",
        "capital": "Afagnagan",
    },
    {
        "region_code": "TG-MAR",
        "region_name": "Maritime",
        "district_code": "TG-MAR-LAC",
        "district_name": "Lacs",
        "capital": "Aného",
    },
    {
        "region_code": "TG-MAR",
        "region_name": "Maritime",
        "district_code": "TG-MAR-VO",
        "district_name": "Vo",
        "capital": "Vogan",
    },
    {
        "region_code": "TG-MAR",
        "region_name": "Maritime",
        "district_code": "TG-MAR-YOT",
        "district_name": "Yoto",
        "capital": "Tabligbo",
    },
    {
        "region_code": "TG-MAR",
        "region_name": "Maritime",
        "district_code": "TG-MAR-ZIO",
        "district_name": "Zio",
        "capital": "Tsévié",
    },
    # Grand Lomé (7)
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-AGO",
        "district_name": "Agoè-Nyivé",
        "capital": "Agoè-Nyivé",
    },
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-GOL",
        "district_name": "Golfe",
        "capital": "Bè",
    },
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-DS1",
        "district_name": "District Sanitaire N°1",
        "capital": "Lomé Centre",
    },
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-DS2",
        "district_name": "District Sanitaire N°2",
        "capital": "Lomé Est",
    },
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-DS3",
        "district_name": "District Sanitaire N°3",
        "capital": "Lomé Ouest",
    },
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-DS4",
        "district_name": "District Sanitaire N°4",
        "capital": "Lomé Sud",
    },
    {
        "region_code": "TG-LOM",
        "region_name": "Grand Lomé",
        "district_code": "TG-LOM-DS5",
        "district_name": "District Sanitaire N°5",
        "capital": "Lomé Nord",
    },
]


def normalize_facility_name(name: str) -> str:
    """Normalise un libellé de formation sanitaire.

    Règles appliquées :
    - Décomposition Unicode NFKD.
    - Élimination des accents et diacritiques combinatoires.
    - Remplacement des caractères de ponctuation et spéciaux par des espaces.
    - Conversion stricte en minuscules.
    - Compactage des espaces consécutifs et retrait des espaces en début/fin.

    Args:
        name: Libellé brut de l'établissement (ex: "CHU Sylvanus Olympio").

    Returns:
        Libellé normalisé sans accent en minuscules (ex: "chu sylvanus olympio").
    """
    if not isinstance(name, str):
        return ""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in ascii_str)
    return " ".join(cleaned.lower().split())


def generate_facility_uuid(facility_code: str) -> str:
    """Génère un identifiant déterministe UUID v5 conforme RFC 4122.

    Args:
        facility_code: Code unique officiel de la formation sanitaire.

    Returns:
        Chaîne UUID v5 immuable.
    """
    return str(uuid.uuid5(NAMESPACE_TOGO_FACILITY, f"facility:{facility_code}"))


def build_togo_health_geography_dataframe() -> pd.DataFrame:
    """Construit le DataFrame complet du référentiel territorial et sanitaire togolais.

    Modélise :
    - 6 régions et 44 districts sanitaires.
    - 3 CHU (niveau 4 : Sylvanus Olympio, Campus, Kara).
    - 6 CHR (niveau 3 : Dapaong, Kara-Tomdè, Sokodé, Atakpamé, Tsévié, Lomé-Commune).
    - 44 CHP / Hôpitaux de District (niveau 2 : 1 par district).
    - Plus de 130 formations de proximité (niveau 1 : CMS et USP).

    Returns:
        DataFrame pandas prêt pour export Parquet avec invariants d'intégrité garantis.
    """
    facilities: list[dict[str, Any]] = []

    # 1. Niveau 4 : Centres Hospitaliers Universitaires (CHU)
    chu_records = [
        {
            "facility_code": "TG-FAC-CHU-01",
            "name": "CHU Sylvanus Olympio",
            "category": "CHU",
            "pyramid_level": 4,
            "district_code": "TG-LOM-DS1",
            "district_name": "District Sanitaire N°1",
            "region_code": "TG-LOM",
            "region_name": "Grand Lomé",
        },
        {
            "facility_code": "TG-FAC-CHU-02",
            "name": "CHU Campus",
            "category": "CHU",
            "pyramid_level": 4,
            "district_code": "TG-LOM-DS3",
            "district_name": "District Sanitaire N°3",
            "region_code": "TG-LOM",
            "region_name": "Grand Lomé",
        },
        {
            "facility_code": "TG-FAC-CHU-03",
            "name": "CHU Kara",
            "category": "CHU",
            "pyramid_level": 4,
            "district_code": "TG-KAR-KOZ",
            "district_name": "Kozah",
            "region_code": "TG-KAR",
            "region_name": "Kara",
        },
    ]
    facilities.extend(chu_records)

    # 2. Niveau 3 : Centres Hospitaliers Régionaux (CHR)
    chr_records = [
        {
            "facility_code": "TG-FAC-CHR-01",
            "name": "CHR Dapaong",
            "category": "CHR",
            "pyramid_level": 3,
            "district_code": "TG-SAV-TON",
            "district_name": "Tône",
            "region_code": "TG-SAV",
            "region_name": "Savanes",
        },
        {
            "facility_code": "TG-FAC-CHR-02",
            "name": "CHR Kara-Tomdè",
            "category": "CHR",
            "pyramid_level": 3,
            "district_code": "TG-KAR-KOZ",
            "district_name": "Kozah",
            "region_code": "TG-KAR",
            "region_name": "Kara",
        },
        {
            "facility_code": "TG-FAC-CHR-03",
            "name": "CHR Sokodé",
            "category": "CHR",
            "pyramid_level": 3,
            "district_code": "TG-CEN-TCJ",
            "district_name": "Tchaoudjo",
            "region_code": "TG-CEN",
            "region_name": "Centrale",
        },
        {
            "facility_code": "TG-FAC-CHR-04",
            "name": "CHR Atakpamé",
            "category": "CHR",
            "pyramid_level": 3,
            "district_code": "TG-PLA-OGU",
            "district_name": "Ogou",
            "region_code": "TG-PLA",
            "region_name": "Plateaux",
        },
        {
            "facility_code": "TG-FAC-CHR-05",
            "name": "CHR Tsévié",
            "category": "CHR",
            "pyramid_level": 3,
            "district_code": "TG-MAR-ZIO",
            "district_name": "Zio",
            "region_code": "TG-MAR",
            "region_name": "Maritime",
        },
        {
            "facility_code": "TG-FAC-CHR-06",
            "name": "CHR Lomé-Commune",
            "category": "CHR",
            "pyramid_level": 3,
            "district_code": "TG-LOM-DS5",
            "district_name": "District Sanitaire N°5",
            "region_code": "TG-LOM",
            "region_name": "Grand Lomé",
        },
    ]
    facilities.extend(chr_records)

    # 3. Formations des 44 districts : Niveau 2 (CHP / Hospital) et Niveau 1 (CMS & USP)
    facility_counter = 100
    for meta in DISTRICTS_METADATA:
        d_code = meta["district_code"]
        d_name = meta["district_name"]
        r_code = meta["region_code"]
        r_name = meta["region_name"]
        cap = meta["capital"]

        # Niveau 2 : Hôpital de District / CHP de référence
        facility_counter += 1
        chp_code = f"TG-FAC-CHP-{facility_counter:04d}"
        if r_code == "TG-LOM":
            chp_name = f"Hôpital de District de {cap}"
        else:
            chp_name = f"Centre Hospitalier Préfectoral de {cap}"

        facilities.append(
            {
                "facility_code": chp_code,
                "name": chp_name,
                "category": "Hospital",
                "pyramid_level": 2,
                "district_code": d_code,
                "district_name": d_name,
                "region_code": r_code,
                "region_name": r_name,
            }
        )

        # Niveau 1 : CMS (Centre Médico-Social)
        facility_counter += 1
        cms_code = f"TG-FAC-CMS-{facility_counter:04d}"
        # Dénominations réalistes pour Grand Lomé, adaptées pour les autres districts
        if d_code == "TG-LOM-DS1":
            cms_name = "CMS Amoutivé"
        elif d_code == "TG-LOM-DS2":
            cms_name = "CMS Bè-Kpota"
        elif d_code == "TG-LOM-DS3":
            cms_name = "CMS Adidogomé"
        elif d_code == "TG-LOM-DS4":
            cms_name = "CMS Kodjoviakopé"
        elif d_code == "TG-LOM-DS5":
            cms_name = "CMS Kégué"
        elif d_code == "TG-LOM-AGO":
            cms_name = "CMS Cacaveli"
        elif d_code == "TG-LOM-GOL":
            cms_name = "CMS Bè"
        else:
            cms_name = f"CMS {cap} Centre"

        facilities.append(
            {
                "facility_code": cms_code,
                "name": cms_name,
                "category": "CMS",
                "pyramid_level": 1,
                "district_code": d_code,
                "district_name": d_name,
                "region_code": r_code,
                "region_name": r_name,
            }
        )

        # Niveau 1 : USP 1 (Unité de Soins Périphériques)
        facility_counter += 1
        usp1_code = f"TG-FAC-USP-{facility_counter:04d}"
        if d_code == "TG-LOM-DS1":
            usp1_name = "USP Nyékonakpoè"
        elif d_code == "TG-LOM-DS2":
            usp1_name = "USP Akodésséwa"
        elif d_code == "TG-LOM-DS3":
            usp1_name = "USP Amadahomé"
        elif d_code == "TG-LOM-DS4":
            usp1_name = "USP Hanoukopé"
        elif d_code == "TG-LOM-DS5":
            usp1_name = "USP Hédzranawoé"
        elif d_code == "TG-LOM-AGO":
            usp1_name = "USP Vakpossito"
        elif d_code == "TG-LOM-GOL":
            usp1_name = "USP Adakpamé"
        else:
            usp1_name = f"USP {cap} Nord"

        facilities.append(
            {
                "facility_code": usp1_code,
                "name": usp1_name,
                "category": "USP",
                "pyramid_level": 1,
                "district_code": d_code,
                "district_name": d_name,
                "region_code": r_code,
                "region_name": r_name,
            }
        )

        # Niveau 1 : USP 2
        facility_counter += 1
        usp2_code = f"TG-FAC-USP-{facility_counter:04d}"
        if d_code == "TG-LOM-DS1":
            usp2_name = "USP Tokoin Centre"
        elif d_code == "TG-LOM-DS2":
            usp2_name = "USP Baguida"
        elif d_code == "TG-LOM-DS3":
            usp2_name = "USP Aflao Gakli"
        elif d_code == "TG-LOM-DS4":
            usp2_name = "USP Assivito"
        elif d_code == "TG-LOM-DS5":
            usp2_name = "USP Totsi"
        elif d_code == "TG-LOM-AGO":
            usp2_name = "USP Agoè-Nyivé Centre"
        elif d_code == "TG-LOM-GOL":
            usp2_name = "USP Adamavo"
        else:
            usp2_name = f"USP {cap} Sud"

        facilities.append(
            {
                "facility_code": usp2_code,
                "name": usp2_name,
                "category": "USP",
                "pyramid_level": 1,
                "district_code": d_code,
                "district_name": d_name,
                "region_code": r_code,
                "region_name": r_name,
            }
        )

    # 4. Assemblage des enregistrements avec identifiants v5 déterministes et noms normalisés
    rows: list[dict[str, Any]] = []
    for f in facilities:
        fac_code = f["facility_code"]
        fac_id = generate_facility_uuid(fac_code)
        norm_name = normalize_facility_name(f["name"])

        rows.append(
            {
                "facility_id": fac_id,
                "facility_code": fac_code,
                "name": f["name"],
                "normalized_name": norm_name,
                "category": f["category"],
                "pyramid_level": int(f["pyramid_level"]),
                "district_code": f["district_code"],
                "district_name": f["district_name"],
                "region_code": f["region_code"],
                "region_name": f["region_name"],
                "country_code": "TG",
                "country_name": "Togo",
                "parent_id": f["district_code"],
                "is_active": True,
            }
        )

    df = pd.DataFrame(rows)
    return df


def validate_health_geography(
    df_or_table: pd.DataFrame | pa.Table | Any,
) -> list[str]:
    """Valide l'intégrité stricte d'un jeu de données géographique et sanitaire togolais.

    Vérifie :
    1. Présence de toutes les colonnes requises.
    2. Absence absolue de valeurs nulles ou vides dans les colonnes essentielles.
    3. Conformité stricte des identifiants au format UUID v5 (RFC 4122).
    4. Unicité globale des codes d'établissements.
    5. Absence absolue de doublons sur (district_code, normalized_name).
    6. Respect des règles de normalisation (minuscules, sans accents, sans espaces superflus).
    7. Cohérence stricte de la pyramide (CHU=4, CHR=3, Hospital/CHP=2, CMS/USP=1).
    8. Validité du lien hiérarchique district -> région (aucun district orphelin ou mal rattaché).
    9. Pays uniformément fixé à TG / Togo.
    10. Intégrité de la couverture (si au moins 44 enregistrements, vérifie la présence des
        6 régions et des 44 districts).

    Args:
        df_or_table: DataFrame pandas ou Table pyarrow à valider.

    Returns:
        Liste des messages d'erreur détectés (vide si le jeu est 100 % valide).
    """
    errors: list[str] = []

    if isinstance(df_or_table, pa.Table):
        df = df_or_table.to_pandas()
    elif isinstance(df_or_table, pd.DataFrame):
        df = df_or_table
    else:
        return [f"Format d'entrée invalide : attendu DataFrame ou Table, reçu {type(df_or_table)}"]

    if df.empty:
        return ["Le jeu de données géographique est vide."]

    # 1. Vérification des colonnes obligatoires
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        errors.append(f"Colonnes obligatoires manquantes : {sorted(missing_cols)}")

    # 2. Vérification de la non-nullité des colonnes essentielles
    for col in ESSENTIAL_COLUMNS:
        if col in df.columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                errors.append(f"Colonne '{col}' : {null_count} valeur(s) nulle(s) détectée(s).")
            empty_count = int((df[col].astype(str).str.strip() == "").sum())
            if empty_count > 0:
                errors.append(f"Colonne '{col}' : {empty_count} chaîne(s) vide(s) détectée(s).")

    # 3. Validation du format UUID v5
    if "facility_id" in df.columns:
        invalid_uuids = [
            fid
            for fid in df["facility_id"].dropna()
            if not isinstance(fid, str) or not UUID_V5_REGEX.match(fid)
        ]
        if invalid_uuids:
            sample = invalid_uuids[:3]
            errors.append(
                f"{len(invalid_uuids)} identifiant(s) ne respectent pas le format UUID v5 RFC 4122 (ex: {sample})."
            )

    # 4. Unicité globale des facility_code
    if "facility_code" in df.columns:
        dup_codes = df[df["facility_code"].duplicated()]["facility_code"].tolist()
        if dup_codes:
            errors.append(
                f"Codes d'établissements en doublon détectés ({len(dup_codes)}) : {dup_codes[:5]}"
            )

    # 5. Unicité stricte de (district_code, normalized_name)
    if "district_code" in df.columns and "normalized_name" in df.columns:
        duplicates = df[df.duplicated(subset=["district_code", "normalized_name"], keep=False)]
        if not duplicates.empty:
            sample_dups = (
                duplicates[["district_code", "normalized_name"]].drop_duplicates().values.tolist()
            )
            errors.append(
                f"Doublons de nom normalisé au sein d'un même district ({len(sample_dups)}) : {sample_dups[:5]}"
            )

    # 6. Règles de normalisation
    if "normalized_name" in df.columns:
        invalid_norm = []
        for name in df["normalized_name"].dropna().astype(str):
            if name != name.lower():
                invalid_norm.append(f"Non-minuscule : '{name}'")
                break
            decomposed = unicodedata.normalize("NFD", name)
            if any(unicodedata.combining(c) for c in decomposed):
                invalid_norm.append(f"Diacritiques résiduels : '{name}'")
                break
            if name.startswith(" ") or name.endswith(" ") or "  " in name:
                invalid_norm.append(f"Espaces superflus : '{name}'")
                break
        if invalid_norm:
            errors.extend(invalid_norm)

    # 7. Cohérence catégorie et niveau de pyramide
    if "category" in df.columns and "pyramid_level" in df.columns:
        for idx, row in df.iterrows():
            cat = str(row["category"]).upper().strip()
            try:
                lvl = int(row["pyramid_level"])
            except (ValueError, TypeError):
                errors.append(f"Ligne {idx} : pyramid_level non entier : {row['pyramid_level']}")
                continue

            if cat == "CHU" and lvl != 4:
                errors.append(
                    f"Incohérence niveau : CHU '{row.get('name')}' a le niveau {lvl} au lieu de 4."
                )
            elif cat == "CHR" and lvl != 3:
                errors.append(
                    f"Incohérence niveau : CHR '{row.get('name')}' a le niveau {lvl} au lieu de 3."
                )
            elif cat in ("HOSPITAL", "CHP") and lvl != 2:
                errors.append(
                    f"Incohérence niveau : Hôpital '{row.get('name')}' a le niveau {lvl} au lieu de 2."
                )
            elif cat in ("CMS", "USP") and lvl != 1:
                errors.append(
                    f"Incohérence niveau : {cat} '{row.get('name')}' a le niveau {lvl} au lieu de 1."
                )

    # 8. Hiérarchie district -> région
    if "district_code" in df.columns and "region_code" in df.columns:
        for _, row in df.iterrows():
            r_code = str(row["region_code"])
            d_code = str(row["district_code"])
            if r_code not in EXPECTED_DISTRICTS_BY_REGION:
                errors.append(f"Région sanitaire inconnue : '{r_code}' pour district '{d_code}'.")
            elif d_code not in EXPECTED_DISTRICTS_BY_REGION[r_code]:
                errors.append(
                    f"Rattachement hiérarchique illégitime : le district '{d_code}' n'appartient pas à '{r_code}'."
                )

    # 9. Pays strictement Togo
    if "country_code" in df.columns:
        invalid_countries = set(df["country_code"].unique()) - {"TG"}
        if invalid_countries:
            errors.append(f"Codes pays inattendus : {invalid_countries} (attendu uniquement 'TG').")
    if "country_name" in df.columns:
        invalid_country_names = set(df["country_name"].unique()) - {"Togo"}
        if invalid_country_names:
            errors.append(
                f"Noms pays inattendus : {invalid_country_names} (attendu uniquement 'Togo')."
            )

    # 10. Couverture complète (si jeu de référence complet avec >= 44 structures)
    if len(df) >= 44:
        if "region_code" in df.columns:
            present_regions = set(df["region_code"].unique())
            missing_regions = set(EXPECTED_REGIONS.keys()) - present_regions
            if missing_regions:
                errors.append(
                    f"Régions sanitaires manquantes dans le référentiel : {sorted(missing_regions)}"
                )
        if "district_code" in df.columns:
            present_districts = set(df["district_code"].unique())
            missing_districts = ALL_44_DISTRICT_CODES - present_districts
            if missing_districts:
                errors.append(
                    f"Districts sanitaires manquants ({len(missing_districts)}) : {sorted(missing_districts)}"
                )

    # 11. Statut d'activation si présent
    if "is_active" in df.columns:
        inactive_count = int((df["is_active"] == False).sum())  # noqa: E712
        if inactive_count > 0:
            errors.append(
                f"{inactive_count} structure(s) inactive(s) trouvée(s) dans le référentiel officiel."
            )

    return errors


def generate_health_geography(
    output_path: Path | str | None = None,
) -> Path:
    """Génère de façon déterministe le fichier Parquet du référentiel géographique sanitaire togolais.

    Args:
        output_path: Chemin du fichier Parquet cible. Si None, utilise le chemin
            officiel `data/reference/togo_health_geography.parquet`.

    Returns:
        Path vers le fichier Parquet généré et validé.

    Raises:
        ValueError: Si le DataFrame généré ne satisfait pas la validation d'intégrité.
    """
    target = Path(output_path) if output_path else DEFAULT_GEOGRAPHY_PARQUET_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    df = build_togo_health_geography_dataframe()

    # Validation d'intégrité avant écriture
    validation_errors = validate_health_geography(df)
    if validation_errors:
        err_msg = "\n - ".join(validation_errors)
        raise ValueError(
            f"Échec de validation lors de la génération du référentiel géographique :\n - {err_msg}"
        )

    # Sérialisation Parquet avec compression Snappy
    table = pa.Table.from_pandas(df)
    pq.write_table(table, target, compression="snappy")

    return target


def load_health_geography(
    parquet_path: Path | str | None = None,
) -> pd.DataFrame:
    """Charge le référentiel géographique et sanitaire officiel du Togo.

    Args:
        parquet_path: Chemin vers le fichier Parquet de référence. Si None, charge
            depuis le chemin par défaut `data/reference/togo_health_geography.parquet`.

    Returns:
        DataFrame pandas contenant les formations sanitaires togolaises.

    Raises:
        FileNotFoundError: Si le fichier Parquet n'existe pas.
    """
    path = Path(parquet_path) if parquet_path else DEFAULT_GEOGRAPHY_PARQUET_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier de référence géographique introuvable : '{path}'. "
            "Exécutez generate_health_geography() ou 'pipeline reference generate-geography'."
        )
    return pd.read_parquet(path)


def get_health_regions() -> list[dict[str, str]]:
    """Retourne la liste officielle des 6 régions sanitaires togolaises."""
    return [
        {"code": code, "name": name, "country_code": "TG"}
        for code, name in EXPECTED_REGIONS.items()
    ]


def get_health_districts(region_code: str | None = None) -> list[dict[str, str]]:
    """Retourne la liste des 44 districts sanitaires, éventuellement filtrée par région."""
    districts: list[dict[str, str]] = []
    for meta in DISTRICTS_METADATA:
        if region_code is None or meta["region_code"] == region_code:
            districts.append(
                {
                    "district_code": meta["district_code"],
                    "district_name": meta["district_name"],
                    "region_code": meta["region_code"],
                    "region_name": meta["region_name"],
                    "capital": meta["capital"],
                }
            )
    return districts
