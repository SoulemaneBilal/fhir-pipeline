# Test Infrastructure Specification — Étape 5 (Ingestion Raw, Bronze & Quarantaine)

## 1. Test Philosophy

The test infrastructure for the Togo Health Data Pipeline (`fhir-pipeline`) adheres to the core engineering principles articulated in `AGENT.md`, `SYNTHESE_PROJET.md`, and architectural decisions `docs/journal/DECISIONS.md`:

1. **Opaque-Box Specification Verification**:
   Tests verify behavioral contracts, schema definitions, clinical rules, and domain invariants as specified in authoritative requirements (`ORIGINAL_REQUEST.md`, `SCOPE.md`, ADR D-04, ADR D-08, ADR D-09, VAL-001, VAL-002, VAL-003), without coupling to ephemeral implementation details.

2. **Offline-First & Zero Network Dependencies**:
   Conforming to `AGENT.md` (§ 2.4, l. 121-125), all tests execute in complete network isolation. Outbound network requests to external terminology servers, live DHIS2 instances (`play.dhis2.org/demo`), or package repositories are forbidden during test runs.

3. **Strict Mathematical Determinism (Bit-for-Bit Parquet)**:
   Conforming to `AGENT.md` (l. 25-44) and ADR D-04, all generation, degradation, and ingestion processes must be strictly reproducible. Two consecutive runs with the same inputs must produce bit-for-bit identical Apache Parquet files and alteration/ingestion manifests (matching SHA-256 cryptographic checksums).

4. **100% Real-World Reference Adherence & Traceability**:
   Every record ingested into the Bronze layer must retain the 4 mandatory audit metadata fields (`source_file`, `source_row`, `ingested_at`, `content_hash`), establishing an unbreakable chain of custody from raw source to analytics.

5. **Host Environment Protection**:
   Tests must never alter, restart, or terminate pre-existing Docker containers running on the host system (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).

6. **Progressive Testability & Strict Mode Gate**:
   Tests provide a `STRICT_E2E=1` gate mode for milestone acceptance where missing artifacts or broken contracts trigger a strict failure.

---

## 2. Feature Inventory & Traceability Matrix (Étape 5)

| Feature ID | Requirement | Domain / Target | Authoritative Source | Test Suite File | Test Tiers |
|---|---|---|---|---|---|
| **FEAT-ING-01** | R1, AGENT.md #1 | Bit-for-Bit Raw Ingestion & SHA-256 | `technique.md:68` | `tests/test_ingestion.py` | Tier 3 |
| **FEAT-ING-02** | R2 | Multi-Format Reader: Multi-Sheet Excel | `technique.md:68` | `tests/test_ingestion.py` | Tier 2 |
| **FEAT-ING-03** | R2 | Multi-Format Reader: Auto-Detect CSV (Delim/Enc) | `technique.md:68` | `tests/test_ingestion.py` | Tier 2 |
| **FEAT-ING-04** | R2 | Multi-Format Reader: FHIR R4 JSON Bundles | `technique.md:68` | `tests/test_ingestion.py` | Tier 2 |
| **FEAT-ING-05** | R2 | Multi-Format Reader: DHIS2 dataValueSets | `technique.md:68` | `tests/test_ingestion.py` | Tier 2 |
| **FEAT-ING-06** | R3, AGENT.md #2 | 4 Mandatory Audit Columns in Bronze | `AGENT.md:29-30` | `tests/test_ingestion.py` | Tier 4 |
| **FEAT-ING-07** | R3 | Row Count Equality (Bronze == Source Valid) | `technique.md:69` | `tests/test_ingestion.py` | Tier 4 |
| **FEAT-ING-08** | R4, AGENT.md #6 | Non-Blocking Quarantine for Corrupt Files | `technique.md:68-69` | `tests/test_ingestion.py` | Tier 5 |
| **FEAT-ING-09** | R5 | Ingestion Idempotence & Determinism | `technique.md:69` | `tests/test_ingestion.py` | Tier 3 & 4 |
| **FEAT-ING-10** | R6 | End-to-End Ingestion Pipeline & Dry-Run | `SCOPE.md:47` | `tests/test_ingestion.py` | Tier 6 |
| **FEAT-ING-11** | R7 | CLI Commands (`raw ingest`, `raw status`) | `src/cli.py:67` | `tests/test_cli_ingestion.py` | CLI Tests |
| **FEAT-ING-12** | R7 | CLI Commands (`bronze convert`, `validate`) | `src/cli.py:126` | `tests/test_cli_ingestion.py` | CLI Tests |

