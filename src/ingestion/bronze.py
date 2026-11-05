"""Convertisseur vers la couche Bronze Parquet et validation technique.

Garantit :
- L'injection systématique des 4 colonnes techniques d'audit obligatoires (AGENT.md #2) :
  * source_file
  * source_row (1-based)
  * ingested_at (ISO 8601 UTC)
  * content_hash (SHA-256 déterministe)
- La conservation stricte du nombre de lignes (Règle d'or : len(bronze) == len(source))
- La structuration au format Apache Parquet typé et compressé Snappy
- La validation d'intégrité schématique des tables Parquet
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.ingestion.quarantine import quarantine_file
from src.ingestion.readers import (
    detect_source_type,
    read_csv_source,
    read_dhis2_source,
    read_excel_source,
    read_fhir_source,
)
from src.ingestion.schemas import AUDIT_COLUMNS, SourceFormat


def _is_missing(val: Any) -> bool:
    """Détecte de manière sûre et robuste les valeurs manquantes (None, NaN, pd.NA)."""
    if val is None:
        return True
    if isinstance(val, (list, dict, set, tuple, np.ndarray)):
        return False
    try:
        return bool(pd.isna(val))
    except (ValueError, TypeError):
        return False


def compute_row_hash(row: dict[str, Any] | pd.Series) -> str:
    """Calcule l'empreinte SHA-256 déterministe d'une ligne de données."""
    row_dict = row.to_dict() if isinstance(row, pd.Series) else dict(row)

    # Exclure les colonnes d'audit
    filtered: dict[str, str] = {}
    for k, v in row_dict.items():
        if k in AUDIT_COLUMNS:
            continue
        if _is_missing(v):
            filtered[str(k)] = ""
        elif isinstance(v, (dict, list)):
            filtered[str(k)] = json.dumps(v, sort_keys=True, ensure_ascii=False)
        else:
            filtered[str(k)] = str(v)

    # Sérialisation canonique triée
    canonical_json = json.dumps(filtered, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def add_audit_columns(
    df: pd.DataFrame,
    source_file: str,
    ingested_at: str | None = None,
) -> pd.DataFrame:
    """Injecte les 4 colonnes d'audit obligatoires dans un DataFrame."""
    now_utc = ingested_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = df.copy()

    # Empreinte de contenu pour chaque ligne
    out["content_hash"] = [compute_row_hash(row) for _, row in out.iterrows()]

    # Métadonnées de provenance et d'audit
    out["source_file"] = source_file
    out["source_row"] = list(range(1, len(out) + 1))
    out["source_row"] = out["source_row"].astype("int64")
    out["ingested_at"] = now_utc

    return out


def _normalize_table_name(table_name: str, source_type: SourceFormat | None = None) -> str:
    """Normalise le nom de table pour le stockage Parquet Bronze."""
    name_lower = table_name.lower().strip()
    if name_lower in ["patient", "patients"]:
        return "patients"
    if name_lower in ["encounter", "encounters"]:
        return "encounters"
    if name_lower in ["observation", "observations"]:
        return "observations"
    if name_lower in ["condition", "conditions"]:
        return "conditions"
    if name_lower in ["prescription", "prescriptions"]:
        return "prescriptions"
    if name_lower in ["immunization", "immunizations"]:
        return "immunizations"
    if "dhis2" in name_lower or source_type == SourceFormat.DHIS2:
        return "dhis2_data_values"
    return name_lower


