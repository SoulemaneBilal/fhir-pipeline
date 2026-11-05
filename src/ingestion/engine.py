"""Moteur d'orchestration global de l'ingestion : Raw -> Bronze -> Quarantaine.

Responsable de :
- L'exécution de bout en bout du pipeline d'ingestion
- La préservation de la règle d'or de non-blocage sur incidents de quarantaine
- La simulation sans effets de bord via le mode dry-run
- La production des métriques et bilans d'ingestion (IngestionResult)
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from src.ingestion.bronze import (
    _normalize_table_name,
    add_audit_columns,
    compute_row_hash,
)
from src.ingestion.quarantine import quarantine_file
from src.ingestion.raw import (
    ingest_raw_file,
)
from src.ingestion.readers import (
    detect_source_type,
    read_csv_source,
    read_dhis2_source,
    read_excel_source,
    read_fhir_source,
)
from src.ingestion.schemas import (
    IngestionResult,
    RawFileRecord,
    RawManifest,
    SourceFormat,
)


class IngestionEngine:
    """Moteur central d'ingestion multiformat résilient."""

    def __init__(
        self,
        raw_dir: Path | str = "data/raw",
        bronze_dir: Path | str = "data/bronze",
        quarantine_dir: Path | str = "data/quarantine",
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.bronze_dir = Path(bronze_dir)
        self.quarantine_dir = Path(quarantine_dir)

    def run(
        self,
        sources: list[Path | str],
        dry_run: bool = False,
        batch_id: str | None = None,
    ) -> IngestionResult:
        """Exécute l'ingestion complète du lot de sources avec isolation résiliente des erreurs."""
        bid = batch_id or f"batch-{uuid.uuid4().hex[:12]}"

        # Mode simulation dry-run : aucune écriture sur le disque
        if dry_run:
            simulated_raw = 0
            simulated_tables: set[str] = set()
            simulated_quarantine = 0
            simulated_rows = 0

            for src_path in sources:
                src = Path(src_path)
                if not src.exists():
                    simulated_quarantine += 1
                    continue

                stype = detect_source_type(src)
                try:
                    tables: dict[str, Any] = {}
                    if stype == SourceFormat.EXCEL:
                        tables = read_excel_source(src)
                    elif stype == SourceFormat.CSV:
                        tables = {src.stem: read_csv_source(src)}
                    elif stype == SourceFormat.FHIR:
                        tables = read_fhir_source(src)
                    elif stype == SourceFormat.DHIS2:
                        tables = {"dhis2_data_values": read_dhis2_source(src)}
                    else:
                        tables = {src.stem: read_csv_source(src)}

                    simulated_raw += 1
                    seen_canon_sim: set[str] = set()
                    for tbl_name, df in tables.items():
                        canon = _normalize_table_name(tbl_name, source_type=stype)
                        if canon in seen_canon_sim:
                            continue
                        seen_canon_sim.add(canon)
                        simulated_tables.add(canon)
                        simulated_rows += len(df)
                except Exception:
                    simulated_quarantine += 1

            return IngestionResult(
                batch_id=bid,
                raw_files_count=simulated_raw,
                bronze_tables_count=len(simulated_tables),
                quarantined_files_count=simulated_quarantine,
                total_rows_ingested=simulated_rows,
                success=True,
            )

        # Mode nominal d'exécution avec persistance
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.bronze_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        raw_records: list[RawFileRecord] = []
        tables_generated: set[str] = set()
        quarantined_count = 0
        total_rows = 0

        for src_path in sources:
            src = Path(src_path)

            if not src.exists():
                quarantine_file(
                    src,
                    self.quarantine_dir,
                    reason="SOURCE_FILE_NOT_FOUND",
                    error=FileNotFoundError(f"Source introuvable : {src}"),
                )
                quarantined_count += 1
                continue

            stype = detect_source_type(src)
            tables: dict[str, Any] = {}

            # Règle d'or : tentative de lecture avec isolation en cas d'échec
            try:
                if stype == SourceFormat.EXCEL:
                    tables = read_excel_source(src)
                elif stype == SourceFormat.CSV:
                    tables = {src.stem: read_csv_source(src)}
                elif stype == SourceFormat.FHIR:
                    tables = read_fhir_source(src)
                elif stype == SourceFormat.DHIS2:
                    tables = {"dhis2_data_values": read_dhis2_source(src)}
                else:
                    tables = {src.stem: read_csv_source(src)}
            except Exception as exc:
                quarantine_file(
                    src,
                    self.quarantine_dir,
                    reason="CORRUPTED_SOURCE_FILE",
                    error=exc,
                )
                quarantined_count += 1
                continue

            # 1. Sanctuarisation dans la couche Raw
            raw_rec = ingest_raw_file(src, self.raw_dir, dry_run=False)
            raw_records.append(raw_rec)

            # 2. Structuration dans la couche Bronze Parquet
            ingested_at = raw_rec.ingested_at
            seen_canon_names: set[str] = set()

            try:
                for raw_tbl_name, df in tables.items():
                    canon_name = _normalize_table_name(raw_tbl_name, source_type=stype)
                    if canon_name in seen_canon_names:
                        continue
                    seen_canon_names.add(canon_name)

                    dest_parquet = self.bronze_dir / f"{canon_name}.parquet"
                    if dest_parquet.exists():
                        try:
                            existing_table = pq.read_table(dest_parquet)
                            if "content_hash" in existing_table.column_names:
                                existing_hashes = existing_table.column("content_hash").to_pylist()
                                new_hashes = [compute_row_hash(row) for _, row in df.iterrows()]
                                if existing_hashes == new_hashes:
                                    tables_generated.add(canon_name)
                                    total_rows += len(df)
                                    continue
                        except Exception:
                            pass

                    df_audit = add_audit_columns(df, source_file=src.name, ingested_at=ingested_at)
                    dest_parquet = self.bronze_dir / f"{canon_name}.parquet"
                    df_audit.to_parquet(dest_parquet, index=False, engine="pyarrow")

                    tables_generated.add(canon_name)
                    total_rows += len(df)
            except Exception as exc:
                quarantine_file(
                    src,
                    self.quarantine_dir,
                    reason="PARQUET_CONVERSION_ERROR",
                    error=exc,
                )
                quarantined_count += 1
                continue

        # 3. Génération du manifeste Raw d'audit
        if raw_records:
            now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            manifest_path = self.raw_dir / "raw_manifest.json"
            if manifest_path.exists():
                try:
                    old_m = json.loads(manifest_path.read_text(encoding="utf-8"))
                    if [f.get("file_hash") for f in old_m.get("files", [])] == [
                        r.file_hash for r in raw_records
                    ]:
                        bid = old_m.get("batch_id", bid)
                        now_utc = old_m.get("created_at", now_utc)
                except Exception:
                    pass

            manifest = RawManifest(
                batch_id=bid,
                created_at=now_utc,
                files=raw_records,
                total_files=len(raw_records),
                total_bytes=sum(r.file_size_bytes for r in raw_records),
            )
            manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        return IngestionResult(
            batch_id=bid,
            raw_files_count=len(raw_records),
            bronze_tables_count=len(tables_generated),
            quarantined_files_count=quarantined_count,
            total_rows_ingested=total_rows,
            success=True,
        )


def run_ingestion_pipeline(
    sources: list[Path | str],
    raw_dir: Path | str = "data/raw",
    bronze_dir: Path | str = "data/bronze",
    quarantine_dir: Path | str = "data/quarantine",
    dry_run: bool = False,
    batch_id: str | None = None,
) -> IngestionResult:
    """Point d'entrée fonctionnel du pipeline d'ingestion."""
    engine = IngestionEngine(
        raw_dir=raw_dir,
        bronze_dir=bronze_dir,
        quarantine_dir=quarantine_dir,
    )
    return engine.run(sources=sources, dry_run=dry_run, batch_id=batch_id)
