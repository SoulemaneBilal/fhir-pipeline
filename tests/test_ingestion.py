"""Tests E2E, unitaires et de validation du Moteur d'Ingestion Multi-Formats (Étape 5).

Conforme aux spécifications formelles de DISPATCH.md, SCOPE.md, Roadmap technique.md §5,
AGENT.md (Principes #1, #2, #3, #6) et SYNTHESE_PROJET.md §3.1 (Étape 5).

Structure de la suite de tests :
- Tier 1 : Modèles, Schémas & Métadonnées d'Audit (Pydantic, PyArrow, SourceFormat, RawManifest, QuarantineRecord)
- Tier 2 : Lecteurs Spécialisés Multi-Formats (Excel multi-onglets, CSV délimiteurs multiples & encodages UTF-8/Latin-1/CP1252, FHIR R4 Bundles JSON, exports DHIS2 dataValueSets)
- Tier 3 : Couche Raw & Sanctuarisation Bit-à-Bit (copie conforme SHA-256, manifeste d'ingestion brute, idempotence, intégrité)
- Tier 4 : Couche Bronze & Structuration Parquet (4 colonnes techniques obligatoires source_file/source_row/ingested_at/content_hash, égalité stricte des comptes, schémas typés, déterminisme)
- Tier 5 : Quarantaine Résiliente & Règle d'Or de Non-Blocage (isolement des fichiers corrompus avec métadonnées d'erreur, poursuite continue du lot pour les fichiers valides)
- Tier 6 : Moteur d'Ingestion Global & Pipeline E2E (orchestration Raw -> Bronze -> Quarantaine, mode dry-run, métriques récapitulatives)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import openpyxl
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

IS_STRICT = os.environ.get("STRICT_E2E") == "1"

DATA_RAW_DIR = Path("data/raw")
DATA_BRONZE_DIR = Path("data/bronze")
DATA_QUARANTINE_DIR = Path("data/quarantine")

# 4 colonnes techniques d'audit obligatoires imposées par AGENT.md (Principe #2)
MANDATORY_AUDIT_COLUMNS = [
    "source_file",
    "source_row",
    "ingested_at",
    "content_hash",
]

# Formats sources canoniques
EXPECTED_SOURCE_FORMATS = {"EXCEL", "CSV", "FHIR", "DHIS2", "UNKNOWN"}

# Expressions régulières de validation
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ISO8601_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)


# ==============================================================================
# Fonctions d'import et de résolution dynamique (Progressive Testability)
# ==============================================================================


def _require_schemas_module() -> Any:
    """Importe dynamiquement le module de schémas d'ingestion."""
    try:
        import src.ingestion.schemas as schemas_mod

        return schemas_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.ingestion.schemas obligatoire manquant : {exc}")
        pytest.skip(f"src.ingestion.schemas en attente d'implémentation : {exc}")


def _require_readers_module() -> Any:
    """Importe dynamiquement le module de lecteurs spécialisés multi-formats."""
    try:
        import src.ingestion.readers as readers_mod

        return readers_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.ingestion.readers obligatoire manquant : {exc}")
        pytest.skip(f"src.ingestion.readers en attente d'implémentation : {exc}")


def _require_raw_module() -> Any:
    """Importe dynamiquement le module d'ingestion Raw bit-à-bit."""
    try:
        import src.ingestion.raw as raw_mod

        return raw_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.ingestion.raw obligatoire manquant : {exc}")
        pytest.skip(f"src.ingestion.raw en attente d'implémentation : {exc}")


def _require_bronze_module() -> Any:
    """Importe dynamiquement le module de structuration Bronze Parquet."""
    try:
        import src.ingestion.bronze as bronze_mod

        return bronze_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.ingestion.bronze obligatoire manquant : {exc}")
        pytest.skip(f"src.ingestion.bronze en attente d'implémentation : {exc}")


def _require_quarantine_module() -> Any:
    """Importe dynamiquement le module de quarantaine résiliente."""
    try:
        import src.ingestion.quarantine as quarantine_mod

        return quarantine_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.ingestion.quarantine obligatoire manquant : {exc}")
        pytest.skip(f"src.ingestion.quarantine en attente d'implémentation : {exc}")


def _require_engine_module() -> Any:
    """Importe dynamiquement le module du moteur global d'ingestion."""
    try:
        import src.ingestion.engine as engine_mod

        return engine_mod
    except ImportError as exc:
        if IS_STRICT:
            pytest.fail(f"Module src.ingestion.engine obligatoire manquant : {exc}")
        pytest.skip(f"src.ingestion.engine en attente d'implémentation : {exc}")


# ==============================================================================
# Utilitaires & Générateurs de Données de Test
# ==============================================================================


def _compute_sha256(data: bytes | str) -> str:
    """Calcule l'empreinte SHA-256 d'une chaîne ou d'un flux binaire."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _create_sample_excel_workbook(path: Path) -> Path:
    """Crée un classeur Excel multi-feuilles réaliste pour les tests d'ingestion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # Feuille 1 : Patients
    ws_patients = wb.active
    ws_patients.title = "patients"
    ws_patients.append(
        ["patient_id", "family_name", "given_name", "gender", "birth_date", "prefecture"]
    )
    ws_patients.append(["PAT-001", "MENSAH", "Koffi", "M", "1985-04-12", "Golfe"])
    ws_patients.append(["PAT-002", "LAWSON", "Akossiwa", "F", "1992-09-23", "Lacs"])
    ws_patients.append(["PAT-003", "ADJAMAGBO", "Komla", "M", "1978-11-05", "Kloto"])

    # Feuille 2 : Encounters
    ws_encounters = wb.create_sheet("encounters")
    ws_encounters.append(
        ["encounter_id", "patient_id", "facility_name", "start_date", "reason_code"]
    )
    ws_encounters.append(["ENC-001", "PAT-001", "CHU Sylvanus Olympio", "2026-01-15", "B54"])
    ws_encounters.append(["ENC-002", "PAT-002", "CMS Adidogomé", "2026-02-10", "A09"])

    # Feuille 3 : Observations
    ws_observations = wb.create_sheet("observations")
    ws_observations.append(["observation_id", "patient_id", "code", "value", "unit"])
    ws_observations.append(["OBS-001", "PAT-001", "8310-5", 38.5, "Cel"])
    ws_observations.append(["OBS-002", "PAT-002", "8480-6", 120.0, "mm[Hg]"])

    wb.save(path)
    return path


