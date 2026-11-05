"""Gestionnaire de la couche Raw : sanctuarisation et copie bit-à-bit.

Garantit :
- L'immuabilité et la copie conforme à l'octet près (AGENT.md #1)
- Le calcul d'empreinte cryptographique SHA-256 (64 hex)
- L'idempotence des opérations d'ingestion successive
- La génération et vérification du manifeste d'audit raw_manifest.json
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.ingestion.readers import detect_source_type
from src.ingestion.schemas import RawFileRecord, RawManifest


def calculate_file_sha256(path: Path | str, chunk_size: int = 65536) -> str:
    """Calcule l'empreinte SHA-256 hexadécimale d'un fichier."""
    path = Path(path)
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def ingest_raw_file(
    src_path: Path | str, raw_dir: Path | str, dry_run: bool = False
) -> RawFileRecord:
    """Copie un fichier source à l'identique dans data/raw/ sans altération et consigne ses métadonnées."""
    src = Path(src_path)
    dest_dir = Path(raw_dir)

    if not src.exists():
        raise FileNotFoundError(f"Fichier source introuvable : {src}")

    file_hash = calculate_file_sha256(src)
    file_size_bytes = src.stat().st_size
    ingested_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_type = detect_source_type(src)

    dest_file = dest_dir / src.name

    if dest_file.exists():
        existing_hash = calculate_file_sha256(dest_file)
        if existing_hash == file_hash:
            # Idempotence : si le fichier a déjà été ingéré, préserver son horodatage initial
            manifest_file = dest_dir / "raw_manifest.json"
            if manifest_file.exists():
                try:
                    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    for f in m_data.get("files", []):
                        if f.get("file_hash") == file_hash:
                            ingested_at = f.get("ingested_at", ingested_at)
                            break
                except Exception:
                    pass
        elif not dry_run:
            shutil.copy2(src, dest_file)
    elif not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_file)

    return RawFileRecord(
        source_path=str(src),
        raw_path=str(dest_file),
        file_hash=file_hash,
        file_size_bytes=file_size_bytes,
        ingested_at=ingested_at,
        source_type=source_type,
    )


def ingest_raw_batch(
    sources: list[Path | str],
    raw_dir: Path | str,
    dry_run: bool = False,
    batch_id: str | None = None,
) -> RawManifest:
    """Ingère un lot de fichiers sources dans data/raw/ et produit le manifeste raw_manifest.json."""
    dest_dir = Path(raw_dir)
    bid = batch_id or f"batch-raw-{uuid.uuid4().hex[:12]}"
    now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    records: list[RawFileRecord] = []
    for src in sources:
        record = ingest_raw_file(src, dest_dir, dry_run=dry_run)
        records.append(record)

    total_bytes = sum(r.file_size_bytes for r in records)

    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = dest_dir / "raw_manifest.json"
        if manifest_path.exists():
            try:
                old_m = json.loads(manifest_path.read_text(encoding="utf-8"))
                if [f.get("file_hash") for f in old_m.get("files", [])] == [
                    r.file_hash for r in records
                ]:
                    bid = old_m.get("batch_id", bid)
                    now_utc = old_m.get("created_at", now_utc)
            except Exception:
                pass

        manifest = RawManifest(
            batch_id=bid,
            created_at=now_utc,
            files=records,
            total_files=len(records),
            total_bytes=total_bytes,
        )
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    else:
        manifest = RawManifest(
            batch_id=bid,
            created_at=now_utc,
            files=records,
            total_files=len(records),
            total_bytes=total_bytes,
        )

    return manifest


def verify_raw_integrity(
    raw_dir: Path | str, manifest_path: Path | str | None = None
) -> tuple[bool, list[str]]:
    """Vérifie l'intégrité de la couche Raw en recalculant les empreintes SHA-256."""
    dir_path = Path(raw_dir)
    m_path = Path(manifest_path) if manifest_path else (dir_path / "raw_manifest.json")

    if not m_path.exists():
        # S'il n'y a aucun fichier de données dans raw_dir, intégrité triviale
        data_files = [p for p in dir_path.glob("*") if p.is_file() and p.name != ".gitkeep"]
        if not data_files:
            return (True, [])
        return (False, [f"Manifeste introuvable : {m_path}"])

    manifest = RawManifest.model_validate_json(m_path.read_text(encoding="utf-8"))
    corrupted_files: list[str] = []

    for file_rec in manifest.files:
        # Recherche par nom de fichier dans raw_dir
        target_file = dir_path / Path(file_rec.raw_path).name
        if not target_file.exists():
            corrupted_files.append(str(target_file))
            continue

        current_hash = calculate_file_sha256(target_file)
        if current_hash != file_rec.file_hash:
            corrupted_files.append(str(target_file))

    return (len(corrupted_files) == 0, corrupted_files)
