"""Lecteurs spécialisés multi-formats résilients pour la couche d'ingestion.

Prend en charge :
- Classeurs Excel multi-onglets (.xlsx, .xls)
- CSV avec détection automatique du délimiteur (, ; \\t |) et de l'encodage (UTF-8, Latin-1, CP1252)
- Bundles FHIR R4 JSON transformés en structures tabulaires
- Exports DHIS2 dataValueSets (JSON et Parquet)
- Renifleur de format source (detect_source_type)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.ingestion.schemas import SourceFormat

# Délimiteurs candidats usuels
CANDIDATE_DELIMITERS = [",", ";", "\t", "|"]

# Encodages candidats testés séquentiellement
CANDIDATE_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]


def detect_csv_encoding(path: Path | str) -> str:
    """Détecte l'encodage d'un fichier CSV sans mojibake."""
    path = Path(path)
    raw_bytes = path.read_bytes()

    for enc in CANDIDATE_ENCODINGS:
        try:
            raw_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


def detect_csv_delimiter(path: Path | str, encoding: str = "utf-8") -> str:
    """Détecte automatiquement le séparateur CSV le plus probable."""
    path = Path(path)
    try:
        sample_text = path.read_text(encoding=encoding, errors="replace")
    except Exception:
        sample_text = path.read_text(encoding="latin-1", errors="replace")

    lines = [line for line in sample_text.splitlines() if line.strip()][:15]
    if not lines:
        return ","

    best_delim = ","
    best_score = -1

    for delim in CANDIDATE_DELIMITERS:
        counts = [line.count(delim) for line in lines]
        # Tous les comptes doivent être réguliers et non nuls
        first_count = counts[0]
        if first_count > 0 and all(c == first_count for c in counts):
            score = first_count * 100
        else:
            score = sum(counts)

        if score > best_score:
            best_score = score
            best_delim = delim

    return best_delim


def read_excel_source(path: Path | str, sheets: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Lit un classeur Excel (.xlsx, .xls) et renvoie un dictionnaire {nom_feuille: DataFrame}."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Classeur Excel introuvable : {path}")

    # pandas read_excel avec sheet_name=None charge toutes les feuilles
    workbook_dict: dict[str, pd.DataFrame] = pd.read_excel(path, sheet_name=None, engine=None)

    if sheets is not None:
        workbook_dict = {sheet: df for sheet, df in workbook_dict.items() if sheet in sheets}

    return workbook_dict


def read_csv_source(
    path: Path | str, sep: str | None = None, encoding: str | None = None
) -> pd.DataFrame:
    """Lit un fichier CSV avec autodétection robuste de l'encodage et du délimiteur."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier CSV introuvable : {path}")

    detected_encoding = encoding or detect_csv_encoding(path)
    detected_sep = sep or detect_csv_delimiter(path, encoding=detected_encoding)

    try:
        return pd.read_csv(
            path,
            sep=detected_sep,
            encoding=detected_encoding,
            engine="python",
        )
    except Exception:
        # Fallback de résilience en latin-1
        return pd.read_csv(
            path,
            sep=detected_sep,
            encoding="latin-1",
            engine="python",
        )


def read_fhir_source(path: Path | str) -> dict[str, pd.DataFrame]:
    """Parse un Bundle FHIR R4 JSON et renvoie un dictionnaire de DataFrames par type de ressource."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier FHIR introuvable : {path}")

    content = path.read_text(encoding="utf-8-sig")
    data: dict[str, Any] = json.loads(content)

    resources_by_type: dict[str, list[dict[str, Any]]] = {}

    if isinstance(data, dict) and data.get("resourceType") == "Bundle":
        for entry in data.get("entry", []):
            resource = entry.get("resource", entry)
            res_type = resource.get("resourceType", "Unknown")
            resources_by_type.setdefault(res_type, []).append(resource)
    elif isinstance(data, dict) and "resourceType" in data:
        res_type = data.get("resourceType", "Resource")
        resources_by_type.setdefault(res_type, []).append(data)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                res_type = item.get("resourceType", "Resource")
                resources_by_type.setdefault(res_type, []).append(item)

    tables: dict[str, pd.DataFrame] = {}
    for res_type, items in resources_by_type.items():
        df = pd.DataFrame(items)
        tables[res_type] = df
        # Alias en minuscules et au pluriel usuel
        lower_key = res_type.lower()
        tables[lower_key] = df
        if not lower_key.endswith("s"):
            tables[f"{lower_key}s"] = df

    return tables


def read_dhis2_source(path: Path | str) -> pd.DataFrame:
    """Lit un export DHIS2 dataValueSets JSON ou Parquet et renvoie un DataFrame normé."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Export DHIS2 introuvable : {path}")

    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)

    content = path.read_text(encoding="utf-8-sig")
    data = json.loads(content)

    data_values: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if "dataValues" in data:
            data_values = data["dataValues"]
        elif "data" in data and isinstance(data["data"], list):
            data_values = data["data"]
        else:
            data_values = [data]
    elif isinstance(data, list):
        data_values = data

    return pd.DataFrame(data_values)


def detect_source_type(path: Path | str) -> SourceFormat:
    """Détecte automatiquement le format d'un fichier source."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in [".xlsx", ".xls"]:
        return SourceFormat.EXCEL

    if suffix in [".csv", ".tsv"]:
        return SourceFormat.CSV

    if suffix == ".json":
        if not path.exists():
            return SourceFormat.UNKNOWN
        try:
            sample_header = path.read_bytes()[:4096].decode("utf-8", errors="ignore")
            if '"resourceType"' in sample_header or '"Bundle"' in sample_header:
                return SourceFormat.FHIR
            if '"dataValues"' in sample_header or '"dataElement"' in sample_header:
                return SourceFormat.DHIS2

            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                if data.get("resourceType") or "entry" in data:
                    return SourceFormat.FHIR
                if "dataValues" in data:
                    return SourceFormat.DHIS2
        except Exception:
            return SourceFormat.UNKNOWN

    if suffix == ".parquet":
        if "dhis2" in path.stem.lower():
            return SourceFormat.DHIS2
        return SourceFormat.UNKNOWN

    return SourceFormat.UNKNOWN