def _create_sample_fhir_bundle(path: Path) -> Path:
    """Crée un Bundle FHIR R4 JSON valide contenant Patient et Encounter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle_data = {
        "resourceType": "Bundle",
        "id": "bundle-test-ingestion-001",
        "type": "collection",
        "total": 3,
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-001",
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "name": [{"family": "AGBO", "given": ["Kossi"]}],
                    "gender": "male",
                    "birthDate": "1990-06-15",
                },
            },
            {
                "fullUrl": "urn:uuid:patient-002",
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-002",
                    "name": [{"family": "DOSSEH", "given": ["Afi"]}],
                    "gender": "female",
                    "birthDate": "1995-12-01",
                },
            },
            {
                "fullUrl": "urn:uuid:encounter-001",
                "resource": {
                    "resourceType": "Encounter",
                    "id": "encounter-001",
                    "status": "finished",
                    "class": {"code": "AMB", "display": "ambulatory"},
                    "subject": {"reference": "Patient/patient-001"},
                    "period": {"start": "2026-02-14T08:30:00Z"},
                },
            },
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle_data, f, ensure_ascii=False, indent=2)
    return path


def _create_sample_dhis2_json(path: Path) -> Path:
    """Crée un export JSON DHIS2 dataValueSets conforme."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dhis2_data = {
        "dataValues": [
            {
                "dataElement": "MALARIA_CONFIRMED",
                "period": "202601",
                "orgUnit": "OU_GOLFE_01",
                "categoryOptionCombo": "DEFAULT",
                "attributeOptionCombo": "DEFAULT",
                "value": "142",
                "storedBy": "agent_sante_lomé",
                "created": "2026-02-01T10:00:00Z",
                "lastUpdated": "2026-02-01T10:00:00Z",
            },
            {
                "dataElement": "CHOLERA_SUSPECTED",
                "period": "202601",
                "orgUnit": "OU_LACS_02",
                "categoryOptionCombo": "DEFAULT",
                "attributeOptionCombo": "DEFAULT",
                "value": "12",
                "storedBy": "agent_sante_aného",
                "created": "2026-02-01T10:05:00Z",
                "lastUpdated": "2026-02-01T10:05:00Z",
            },
            {
                "dataElement": "MEASLES_IMMUNIZED",
                "period": "202601",
                "orgUnit": "OU_KLOTO_01",
                "categoryOptionCombo": "DEFAULT",
                "attributeOptionCombo": "DEFAULT",
                "value": "89",
                "storedBy": "agent_sante_kpalimé",
                "created": "2026-02-01T10:10:00Z",
                "lastUpdated": "2026-02-01T10:10:00Z",
            },
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dhis2_data, f, ensure_ascii=False, indent=2)
    return path


# ==============================================================================
# Tier 1 : Modèles, Schémas & Métadonnées d'Audit (src.ingestion.schemas)
# ==============================================================================


def test_schemas_source_format_enum() -> None:
    """Vérifie que l'énumération SourceFormat définit tous les formats canoniques."""
    mod = _require_schemas_module()
    assert hasattr(mod, "SourceFormat"), "Enum 'SourceFormat' manquant dans src.ingestion.schemas"
    source_format_cls = mod.SourceFormat

    # Vérification de l'existence des membres requis
    enum_members = {member.name for member in source_format_cls}
    for expected in EXPECTED_SOURCE_FORMATS:
        assert expected in enum_members, f"Membre SourceFormat.{expected} manquant"


def test_schemas_raw_file_record_model() -> None:
    """Vérifie le modèle Pydantic RawFileRecord et ses contraintes de validation."""
    mod = _require_schemas_module()
    assert hasattr(mod, "RawFileRecord"), "Modèle 'RawFileRecord' manquant"
    record_cls = mod.RawFileRecord

    record = record_cls(
        source_path="/tmp/external/patients.csv",
        raw_path="data/raw/patients.csv",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1024,
        ingested_at="2026-11-05T20:15:00Z",
        source_type="CSV",
    )

    assert record.source_path == "/tmp/external/patients.csv"
    assert record.raw_path == "data/raw/patients.csv"
    assert SHA256_HEX_PATTERN.match(record.file_hash)
    assert record.file_size_bytes == 1024
    assert ISO8601_TIMESTAMP_PATTERN.match(record.ingested_at)


def test_schemas_raw_manifest_model() -> None:
    """Vérifie le modèle Pydantic RawManifest et sa sérialisation JSON."""
    mod = _require_schemas_module()
    assert hasattr(mod, "RawManifest"), "Modèle 'RawManifest' manquant"
    manifest_cls = mod.RawManifest
    record_cls = mod.RawFileRecord

    file_rec = record_cls(
        source_path="inputs/clinique.xlsx",
        raw_path="data/raw/clinique.xlsx",
        file_hash=_compute_sha256("test-content"),
        file_size_bytes=42,
        ingested_at="2026-11-05T20:15:00Z",
        source_type="EXCEL",
    )

    manifest = manifest_cls(
        batch_id="batch-test-001",
        created_at="2026-11-05T20:15:00Z",
        files=[file_rec],
        total_files=1,
        total_bytes=42,
    )

    json_str = (
        manifest.model_dump_json() if hasattr(manifest, "model_dump_json") else manifest.json()
    )
    assert "batch-test-001" in json_str
    assert "clinique.xlsx" in json_str

    # Test round-trip
    restored = (
        manifest_cls.model_validate_json(json_str)
        if hasattr(manifest_cls, "model_validate_json")
        else manifest_cls.parse_raw(json_str)
    )
    assert restored.batch_id == manifest.batch_id
    assert len(restored.files) == 1
    assert restored.files[0].file_hash == file_rec.file_hash


