"""Exportateurs multi-formats pour les données de santé dégradées.

Génère les jeux de données d'entraînement et de stress-test dans les formats
usuels des systèmes de santé togolais et internationaux :
- Classeur Excel (.xlsx) multi-onglets
- Fichiers CSV propriétaires avec délimiteur point-virgule (;)
- Bundles JSON / FHIR R4 dégradés
- Agrégats statistiques sanitaires DHIS2
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from src.degradation.schemas import AlterationRecord


def export_degraded_excel(tables: dict[str, pd.DataFrame], output_path: Path | str) -> Path:
    """Exporte un dictionnaire de tables dans un classeur Excel multi-feuilles openpyxl."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
        for table_name, df in tables.items():
            # Tronquer le nom de la feuille à 31 caractères max (limitation Excel)
            sheet_title = table_name[:31]
            df.to_excel(writer, sheet_name=sheet_title, index=False)

    return out_file


def export_degraded_csv(
    tables: dict[str, pd.DataFrame],
    output_dir: Path | str,
    sep: str = ";",
    encoding: str = "utf-8",
) -> list[Path]:
    """Exporte chaque table sous format CSV avec séparateur point-virgule et encodage spécifié."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []

    for table_name, df in tables.items():
        csv_file = out_dir / f"{table_name}.csv"
        df.to_csv(csv_file, sep=sep, index=False, encoding=encoding)
        created_files.append(csv_file)

    return created_files


def export_degraded_fhir(
    tables: dict[str, pd.DataFrame],
    output_dir: Path | str,
    alterations_log: list[AlterationRecord] | None = None,
) -> list[Path]:
    """Produit une représentation FHIR Bundle JSON contenant les ressources dégradées."""
    _ = alterations_log
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle_file = out_dir / "fhir_bundle_degraded.json"

    entries: list[dict[str, Any]] = []

    # Conversion simplifiée des patients en ressources Patient FHIR
    patients_df = tables.get("patients")
    if patients_df is not None:
        for _, row in patients_df.iterrows():
            patient_res: dict[str, Any] = {
                "resourceType": "Patient",
                "id": str(row.get("patient_id", "")),
                "name": [
                    {
                        "family": str(row.get("family_name", "")),
                        "given": [str(row.get("given_name", ""))],
                    }
                ],
                "gender": str(row.get("gender", "unknown")),
                "birthDate": str(row.get("birth_date", "")),
            }
            entries.append(
                {
                    "fullUrl": f"urn:uuid:{patient_res['id']}",
                    "resource": patient_res,
                }
            )

    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "id": "degraded-dataset-bundle",
        "total": len(entries),
        "entry": entries,
    }

    with open(bundle_file, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    return [bundle_file]


def export_degraded_dhis2(
    dhis2_data: Any,
    output_dir: Path | str,
) -> list[Path]:
    """Exporte les agrégats statistiques DHIS2 altérés en formats JSON et Parquet."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    if isinstance(dhis2_data, pd.DataFrame):
        parquet_file = out_dir / "dhis2_data_values.parquet"
        dhis2_data.to_parquet(parquet_file, index=False)
        created.append(parquet_file)

        json_file = out_dir / "dhis2_data_values.json"
        records = dhis2_data.to_dict(orient="records")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"dataValues": records}, f, ensure_ascii=False, indent=2)
        created.append(json_file)
    elif isinstance(dhis2_data, (dict, list)):
        json_file = out_dir / "dhis2_data_values.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(dhis2_data, f, ensure_ascii=False, indent=2)
        created.append(json_file)

    return created