def convert_to_bronze(
    raw_file_or_dir: Path | str,
    bronze_dir: Path | str,
    batch_id: str | None = None,
    quarantine_dir: Path | str | None = None,
    ingested_at: str | None = None,
) -> dict[str, Path]:
    """Convertit les fichiers bruts vers le format Apache Parquet avec métadonnées d'audit."""
    _ = batch_id
    target = Path(raw_file_or_dir)
    out_dir = Path(bronze_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if target.is_file():
        files_to_process = [target]
        manifest_path = target.parent / "raw_manifest.json"
    elif target.is_dir():
        files_to_process = [
            p
            for p in sorted(target.iterdir())
            if p.is_file() and p.name != "raw_manifest.json" and not p.name.startswith(".")
        ]
        manifest_path = target / "raw_manifest.json"
    else:
        return {}

    # Si un manifeste d'ingestion brute existe, tenter de retrouver l'horodatage pour déterminisme
    manifest_timestamps: dict[str, str] = {}
    if manifest_path.exists():
        try:
            m_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for f in m_data.get("files", []):
                fname = Path(f.get("raw_path", "")).name
                if fname and f.get("ingested_at"):
                    manifest_timestamps[fname] = f["ingested_at"]
        except Exception:
            pass

    default_ingested_at = ingested_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    result_tables: dict[str, Path] = {}

    for src_file in files_to_process:
        file_ingested_at = manifest_timestamps.get(src_file.name, default_ingested_at)
        stype = detect_source_type(src_file)
        tables: dict[str, pd.DataFrame] = {}

        try:
            if stype == SourceFormat.EXCEL:
                tables = read_excel_source(src_file)
            elif stype == SourceFormat.CSV:
                df = read_csv_source(src_file)
                tables = {src_file.stem: df}
            elif stype == SourceFormat.FHIR:
                tables = read_fhir_source(src_file)
            elif stype == SourceFormat.DHIS2:
                df = read_dhis2_source(src_file)
                tables = {"dhis2_data_values": df}
            else:
                # Tentative générique CSV
                df = read_csv_source(src_file)
                tables = {src_file.stem: df}
        except Exception as exc:
            if quarantine_dir is not None:
                quarantine_file(
                    src_file,
                    quarantine_dir,
                    reason="UNREADABLE_RAW_FILE_CORRUPT",
                    error=exc,
                )
            continue

        # Sauvegarde Parquet de chaque table extraite
        seen_canonical: set[str] = set()
        for raw_tbl_name, df in tables.items():
            canon_name = _normalize_table_name(raw_tbl_name, source_type=stype)
            if canon_name in seen_canonical:
                continue
            seen_canonical.add(canon_name)

            parquet_path = out_dir / f"{canon_name}.parquet"

            # Idempotence : si la table Parquet existe et a exactement le même contenu, préserver
            if parquet_path.exists():
                try:
                    existing_table = pq.read_table(parquet_path)
                    if "content_hash" in existing_table.column_names:
                        existing_hashes = existing_table.column("content_hash").to_pylist()
                        new_hashes = [compute_row_hash(row) for _, row in df.iterrows()]
                        if existing_hashes == new_hashes:
                            result_tables[canon_name] = parquet_path
                            result_tables[raw_tbl_name] = parquet_path
                            continue
                except Exception:
                    pass

            df_with_audit = add_audit_columns(
                df, source_file=src_file.name, ingested_at=file_ingested_at
            )
            df_with_audit.to_parquet(parquet_path, index=False, engine="pyarrow")

            result_tables[canon_name] = parquet_path
            # Conserver également la clé d'origine brute
            result_tables[raw_tbl_name] = parquet_path

    return result_tables


# Alias pour compatibilité DISPATCH
convert_raw_to_bronze = convert_to_bronze


def validate_bronze_table(parquet_path: Path | str, strict: bool = False) -> bool:
    """Valide qu'une table Parquet contient les 4 colonnes d'audit et respecte les contraintes."""
    path = Path(parquet_path)
    if not path.exists():
        return False

    try:
        table = pq.read_table(path)
    except Exception:
        return False

    schema = table.schema
    field_names = set(schema.names)

    for col in AUDIT_COLUMNS:
        if col not in field_names:
            return False

    if strict:
        if table.num_rows == 0:
            return False

        def _is_str_type(t: pa.DataType) -> bool:
            return pa.types.is_string(t) or pa.types.is_large_string(t)

        # Vérification des types stricts
        if not _is_str_type(table.schema.field("source_file").type):
            return False
        if not table.schema.field("source_row").type.equals(pa.int64()):
            return False
        if not _is_str_type(table.schema.field("ingested_at").type):
            return False
        if not _is_str_type(table.schema.field("content_hash").type):
            return False

    return True


def validate_bronze_directory(bronze_dir: Path | str, strict: bool = False) -> dict[str, bool]:
    """Valide l'ensemble des tables Parquet du répertoire Bronze."""
    bdir = Path(bronze_dir)
    if not bdir.exists():
        return {}

    results: dict[str, bool] = {}
    for p_file in sorted(bdir.glob("*.parquet")):
        results[p_file.stem] = validate_bronze_table(p_file, strict=strict)

    return results


validate_bronze_tables = validate_bronze_directory