def test_schemas_quarantine_record_model() -> None:
    """Vérifie le modèle Pydantic QuarantineRecord stockant les motifs codifiés d'exclusion."""
    mod = _require_schemas_module()
    assert hasattr(mod, "QuarantineRecord"), "Modèle 'QuarantineRecord' manquant"
    quarantine_cls = mod.QuarantineRecord

    rec = quarantine_cls(
        source_file="corrupted_patients.json",
        quarantined_at="2026-11-05T20:15:00Z",
        quarantine_reason="INVALID_JSON_SYNTAX",
        error_type="JSONDecodeError",
        error_details="Expecting property name enclosed in double quotes: line 2 column 5",
        original_path="/tmp/sources/corrupted_patients.json",
    )

    assert rec.source_file == "corrupted_patients.json"
    assert rec.quarantine_reason == "INVALID_JSON_SYNTAX"
    assert rec.error_type == "JSONDecodeError"
    assert "Expecting property name" in rec.error_details


def test_schemas_audit_columns_and_arrow_schema() -> None:
    """Vérifie que les 4 colonnes techniques d'audit sont définies avec types PyArrow stricts."""
    mod = _require_schemas_module()
    assert hasattr(mod, "AUDIT_COLUMNS"), (
        "Constante 'AUDIT_COLUMNS' manquante dans src.ingestion.schemas"
    )
    audit_cols = mod.AUDIT_COLUMNS
    for col in MANDATORY_AUDIT_COLUMNS:
        assert col in audit_cols, (
            f"Colonne d'audit obligatoire '{col}' manquante dans AUDIT_COLUMNS"
        )

    assert hasattr(mod, "BRONZE_AUDIT_SCHEMA"), "Schéma PyArrow 'BRONZE_AUDIT_SCHEMA' manquant"
    arrow_schema = mod.BRONZE_AUDIT_SCHEMA
    assert isinstance(arrow_schema, pa.Schema), (
        "BRONZE_AUDIT_SCHEMA doit être une instance de pyarrow.Schema"
    )

    # Vérification des types attendus pour les 4 colonnes
    field_names = arrow_schema.names
    for col in MANDATORY_AUDIT_COLUMNS:
        assert col in field_names, f"Colonne '{col}' absente de BRONZE_AUDIT_SCHEMA"

    assert pa.types.is_string(arrow_schema.field("source_file").type)
    assert pa.types.is_integer(arrow_schema.field("source_row").type)
    assert pa.types.is_string(arrow_schema.field("ingested_at").type)
    assert pa.types.is_string(arrow_schema.field("content_hash").type)


# ==============================================================================
# Tier 2 : Lecteurs Spécialisés Multi-Formats (src.ingestion.readers)
# ==============================================================================


def test_reader_excel_multisheet(tmp_path: Path) -> None:
    """Vérifie la lecture fidèle d'un classeur Excel multi-onglets (.xlsx) vers un dict de DataFrames."""
    mod = _require_readers_module()
    excel_path = tmp_path / "test_multisheet.xlsx"
    _create_sample_excel_workbook(excel_path)

    read_excel_fn = mod.read_excel_source
    tables = read_excel_fn(excel_path)

    assert isinstance(tables, dict), "read_excel_source doit renvoyer un dictionnaire de DataFrames"
    assert "patients" in tables, "Feuille 'patients' manquante dans le résultat"
    assert "encounters" in tables, "Feuille 'encounters' manquante dans le résultat"
    assert "observations" in tables, "Feuille 'observations' manquante dans le résultat"

    df_patients = tables["patients"]
    assert len(df_patients) == 3, f"Attendu 3 patients, obtenu {len(df_patients)}"
    assert list(df_patients["family_name"]) == ["MENSAH", "LAWSON", "ADJAMAGBO"]

    df_encounters = tables["encounters"]
    assert len(df_encounters) == 2
    assert "CHU Sylvanus Olympio" in df_encounters["facility_name"].values


def test_reader_excel_sheet_selection(tmp_path: Path) -> None:
    """Vérifie le filtrage d'onglets spécifiques dans un classeur Excel."""
    mod = _require_readers_module()
    excel_path = tmp_path / "test_filter_sheets.xlsx"
    _create_sample_excel_workbook(excel_path)

    read_excel_fn = mod.read_excel_source
    tables = read_excel_fn(excel_path, sheets=["patients"])

    assert "patients" in tables
    assert "encounters" not in tables
    assert len(tables) == 1


def test_reader_excel_file_not_found(tmp_path: Path) -> None:
    """Vérifie que la lecture d'un fichier Excel inexistant lève FileNotFoundError."""
    mod = _require_readers_module()
    read_excel_fn = mod.read_excel_source
    missing_path = tmp_path / "inexistant.xlsx"
    with pytest.raises(FileNotFoundError):
        read_excel_fn(missing_path)


