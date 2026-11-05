"""Schémas PyArrow et modèles Pydantic pour l'ingestion Raw, Bronze et Quarantaine.

Définit les formats sources, métadonnées techniques d'audit obligatoires (AGENT.md #2)
et structures de données d'ingestion conformes à la roadmap technique (Étape 5).
"""

from __future__ import annotations

from enum import StrEnum

import pyarrow as pa
from pydantic import BaseModel, Field, model_validator


class SourceFormat(StrEnum):
    """Formats de données sources supportés par le moteur d'ingestion."""

    EXCEL = "EXCEL"
    CSV = "CSV"
    FHIR = "FHIR"
    DHIS2 = "DHIS2"
    UNKNOWN = "UNKNOWN"


class RawFileRecord(BaseModel):
    """Métadonnées d'un fichier source copié à l'identique dans la couche Raw."""

    source_path: str
    raw_path: str
    file_hash: str  # SHA-256 (64 caractères hexadécimaux)
    file_size_bytes: int
    ingested_at: str  # Horodatage ISO 8601 UTC
    source_type: str | SourceFormat


class RawManifest(BaseModel):
    """Manifeste d'ingestion d'un lot dans data/raw/."""

    batch_id: str
    created_at: str
    files: list[RawFileRecord] = Field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0


class QuarantineRecord(BaseModel):
    """Fiche d'incident pour un fichier source corrompu ou invalide isolé en quarantaine."""

    source_file: str
    quarantined_at: str  # Horodatage ISO 8601 UTC
    quarantine_reason: str
    error_type: str
    error_details: str
    original_path: str | None = None
    file_hash: str | None = None


# 4 colonnes techniques d'audit obligatoires imposées par AGENT.md (Principe #2)
AUDIT_COLUMNS: list[str] = [
    "source_file",
    "source_row",
    "ingested_at",
    "content_hash",
]

BRONZE_METADATA_FIELDS: list[str] = AUDIT_COLUMNS

# Schéma PyArrow strict des colonnes d'audit Bronze
BRONZE_AUDIT_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("source_file", pa.string()),
        pa.field("source_row", pa.int64()),
        pa.field("ingested_at", pa.string()),
        pa.field("content_hash", pa.string()),
    ]
)


class IngestionResult(BaseModel):
    """Bilan récapitulatif de l'exécution d'un lot d'ingestion."""

    batch_id: str
    raw_files_count: int = 0
    bronze_tables_count: int = 0
    quarantined_files_count: int = 0
    total_rows_ingested: int = 0
    success: bool = True

    # Attributs complémentaires pour interopérabilité et métriques
    total_files: int = 0
    tables_converted: int = 0
    quarantined_count: int = 0

    @model_validator(mode="after")
    def sync_aliases(self) -> IngestionResult:
        """Synchronise les alias de métriques d'ingestion."""
        if self.total_files == 0 and self.raw_files_count > 0:
            self.total_files = self.raw_files_count
        elif self.raw_files_count == 0 and self.total_files > 0:
            self.raw_files_count = self.total_files

        if self.tables_converted == 0 and self.bronze_tables_count > 0:
            self.tables_converted = self.bronze_tables_count
        elif self.bronze_tables_count == 0 and self.tables_converted > 0:
            self.bronze_tables_count = self.tables_converted

        if self.quarantined_count == 0 and self.quarantined_files_count > 0:
            self.quarantined_count = self.quarantined_files_count
        elif self.quarantined_files_count == 0 and self.quarantined_count > 0:
            self.quarantined_files_count = self.quarantined_count

        return self