---

## 3. Test Tier Architecture (Étape 5)

### Tier 1: Schemas & Data Contracts
- **Objective**: Validate Pydantic v2 models and PyArrow schemas (`SourceFormat`, `RawFileRecord`, `RawManifest`, `QuarantineRecord`, `AUDIT_COLUMNS`, `BRONZE_AUDIT_SCHEMA`, `IngestionResult`).

### Tier 2: Multi-Format Source Readers
- **Objective**: Validate format-specific readers:
  - Excel (`read_excel_source`): multi-sheet `.xlsx` / `.xls` extraction with sheet filtering.
  - CSV (`read_csv_source`): auto-detection of delimiters (`,`, `;`, `\t`, `|`) and encodings (`utf-8`, `latin-1`, `cp1252`) preserving Togolese diacritics.
  - FHIR (`read_fhir_source`): JSON Bundle parsing into typed DataFrames by `resourceType`.
  - DHIS2 (`read_dhis2_source`): `dataValueSets` JSON/Parquet parsing into normalized tabular formats.
  - Sniffer (`detect_source_type`): automatic format detection from filename and content inspection.

### Tier 3: Raw Layer & Cryptographic Manifest
- **Objective**: Validate immutable bit-for-bit file copy to `data/raw/`, 64KB block SHA-256 calculation, `raw_manifest.json` generation, idempotence, and byte-level corruption detection (`verify_raw_integrity`).

### Tier 4: Bronze Layer Parquet Conversion
- **Objective**: Validate conversion to Apache Parquet SNAPPY with the 4 mandatory audit columns (`source_file`, `source_row` 1-based, `ingested_at`, `content_hash`). Enforces strict row count equality (`len(bronze) == len(source_valid)`).

### Tier 5: Resilient Quarantine & Golden Non-Blocking Rule
- **Objective**: Validate automatic isolation of corrupted files (truncated binaries, broken JSON syntax) into `data/quarantine/` with codified incident metadata JSON (`quarantine_reason`, `error_type`, `error_details`). Asserts that quarantined files NEVER halt batch processing and valid files are 100% converted to Bronze.

### Tier 6: End-to-End Ingestion Engine
- **Objective**: Validate `IngestionEngine` and `run_ingestion_pipeline`, including `--dry-run` simulation without disk side-effects.

---

## 4. Directory Layout

```
fhir-pipeline/
├── data/
│   ├── raw/                                    # Immutable raw sources (read-only, SHA-256 tracked)
│   ├── bronze/                                 # Typed Bronze Parquet tables with 4 audit metadata
│   ├── quarantine/                             # Isolated corrupted files + incident JSON records
│   ├── reference/                              # National geographic and terminology references
│   ├── truth/                                  # Ground Truth cohort (Étape 3)
│   └── degraded/                               # Degraded datasets & alteration logs (Étape 4)
├── src/
│   ├── cli.py                                  # Typer CLI entrypoint
│   └── ingestion/
│       ├── __init__.py                         # Public API exports
│       ├── schemas.py                          # Pydantic models & PyArrow schemas
│       ├── readers.py                          # Specialized multi-format source readers
│       ├── raw.py                              # Raw layer ingestion & SHA-256 integrity
│       ├── bronze.py                           # Bronze layer conversion & audit columns
│       ├── quarantine.py                       # Resilient quarantine manager
│       └── engine.py                           # IngestionEngine & run_ingestion_pipeline
├── tests/
│   ├── test_ingestion.py                       # Étape 5 ingestion test suite (Tiers 1-6)
│   └── test_cli_ingestion.py                   # Étape 5 CLI Typer test suite
├── TEST_INFRA.md                               # This document
└── TEST_READY.md                               # Test suite readiness & execution summary
```

---

## 5. Execution Commands & Quality Gates

### Running All Étape 5 Tests
```bash
STRICT_E2E=1 uv run pytest tests/test_ingestion.py tests/test_cli_ingestion.py -v
```

### Running Full Project Test Suite
```bash
uv run pytest -v
```

### Code Quality & Linting
```bash
uv run ruff check .
uv run ruff format --check .
```

### Acceptance Gate Criteria
- **Pass rate**: 100% of executed tests pass (278/278 tests).
- **Ruff linter**: 0 errors, 0 warnings.
- **Host Docker safety**: 0 host containers stopped or restarted (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).
- **Network isolation**: 0 external network requests during test runs.