@pytest.mark.parametrize(
    ("delimiter", "sample_csv_text"),
    [
        (
            ",",
            "patient_id,name,gender,age\nPAT-1,Koffi,M,35\nPAT-2,Akossiwa,F,28\nPAT-3,Komla,M,45\n",
        ),
        (
            ";",
            "patient_id;name;gender;age\nPAT-1;Koffi;M;35\nPAT-2;Akossiwa;F;28\nPAT-3;Komla;M;45\n",
        ),
        (
            "\t",
            "patient_id\tname\tgender\tage\nPAT-1\tKoffi\tM\t35\nPAT-2\tAkossiwa\tF\t28\nPAT-3\tKomla\tM\t45\n",
        ),
        (
            "|",
            "patient_id|name|gender|age\nPAT-1|Koffi|M|35\nPAT-2|Akossiwa|F|28\nPAT-3|Komla|M|45\n",
        ),
    ],
)
def test_reader_csv_delimiter_autodetection(
    tmp_path: Path, delimiter: str, sample_csv_text: str
) -> None:
    """Vérifie la détection automatique des séparateurs CSV (virgule, point-virgule, tab, pipe)."""
    mod = _require_readers_module()
    read_csv_fn = mod.read_csv_source

    csv_file = tmp_path / f"test_delim_{ord(delimiter)}.csv"
    csv_file.write_text(sample_csv_text, encoding="utf-8")

    df = read_csv_fn(csv_file)
    assert isinstance(df, pd.DataFrame), "read_csv_source doit renvoyer un DataFrame"
    assert len(df) == 3, f"Échec détection délimiteur '{delimiter}', 3 lignes attendues"
    expected_cols = {"patient_id", "name", "gender", "age"}
    assert set(df.columns) == expected_cols, f"Colonnes non reconnues avec délimiteur '{delimiter}'"


@pytest.mark.parametrize(
    ("encoding", "french_text"),
    [
        (
            "utf-8",
            "patient_id;family_name;facility;symptom\nPAT-1;Émile;Hôpital de Lomé;fièvre aiguë\nPAT-2;Koffi;CMS Tokoin;diarrhée profuse\n",
        ),
        (
            "latin-1",
            "patient_id;family_name;facility;symptom\nPAT-1;Émile;Hôpital de Lomé;fièvre aiguë\nPAT-2;Koffi;CMS Tokoin;diarrhée profuse\n",
        ),
        (
            "cp1252",
            "patient_id;family_name;facility;symptom\nPAT-1;Émile;Hôpital de Lomé;fièvre aiguë\nPAT-2;Koffi;CMS Tokoin;diarrhée profuse\n",
        ),
    ],
)
def test_reader_csv_multi_encodings(tmp_path: Path, encoding: str, french_text: str) -> None:
    """Vérifie la détection et la lecture fidèle des encodages fréquents sans mojibake."""
    mod = _require_readers_module()
    read_csv_fn = mod.read_csv_source

    csv_file = tmp_path / f"test_enc_{encoding}.csv"
    csv_file.write_bytes(french_text.encode(encoding))

    df = read_csv_fn(csv_file)
    assert len(df) == 2
    # Vérification de l'intégrité des caractères diacritiques français
    row1_name = str(df.iloc[0]["family_name"])
    row1_facility = str(df.iloc[0]["facility"])
    row1_symptom = str(df.iloc[0]["symptom"])

    assert "Émile" in row1_name or "Emile" in row1_name, (
        f"Altération patronyme sous {encoding} : {row1_name}"
    )
    assert "Hôpital" in row1_facility or "Hopital" in row1_facility
    assert "fièvre" in row1_symptom or "aigue" in row1_symptom or "aiguë" in row1_symptom


def test_reader_fhir_bundle_json(tmp_path: Path) -> None:
    """Vérifie l'extraction tabulaire d'un Bundle FHIR R4 JSON vers des DataFrames par type de ressource."""
    mod = _require_readers_module()
    fhir_path = tmp_path / "test_bundle.json"
    _create_sample_fhir_bundle(fhir_path)

    read_fhir_fn = mod.read_fhir_source
    tables = read_fhir_fn(fhir_path)

    assert isinstance(tables, dict), (
        "read_fhir_source doit renvoyer un dict de DataFrames par resourceType"
    )
    assert "Patient" in tables or "patients" in tables, "Table Patient absente du parsing FHIR"

    patient_key = "Patient" if "Patient" in tables else "patients"
    df_patient = tables[patient_key]
    assert len(df_patient) == 2, f"Attendu 2 patients dans le bundle, obtenu {len(df_patient)}"


def test_reader_dhis2_data_value_sets(tmp_path: Path) -> None:
    """Vérifie la lecture d'un export JSON dataValueSets de DHIS2."""
    mod = _require_readers_module()
    dhis2_path = tmp_path / "dhis2_export.json"
    _create_sample_dhis2_json(dhis2_path)

    read_dhis2_fn = mod.read_dhis2_source
    df = read_dhis2_fn(dhis2_path)

    assert isinstance(df, pd.DataFrame), "read_dhis2_source doit renvoyer un DataFrame"
    assert len(df) == 3, f"Attendu 3 dataValues DHIS2, obtenu {len(df)}"
    assert "dataElement" in df.columns
    assert "period" in df.columns
    assert "orgUnit" in df.columns
    assert "value" in df.columns
    assert "MALARIA_CONFIRMED" in df["dataElement"].values


def test_detect_source_type(tmp_path: Path) -> None:
    """Vérifie la détection automatique du format source via detect_source_type."""
    mod = _require_readers_module()
    assert hasattr(mod, "detect_source_type"), "Fonction 'detect_source_type' manquante"
    detect_fn = mod.detect_source_type

    # 1. Fichier Excel
    excel_file = _create_sample_excel_workbook(tmp_path / "sample.xlsx")
    assert str(detect_fn(excel_file)).upper().endswith("EXCEL") or detect_fn(excel_file) == "excel"

    # 2. Fichier CSV
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("a,b\n1,2\n", encoding="utf-8")
    assert str(detect_fn(csv_file)).upper().endswith("CSV") or detect_fn(csv_file) == "csv"

    # 3. Fichier FHIR JSON
    fhir_file = _create_sample_fhir_bundle(tmp_path / "bundle.json")
    assert str(detect_fn(fhir_file)).upper().endswith("FHIR") or detect_fn(fhir_file) == "fhir"

    # 4. Fichier DHIS2 JSON
    dhis2_file = _create_sample_dhis2_json(tmp_path / "dhis2.json")
    assert str(detect_fn(dhis2_file)).upper().endswith("DHIS2") or detect_fn(dhis2_file) == "dhis2"


