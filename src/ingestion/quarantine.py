"""Gestionnaire de Quarantaine résiliente pour données sources invalides ou corrompues.

Garantit :
- L'isolation immédiate sans blocage de l'exécution du lot (Règle d'or de résilience)
- La génération d'une fiche d'incident codifiée (<source>.quarantine.json)
- L'audit et le rechargement de l'historique des exclusions
"""

from __future__ import annotations

import contextlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

from src.ingestion.raw import calculate_file_sha256
from src.ingestion.schemas import QuarantineRecord


def quarantine_file(
    src_path: Path | str,
    quarantine_dir: Path | str,
    reason: str,
    error: Exception | str,
) -> QuarantineRecord:
    """Isole un fichier corrompu dans data/quarantine/ avec sa fiche d'incident sans bloquer le lot."""
    src = Path(src_path)
    qdir = Path(quarantine_dir)
    qdir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    err_type = type(error).__name__ if isinstance(error, Exception) else "UnknownError"
    err_details = str(error)

    file_hash: str | None = None
    if src.exists():
        with contextlib.suppress(Exception):
            file_hash = calculate_file_sha256(src)

        # Copie de sauvegarde du fichier corrompu en quarantaine
        dest_copy = qdir / src.name
        with contextlib.suppress(Exception):
            shutil.copy2(src, dest_copy)

    record = QuarantineRecord(
        source_file=src.name,
        quarantined_at=now_utc,
        quarantine_reason=reason,
        error_type=err_type,
        error_details=err_details,
        original_path=str(src),
        file_hash=file_hash,
    )

    with contextlib.suppress(Exception):
        record_path = qdir / f"{src.stem}.quarantine.json"
        record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    return record


def load_quarantine_records(quarantine_dir: Path | str) -> list[QuarantineRecord]:
    """Charge l'ensemble des fiches d'incident archivées dans le répertoire de quarantaine."""
    qdir = Path(quarantine_dir)
    if not qdir.exists():
        return []

    records: list[QuarantineRecord] = []
    for json_path in sorted(qdir.glob("*.quarantine.json")):
        try:
            rec = QuarantineRecord.model_validate_json(json_path.read_text(encoding="utf-8"))
            records.append(rec)
        except Exception:
            continue

    if not records:
        # Fallback pour tout autre JSON de quarantaine
        for json_path in sorted(qdir.glob("*.json")):
            try:
                rec = QuarantineRecord.model_validate_json(json_path.read_text(encoding="utf-8"))
                records.append(rec)
            except Exception:
                continue

    return records
