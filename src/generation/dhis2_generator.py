"""Générateur et extracteur d'agrégats statistiques DHIS2 pour le Togo (Étape 3).

Ce module produit des séries temporelles agrégées mensuelles par district selon le standard
officiel DHIS2 dataValueSets (10 indicateurs clés, 44 districts, 12 périodes mensuelles).
Intègre un mécanisme de repli hors-ligne (offline fallback) résilient (ADR D-04, SYNTHESE_PROJET §5.2.5).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq

from src.generation.schemas import DHIS2_DATA_VALUE_SCHEMA, create_pyarrow_table
from src.terminology.geography import load_health_geography

# 10 Indicateurs épidémiologiques et programmatiques nationaux du Togo
DHIS2_INDICATORS: list[dict[str, str]] = [
    {
        "id": "DE_MALARIA_CONF_U5",
        "name": "Paludisme confirmé chez les moins de 5 ans",
        "base_rate": "150",
    },
    {
        "id": "DE_MALARIA_CONF_GEN",
        "name": "Paludisme confirmé chez les 5 ans et plus",
        "base_rate": "220",
    },
    {
        "id": "DE_MALARIA_SEVERE_ADM",
        "name": "Paludisme grave hospitalisé",
        "base_rate": "25",
    },
    {
        "id": "DE_ANC1_VISITS",
        "name": "Première consultation prénatale (CPN 1)",
        "base_rate": "90",
    },
    {
        "id": "DE_ANC4_VISITS",
        "name": "Quatrième consultation prénatale (CPN 4)",
        "base_rate": "65",
    },
    {
        "id": "DE_ASSISTED_DELIVERIES",
        "name": "Accouchements assistés en établissement",
        "base_rate": "60",
    },
    {
        "id": "DE_BCG_DOSES",
        "name": "Doses de vaccin BCG administrées",
        "base_rate": "80",
    },
    {
        "id": "DE_PENTA3_DOSES",
        "name": "Doses de vaccin Pentavalent 3 administrées",
        "base_rate": "75",
    },
    {
        "id": "DE_RR1_DOSES",
        "name": "Doses de vaccin Rougeole-Rubéole 1 administrées",
        "base_rate": "70",
    },
    {
        "id": "DE_DIARRHEA_U5_ORS_ZINC",
        "name": "Cas de diarrhée < 5 ans traités par SRO et Zinc",
        "base_rate": "45",
    },
]


def generate_synthetic_dhis2_dataset(
    seed: int = 42,
    year: int = 2025,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Génère de manière autonome et déterministe le jeu d'agrégats DHIS2.

    Couvre les 44 districts sanitaires sur 12 mois pour 10 indicateurs (5 280 valeurs).
    """
    rng = random.Random(seed)
    geo_df = load_health_geography()
    districts = (
        geo_df[["district_code", "district_name", "region_code", "region_name"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    periods = [f"{year}{m:02d}" for m in range(1, 13)]

    # Poids démographiques par région
    region_weights = {
        "TG-LOM": 2.8,
        "TG-MAR": 1.6,
        "TG-PLA": 1.5,
        "TG-SAV": 1.2,
        "TG-KAR": 1.1,
        "TG-CEN": 1.0,
    }

    # Saisonnalité palustre (pic en mai-juillet dans le sud, juillet-septembre dans le nord)
    seasonality_south = [0.8, 0.8, 0.9, 1.2, 1.5, 1.6, 1.4, 1.1, 1.0, 0.9, 0.8, 0.8]
    seasonality_north = [0.6, 0.6, 0.7, 0.8, 1.1, 1.3, 1.6, 1.7, 1.5, 1.1, 0.8, 0.6]

    json_data_values: list[dict[str, Any]] = []
    parquet_records: list[dict[str, Any]] = []

    for d in districts:
        d_code = d["district_code"]
        d_name = d["district_name"]
        r_code = d["region_code"]
        pop_weight = region_weights.get(r_code, 1.0)
        is_north = r_code in ("TG-KAR", "TG-SAV", "TG-CEN")
        seasonality = seasonality_north if is_north else seasonality_south

        for m_idx, period in enumerate(periods):
            s_factor = seasonality[m_idx]

            for indicator in DHIS2_INDICATORS:
                ind_id = indicator["id"]
                ind_name = indicator["name"]
                base_val = int(indicator["base_rate"])

                if "MALARIA" in ind_id:
                    val = int(round(base_val * pop_weight * s_factor * rng.uniform(0.85, 1.15)))
                else:
                    val = int(round(base_val * pop_weight * rng.uniform(0.85, 1.15)))

                val = max(1, val)

                # Entrée JSON conforme DHIS2 dataValueSets
                json_item = {
                    "dataElement": ind_id,
                    "period": period,
                    "orgUnit": d_code,
                    "categoryOptionCombo": "COC_DEFAULT",
                    "attributeOptionCombo": "AOC_DEFAULT",
                    "value": str(val),
                    "storedBy": "fhir-pipeline-bot",
                    "created": f"{year}-{period[4:]}-28T10:00:00.000",
                    "lastUpdated": f"{year}-{period[4:]}-28T10:00:00.000",
                    "comment": None,
                    "followup": False,
                }
                json_data_values.append(json_item)

                # Entrée Parquet tabulaire
                parquet_record = {
                    "data_element_id": ind_id,
                    "data_element_name": ind_name,
                    "period": period,
                    "org_unit_id": d_code,
                    "district_code": d_code,
                    "org_unit_name": d_name,
                    "district_name": d_name,
                    "region_code": r_code,
                    "category_option_combo": "COC_DEFAULT",
                    "attribute_option_combo": "AOC_DEFAULT",
                    "value": val,
                    "stored_by": "fhir-pipeline-bot",
                    "created": f"{year}-{period[4:]}-28T10:00:00.000",
                    "last_updated": f"{year}-{period[4:]}-28T10:00:00.000",
                }
                parquet_records.append(parquet_record)

    # Tri déterministe
    parquet_records.sort(
        key=lambda x: (
            str(x["district_code"]),
            str(x["period"]),
            str(x["data_element_id"]),
        )
    )

    json_container = {"dataValues": json_data_values}
    return json_container, parquet_records


def extract_or_generate_dhis2_aggregates(
    api_url: str = "https://play.dhis2.org/demo",
    output_dir: Path | str = Path("data/truth/dhis2"),
    offline: bool = False,
    seed: int = 42,
) -> dict[str, Path]:
    """Extrait ou génère les agrégats statistiques DHIS2 pour les 44 districts du Togo.

    Tente d'interroger l'API distante avec un court timeout si offline=False,
    et bascule sans crash vers le générateur local autonome en cas d'indisponibilité réseau.

    Args:
        api_url: URL racine de l'instance DHIS2 (ex: https://play.dhis2.org/demo).
        output_dir: Répertoire de destination pour les fichiers JSON et Parquet.
        offline: Si True, force l'exécution hors-ligne sans aucune requête HTTP.
        seed: Graine pour la génération déterministe.

    Returns:
        Dictionnaire contenant les chemins des fichiers 'json' et 'parquet'.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    json_path = out_path / "dhis2_data_values.json"
    parquet_path = out_path / "dhis2_data_values.parquet"

    # Tentative d'accès en ligne si autorisé
    fetched_data: dict[str, Any] | None = None
    if not offline:
        try:
            # Requête avec timeout court (2.0s) pour ne pas bloquer les environnements déconnectés
            endpoint = f"{api_url.rstrip('/')}/api/dataValueSets.json"
            resp = httpx.get(endpoint, timeout=2.0)
            if resp.status_code == 200:
                body = resp.json()
                if "dataValues" in body and isinstance(body["dataValues"], list):
                    fetched_data = body
        except Exception:
            # Repli silencieux et immédiat sur le mode synthétique hors-ligne
            fetched_data = None

    if fetched_data is not None:
        # Données récupérées avec succès depuis l'API distante
        json_container = fetched_data
        parquet_records: list[dict[str, Any]] = []
        for item in json_container.get("dataValues", []):
            try:
                num_val = int(item.get("value", 0))
            except (ValueError, TypeError):
                num_val = 0

            parquet_records.append(
                {
                    "data_element_id": str(item.get("dataElement", "")),
                    "data_element_name": str(item.get("dataElement", "")),
                    "period": str(item.get("period", "")),
                    "org_unit_id": str(item.get("orgUnit", "")),
                    "district_code": str(item.get("orgUnit", "")),
                    "org_unit_name": str(item.get("orgUnit", "")),
                    "district_name": str(item.get("orgUnit", "")),
                    "region_code": "TG-LOM",
                    "category_option_combo": str(item.get("categoryOptionCombo", "default")),
                    "attribute_option_combo": str(item.get("attributeOptionCombo", "default")),
                    "value": num_val,
                    "stored_by": str(item.get("storedBy", "remote-dhis2")),
                    "created": str(item.get("created", "")),
                    "last_updated": str(item.get("lastUpdated", "")),
                }
            )
    else:
        # Générateur synthétique hors-ligne conforme
        json_container, parquet_records = generate_synthetic_dhis2_dataset(seed=seed)

    # Écriture du fichier JSON standard
    json_path.write_text(json.dumps(json_container, indent=2, ensure_ascii=False), encoding="utf-8")

    # Écriture de la table Parquet typée strictement
    parquet_table = create_pyarrow_table(parquet_records, DHIS2_DATA_VALUE_SCHEMA)
    pq.write_table(parquet_table, parquet_path, compression="SNAPPY")

    return {
        "json": json_path,
        "parquet": parquet_path,
    }