# ==============================================================================
# Tier 3 : Couche Raw & Sanctuarisation Bit-à-Bit (src.ingestion.raw)
# ==============================================================================


def test_raw_file_bit_for_bit_copy(tmp_path: Path) -> None:
    """Vérifie que l'ingestion Raw copie le fichier à l'identique (stricte égalité binaire et SHA-256)."""
    assert DATA_RAW_DIR.name == "raw"
    raw_mod = _require_raw_module()
    ingest_raw_fn = raw_mod.ingest_raw_file

    src_dir = tmp_path / "sources"
    src_dir.mkdir(parents=True)
    src_file = src_dir / "origin.csv"
    payload = b"id;val\n1;test_alpha\n2;test_beta\n"
    src_file.write_bytes(payload)
    original_sha256 = _compute_sha256(payload)

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True)

    record = ingest_raw_fn(src_file, raw_dir)

    # Vérification du fichier copié
    dest_file = raw_dir / "origin.csv"
    assert dest_file.exists(), f"Fichier raw manquant : {dest_file}"
    raw_bytes = dest_file.read_bytes()
    assert raw_bytes == payload, "Violation de la copie bit-à-bit : octets différents !"
    assert _compute_sha256(raw_bytes) == original_sha256

    # Vérification des métadonnées renvoyées
    assert record.file_hash == original_sha256
    assert record.file_size_bytes == len(payload)
    assert ISO8601_TIMESTAMP_PATTERN.match(record.ingested_at)


def test_raw_batch_manifest_generation(tmp_path: Path) -> None:
    """Vérifie l'ingestion d'un lot de sources et la génération conforme du manifeste d'audit."""
    raw_mod = _require_raw_module()
    ingest_batch_fn = raw_mod.ingest_raw_batch

    src_dir = tmp_path / "batch_sources"
    src_dir.mkdir()
    f1 = _create_sample_excel_workbook(src_dir / "clinique.xlsx")
    f2 = src_dir / "patients.csv"
    f2.write_text("id,name\n1,Koffi\n2,Afi\n", encoding="utf-8")
    f3 = _create_sample_fhir_bundle(src_dir / "bundle.json")

    raw_dir = tmp_path / "raw_dest"
    raw_dir.mkdir()

    manifest = ingest_batch_fn([f1, f2, f3], raw_dir, batch_id="batch-raw-test-42")

    assert manifest.batch_id == "batch-raw-test-42"
    assert manifest.total_files == 3
    assert len(manifest.files) == 3

    # Vérification de la persistance du manifeste sur le disque
    manifest_file = raw_dir / "raw_manifest.json"
    if manifest_file.exists():
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest_data["batch_id"] == "batch-raw-test-42"
        assert len(manifest_data["files"]) == 3


def test_raw_idempotence(tmp_path: Path) -> None:
    """Vérifie qu'une ré-ingestion successive ne modifie pas le fichier raw ni son empreinte SHA-256."""
    raw_mod = _require_raw_module()
    ingest_raw_fn = raw_mod.ingest_raw_file

    src_file = tmp_path / "constant.csv"
    src_file.write_text("col1;col2\nvalA;valB\n", encoding="utf-8")
    raw_dir = tmp_path / "raw_idempotence"
    raw_dir.mkdir()

    # Première ingestion
    rec1 = ingest_raw_fn(src_file, raw_dir)
    hash_1 = rec1.file_hash
    dest_path = raw_dir / "constant.csv"

    # Deuxième ingestion
    rec2 = ingest_raw_fn(src_file, raw_dir)
    hash_2 = rec2.file_hash

    assert hash_1 == hash_2, "L'empreinte SHA-256 a divergé entre deux ingestions identiques !"
    # Vérification que le contenu reste strictement inchangé
    assert dest_path.read_text(encoding="utf-8") == "col1;col2\nvalA;valB\n"


def test_raw_integrity_verification(tmp_path: Path) -> None:
    """Vérifie la détection de corruption ou d'altération dans la couche Raw."""
    raw_mod = _require_raw_module()
    ingest_batch_fn = raw_mod.ingest_raw_batch
    verify_fn = raw_mod.verify_raw_integrity

    src_dir = tmp_path / "src_integrity"
    src_dir.mkdir()
    f1 = src_dir / "data.csv"
    f1.write_text("col1,col2\n10,20\n", encoding="utf-8")

    raw_dir = tmp_path / "raw_integrity"
    raw_dir.mkdir()

    ingest_batch_fn([f1], raw_dir)

    # 1. Vérification nominale : intégrité valide
    valid_res = verify_fn(raw_dir)
    is_valid = valid_res[0] if isinstance(valid_res, tuple) else valid_res
    assert is_valid is True, "L'intégrité d'une couche Raw intacte doit être validée"

    # 2. Corruption volontaire d'un octet dans raw/data.csv
    tampered_file = raw_dir / "data.csv"
    tampered_file.write_text("col1,col2\n10,99\n", encoding="utf-8")  # modification illicite

    # 3. La vérification doit échouer
    corrupt_res = verify_fn(raw_dir)
    is_corrupt_valid = corrupt_res[0] if isinstance(corrupt_res, tuple) else corrupt_res
    assert is_corrupt_valid is False, (
        "L'altération de data.csv aurait dû être détectée par verify_raw_integrity"
    )


