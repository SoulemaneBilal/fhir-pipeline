"""Module d'ingestion multiformat vers les couches Raw, Bronze et Quarantaine.

Responsable de :
- La sanctuarisation et copie bit-à-bit des sources (data/raw/)
- L'injection des 4 colonnes d'audit et conversion Parquet (data/bronze/)
- L'isolation non-bloquante des fichiers corrompus (data/quarantine/)
- L'orchestration E2E via IngestionEngine et CLI
"""

from __future__ import annotations

from src.ingestion.bronze import (
    add_audit_columns,
    compute_row_hash,
    convert_raw_to_bronze,
    convert_to_bronze,
    validate_bronze_directory,
    validate_bronze_table,
    validate_bronze_tables,
)
from src.ingestion.engine import IngestionEngine, run_ingestion_pipeline
from src.ingestion.quarantine import load_quarantine_records, quarantine_file
from src.ingestion.raw import (
    calculate_file_sha256,
    ingest_raw_batch,
    ingest_raw_file,
    verify_raw_integrity,
)
from src.ingestion.readers import (
    detect_source_type,
    read_csv_source,
    read_dhis2_source,
    read_excel_source,
    read_fhir_source,
)
from src.ingestion.schemas import (
    AUDIT_COLUMNS,
    BRONZE_AUDIT_SCHEMA,
    BRONZE_METADATA_FIELDS,
    IngestionResult,
    QuarantineRecord,
    RawFileRecord,
    RawManifest,
    SourceFormat,
)

__all__ = [
    "AUDIT_COLUMNS",
    "BRONZE_AUDIT_SCHEMA",
    "BRONZE_METADATA_FIELDS",
    "IngestionEngine",
    "IngestionResult",
    "QuarantineRecord",
    "RawFileRecord",
    "RawManifest",
    "SourceFormat",
    "add_audit_columns",
    "calculate_file_sha256",
    "compute_row_hash",
    "convert_raw_to_bronze",
    "convert_to_bronze",
    "detect_source_type",
    "ingest_raw_batch",
    "ingest_raw_file",
    "load_quarantine_records",
    "quarantine_file",
    "read_csv_source",
    "read_dhis2_source",
    "read_excel_source",
    "read_fhir_source",
    "run_ingestion_pipeline",
    "validate_bronze_directory",
    "validate_bronze_table",
    "validate_bronze_tables",
    "verify_raw_integrity",
]