# ==============================================================================
# Tier 4 : Couche Bronze & Structuration Parquet (src.ingestion.bronze)
# ==============================================================================


def test_bronze_mandatory_audit_columns_injection(tmp_path: Path) -> None:
    """Vérifie l'injection systématique des 4 colonnes techniques d'audit dans les tables Bronze."""
    assert DATA_BRONZE_DIR.name == "bronze"
    bronze_mod = _require_bronze_module()
    convert_fn = bronze_mod.convert_to_bronze

    # Préparation d'une source brute
    raw_dir = tmp_path / "raw_input"
    raw_dir.mkdir()
    patients_csv = raw_dir / "patients.csv"
    patients_csv.write_text(
        "patient_id,name,gender\nPAT-1,Koffi,M\nPAT-2,Akossiwa,F\nPAT-3,Komla,M\n",
        encoding="utf-8",
    )

    bronze_dir = tmp_path / "bronze_output"
    bronze_dir.mkdir()

    result_tables = convert_fn(raw_dir, bronze_dir)
    assert "patients" in result_tables, "Table 'patients' manquante dans le résultat de conversion"

    parquet_file = result_tables["patients"]
    assert parquet_file.exists(), f"Fichier Parquet non trouvé : {parquet_file}"

    df_bronze = pd.read_parquet(parquet_file)

    # Vérification de la présence des 4 colonnes obligatoires
    for col in MANDATORY_AUDIT_COLUMNS:
        assert col in df_bronze.columns, (
            f"Colonne technique d'audit obligatoire '{col}' absente du Parquet Bronze"
        )

    # Vérification des propriétés des métadonnées
    assert (df_bronze["source_file"] == "patients.csv").all() or (
        df_bronze["source_file"].str.endswith("patients.csv")
    ).all()
    # Indices de ligne 1-based : 1, 2, 3
    assert list(df_bronze["source_row"]) == [1, 2, 3]

    # Horodatages ISO 8601 valides
    for ts in df_bronze["ingested_at"]:
        assert ISO8601_TIMESTAMP_PATTERN.match(str(ts)), f"Horodatage invalide : {ts}"

    # Empreintes SHA-256 de ligne valides et uniques (puisque les lignes sont différentes)
    for h in df_bronze["content_hash"]:
        assert SHA256_HEX_PATTERN.match(str(h)), f"content_hash invalide : {h}"
    assert len(df_bronze["content_hash"].unique()) == 3


def test_bronze_strict_row_count_preservation(tmp_path: Path) -> None:
    """Règle d'or : le comptage de lignes Bronze est rigoureusement égal au comptage de lignes sources."""
    bronze_mod = _require_bronze_module()
    convert_fn = bronze_mod.convert_to_bronze

    raw_dir = tmp_path / "raw_counts"
    raw_dir.mkdir()
    excel_file = raw_dir / "health_center.xlsx"
    _create_sample_excel_workbook(excel_file)  # 3 patients, 2 encounters, 2 observations

    bronze_dir = tmp_path / "bronze_counts"
    bronze_dir.mkdir()

    tables = convert_fn(raw_dir, bronze_dir)

    # 3 patients
    df_pat = pd.read_parquet(tables["patients"])
    assert len(df_pat) == 3, f"Perte de lignes Bronze : attendu 3, obtenu {len(df_pat)}"

    # 2 encounters
    df_enc = pd.read_parquet(tables["encounters"])
    assert len(df_enc) == 2, f"Perte de lignes Bronze : attendu 2, obtenu {len(df_enc)}"

    # 2 observations
    df_obs = pd.read_parquet(tables["observations"])
    assert len(df_obs) == 2, f"Perte de lignes Bronze : attendu 2, obtenu {len(df_obs)}"


def test_bronze_parquet_pyarrow_types(tmp_path: Path) -> None:
    """Vérifie que les tables produites sont au format Apache Parquet typé et lisibles par PyArrow."""
    bronze_mod = _require_bronze_module()
    convert_fn = bronze_mod.convert_to_bronze

    raw_dir = tmp_path / "raw_parquet"
    raw_dir.mkdir()
    dhis2_file = raw_dir / "dhis2_values.json"
    _create_sample_dhis2_json(dhis2_file)  # 3 values

    bronze_dir = tmp_path / "bronze_parquet"
    bronze_dir.mkdir()

    tables = convert_fn(raw_dir, bronze_dir)
    assert "dhis2_data_values" in tables

    parquet_path = tables["dhis2_data_values"]
    table = pq.read_table(parquet_path)
    assert isinstance(table, pa.Table)
    assert table.num_rows == 3

    schema = table.schema
    for col in MANDATORY_AUDIT_COLUMNS:
        assert col in schema.names


def test_bronze_determinism_and_idempotence(tmp_path: Path) -> None:
    """Vérifie que deux exécutions consécutives produisent des tables Parquet avec un contenu identique."""
    bronze_mod = _require_bronze_module()
    convert_fn = bronze_mod.convert_to_bronze

    raw_dir = tmp_path / "raw_det"
    raw_dir.mkdir()
    csv_file = raw_dir / "patients.csv"
    csv_file.write_text("patient_id,name\nP-1,Koffi\nP-2,Akossiwa\n", encoding="utf-8")

    bronze_dir_1 = tmp_path / "bronze_run1"
    bronze_dir_1.mkdir()
    tables_1 = convert_fn(raw_dir, bronze_dir_1, batch_id="fixed-batch-001")
    df_1 = pd.read_parquet(tables_1["patients"])

    bronze_dir_2 = tmp_path / "bronze_run2"
    bronze_dir_2.mkdir()
    tables_2 = convert_fn(raw_dir, bronze_dir_2, batch_id="fixed-batch-001")
    df_2 = pd.read_parquet(tables_2["patients"])

    # Égalité stricte des DataFrames (hors horodatage si non fixé, mais content_hash identique)
    assert len(df_1) == len(df_2)
    assert list(df_1["content_hash"]) == list(df_2["content_hash"])
    assert list(df_1["patient_id"]) == list(df_2["patient_id"])


def test_bronze_validation_function(tmp_path: Path) -> None:
    """Vérifie la fonction validate_bronze_table pour auditer la conformité d'une table Parquet."""
    bronze_mod = _require_bronze_module()
    validate_fn = bronze_mod.validate_bronze_table

    # 1. Table valide avec les 4 colonnes techniques
    valid_parquet = tmp_path / "valid_table.parquet"
    valid_df = pd.DataFrame(
        {
            "id": ["1", "2"],
            "source_file": ["f.csv", "f.csv"],
            "source_row": [1, 2],
            "ingested_at": ["2026-11-05T20:15:00Z", "2026-11-05T20:15:00Z"],
            "content_hash": ["a" * 64, "b" * 64],
        }
    )
    valid_df.to_parquet(valid_parquet)

    assert validate_fn(valid_parquet) is True

    # 2. Table invalide (colonne content_hash manquante)
    invalid_parquet = tmp_path / "invalid_table.parquet"
    invalid_df = pd.DataFrame({"id": ["1", "2"], "source_file": ["f.csv", "f.csv"]})
    invalid_df.to_parquet(invalid_parquet)

    assert validate_fn(invalid_parquet) is False


# ==============================================================================
# Tier 5 : Quarantaine Résiliente & Règle d'Or de Non-Blocage (src.ingestion.quarantine)
# ==============================================================================


def test_quarantine_corrupt_binary_isolation(tmp_path: Path) -> None:
    """Vérifie l'isolement en quarantaine d'un fichier binaire corrompu avec motif codifié."""
    assert DATA_QUARANTINE_DIR.name == "quarantine"
    quar_mod = _require_quarantine_module()
    quarantine_fn = quar_mod.quarantine_file

    corrupt_file = tmp_path / "corrupted_archive.xlsx"
    corrupt_file.write_bytes(b"\x00\xff\xfe\x00_NOT_A_VALID_ZIP_OR_EXCEL_")

    quar_dir = tmp_path / "quarantine"
    quar_dir.mkdir()

    record = quarantine_fn(
        corrupt_file,
        quar_dir,
        reason="UNREADABLE_EXCEL_CORRUPT",
        error=ValueError("Fichier non décodable par openpyxl"),
    )

    assert record.source_file == "corrupted_archive.xlsx"
    assert record.quarantine_reason == "UNREADABLE_EXCEL_CORRUPT"
    assert "ValueError" in record.error_type or "Fichier non décodable" in record.error_details

    # Vérification de la présence dans data/quarantine/
    quarantined_files = list(quar_dir.glob("*corrupted_archive.xlsx*"))
    assert len(quarantined_files) >= 1, (
        "Le fichier corrompu doit être déplacé ou consigné dans la quarantaine"
    )


def test_quarantine_malformed_json_syntax(tmp_path: Path) -> None:
    """Vérifie l'isolement d'un fichier FHIR/DHIS2 JSON tronqué ou malformé."""
    quar_mod = _require_quarantine_module()
    quarantine_fn = quar_mod.quarantine_file

    bad_json_file = tmp_path / "broken_fhir.json"
    bad_json_file.write_text('{"resourceType": "Bundle", "entry": [', encoding="utf-8")

    quar_dir = tmp_path / "quarantine_json"
    quar_dir.mkdir()

    record = quarantine_fn(
        bad_json_file,
        quar_dir,
        reason="INVALID_JSON_SYNTAX",
        error=json.JSONDecodeError("Unterminated array", bad_json_file.read_text(), 34),
    )

    assert record.quarantine_reason == "INVALID_JSON_SYNTAX"
    assert "JSONDecodeError" in record.error_type


def test_quarantine_batch_non_blocking_golden_rule(tmp_path: Path) -> None:
    """RÈGLE D'OR DE RÉSILIENCE : Un fichier corrompu N'INTERROMPT JAMAIS le traitement du lot.

    Dans un lot comprenant 2 fichiers valides et 1 fichier corrompu :
    - Le fichier corrompu est dirigé vers data/quarantine/ avec sa fiche d'incident.
    - L'exécution du lot se poursuit sans exception bloquante.
    - Les 2 fichiers valides sont convertis en Bronze à 100% avec toutes leurs lignes.
    """
    engine_mod = _require_engine_module()
    engine_cls = getattr(engine_mod, "IngestionEngine", None)
    run_ingest_fn = getattr(engine_mod, "run_ingestion_pipeline", None)

    # Préparation du lot mixte
    sources_dir = tmp_path / "mixed_sources"
    sources_dir.mkdir()

    # Fichier valide 1 : patients.csv (2 lignes)
    valid_csv = sources_dir / "patients.csv"
    valid_csv.write_text("patient_id,name\nPAT-1,Koffi\nPAT-2,Akossiwa\n", encoding="utf-8")

    # Fichier corrompu 2 : garbage.xlsx (faux classeur, binaire invalide)
    corrupt_excel = sources_dir / "garbage.xlsx"
    corrupt_excel.write_bytes(b"RANDOM_CORRUPTED_BYTES_NOT_ZIP_HEADER")

    # Fichier valide 3 : dhis2.json (3 dataValues)
    valid_dhis2 = sources_dir / "dhis2.json"
    _create_sample_dhis2_json(valid_dhis2)

    raw_dir = tmp_path / "raw_resilient"
    bronze_dir = tmp_path / "bronze_resilient"
    quarantine_dir = tmp_path / "quarantine_resilient"

    raw_dir.mkdir()
    bronze_dir.mkdir()
    quarantine_dir.mkdir()

    # Exécution du moteur
    if engine_cls:
        engine = engine_cls(raw_dir=raw_dir, bronze_dir=bronze_dir, quarantine_dir=quarantine_dir)
        summary = engine.run([valid_csv, corrupt_excel, valid_dhis2])
    elif run_ingest_fn:
        summary = run_ingest_fn(
            sources=[valid_csv, corrupt_excel, valid_dhis2],
            raw_dir=raw_dir,
            bronze_dir=bronze_dir,
            quarantine_dir=quarantine_dir,
        )
    else:
        pytest.fail(
            "Ni IngestionEngine ni run_ingestion_pipeline trouvés dans src.ingestion.engine"
        )

    assert summary is not None

    # 1. Vérification que le lot ne s'est pas arrêté
    # 2. Le fichier corrompu doit être recensé en quarantaine
    quarantine_records = list(quarantine_dir.glob("*garbage.xlsx*")) + list(
        quarantine_dir.glob("*.json")
    )
    assert len(quarantine_records) >= 1, (
        "Le fichier corrompu doit être consigné dans quarantine_dir"
    )

    # 3. Les fichiers valides doivent être convertis en Bronze à 100%
    bronze_patients = bronze_dir / "patients.parquet"
    assert bronze_patients.exists(), (
        "Table 'patients.parquet' manquante malgré la présence d'un fichier valide"
    )
    df_pat = pd.read_parquet(bronze_patients)
    assert len(df_pat) == 2, (
        f"Les 2 patients valides doivent être tous présents, obtenu {len(df_pat)}"
    )

    bronze_dhis2 = bronze_dir / "dhis2_data_values.parquet"
    if not bronze_dhis2.exists():
        # Nommage alternatif possible : dhis2.parquet
        bronze_dhis2 = bronze_dir / "dhis2.parquet"
    assert bronze_dhis2.exists(), "Table DHIS2 manquante malgré la présence du fichier JSON valide"
    df_dhis2 = pd.read_parquet(bronze_dhis2)
    assert len(df_dhis2) == 3, (
        f"Les 3 valeurs DHIS2 doivent être toutes présentes, obtenu {len(df_dhis2)}"
    )


# ==============================================================================
# Tier 6 : Moteur d'Ingestion Global & Pipeline E2E (src.ingestion.engine)
# ==============================================================================


def test_engine_dry_run_mode(tmp_path: Path) -> None:
    """Vérifie que le mode --dry-run simule l'ingestion sans écrire dans raw/ ni bronze/."""
    engine_mod = _require_engine_module()
    engine_cls = getattr(engine_mod, "IngestionEngine", None)
    run_ingest_fn = getattr(engine_mod, "run_ingestion_pipeline", None)

    src_dir = tmp_path / "dry_run_sources"
    src_dir.mkdir()
    f1 = src_dir / "sample.csv"
    f1.write_text("a,b\n1,2\n", encoding="utf-8")

    raw_dir = tmp_path / "raw_dry"
    bronze_dir = tmp_path / "bronze_dry"
    quarantine_dir = tmp_path / "quarantine_dry"

    if engine_cls:
        engine = engine_cls(raw_dir=raw_dir, bronze_dir=bronze_dir, quarantine_dir=quarantine_dir)
        summary = engine.run([f1], dry_run=True)
    elif run_ingest_fn:
        summary = run_ingest_fn(
            sources=[f1],
            raw_dir=raw_dir,
            bronze_dir=bronze_dir,
            quarantine_dir=quarantine_dir,
            dry_run=True,
        )
    else:
        pytest.fail("Ni IngestionEngine ni run_ingestion_pipeline trouvés")

    assert summary is not None

    # Aucun fichier de données ne doit avoir été créé dans raw/ ou bronze/
    raw_files = [p for p in raw_dir.glob("*") if p.name != ".gitkeep"]
    bronze_files = [p for p in bronze_dir.glob("*") if p.name != ".gitkeep"]
    assert len(raw_files) == 0, (
        f"Mode dry-run : des fichiers ont été écrits dans raw/ : {raw_files}"
    )
    assert len(bronze_files) == 0, (
        f"Mode dry-run : des fichiers ont été écrits dans bronze/ : {bronze_files}"
    )


def test_engine_summary_metrics(tmp_path: Path) -> None:
    """Vérifie que le moteur produit un objet récapitulatif complet des métriques d'ingestion."""
    engine_mod = _require_engine_module()
    engine_cls = getattr(engine_mod, "IngestionEngine", None)
    run_ingest_fn = getattr(engine_mod, "run_ingestion_pipeline", None)

    src_dir = tmp_path / "metrics_sources"
    src_dir.mkdir()
    excel_path = _create_sample_excel_workbook(src_dir / "clinic.xlsx")

    raw_dir = tmp_path / "raw_metrics"
    bronze_dir = tmp_path / "bronze_metrics"
    quarantine_dir = tmp_path / "quar_metrics"

    if engine_cls:
        engine = engine_cls(raw_dir=raw_dir, bronze_dir=bronze_dir, quarantine_dir=quarantine_dir)
        summary = engine.run([excel_path])
    elif run_ingest_fn:
        summary = run_ingest_fn(
            sources=[excel_path],
            raw_dir=raw_dir,
            bronze_dir=bronze_dir,
            quarantine_dir=quarantine_dir,
        )
    else:
        pytest.fail("Moteur d'ingestion manquant")

    # Vérification de la présence des compteurs essentiels
    assert hasattr(summary, "raw_files_count") or hasattr(summary, "total_files")
    assert hasattr(summary, "bronze_tables_count") or hasattr(summary, "tables_converted")
    assert hasattr(summary, "quarantined_files_count") or hasattr(summary, "quarantined_count")
