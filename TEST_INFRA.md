# Test Infrastructure Specification — Étape 6 (Profilage Qualité Initial & Rapport Avant)

## 1. Test Philosophy

The test infrastructure for the Togo Health Data Pipeline (`fhir-pipeline`) adheres to the core engineering principles articulated in `AGENT.md`, `SYNTHESE_PROJET.md`, and architectural decisions `docs/journal/DECISIONS.md`:

1. **Opaque-Box Specification Verification**:
   Tests verify behavioral contracts, schema definitions, clinical rules, and domain invariants as specified in authoritative requirements (`ORIGINAL_REQUEST.md`, `SCOPE.md`, ADR D-04, ADR D-08, ADR D-09, VAL-001, VAL-002, VAL-003), without coupling to ephemeral implementation details.

2. **Offline-First & Zero Network Dependencies**:
   Conforming to `AGENT.md` (§ 2.4, l. 121-125), all tests execute in complete network isolation. Outbound network requests to external terminology servers, live DHIS2 instances (`play.dhis2.org/demo`), or package repositories are forbidden during test runs.

3. **Strict Mathematical Determinism (Bit-for-Bit Parquet & Reports)**:
   Conforming to `AGENT.md` (l. 25-44) and ADR D-04, all profiling evaluations and report calculations must be strictly reproducible. Repeated executions on the same Bronze dataset produce identical metrics, dimension scores, and report outputs.

4. **100% Real-World Reference Adherence & Traceability**:
   Profilers strictly evaluate clinical data against frozen authoritative tables:
   - Codes verified against `terminology/sample_vocabularies.parquet` (CIM-10, LOINC, ATC, SNOMED).
   - Facilities and administrative boundaries verified against `data/reference/togo_health_geography.parquet`.
   - Audit columns (`source_file`, `source_row`, `ingested_at`, `content_hash`) are strictly excluded from business data quality calculations (AGENT.md #2).

5. **Host Environment Protection**:
   Tests must never alter, restart, or terminate pre-existing Docker containers running on the host system (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).

6. **Progressive Testability & Strict Mode Gate**:
   Tests provide a `STRICT_E2E=1` gate mode for milestone acceptance where missing artifacts or broken contracts trigger a strict failure.

---

## 2. Feature Inventory & Traceability Matrix (Étape 6)

| Feature ID | Requirement | Domain / Target | Authoritative Source | Test Suite File | Test Tiers |
|---|---|---|---|---|---|
| **FEAT-PRF-01** | R1, ISO 25012 | 6 Normative Quality Dimensions (Schemas & Models) | `technique.md:73` | `tests/test_profiling.py` | Tier 1 |
| **FEAT-PRF-02** | R1 | Evaluator: Completeness (Nulls, Sentinels, Empty) | `technique.md:73` | `tests/test_profiling.py` | Tier 2 |
| **FEAT-PRF-03** | R1 | Evaluator: Accuracy (Non-ISO Dates, Approx Ages, Mojibake) | `technique.md:73` | `tests/test_profiling.py` | Tier 2 |
| **FEAT-PRF-04** | R1 | Evaluator: Consistency (Male Pregnancy, Temporal Order) | `technique.md:73` | `tests/test_profiling.py` | Tier 2 |
| **FEAT-PRF-05** | R1 | Evaluator: Uniqueness (Primary Keys, Splink Quasi-Duplicates) | `technique.md:73` | `tests/test_profiling.py` | Tier 2 |
| **FEAT-PRF-06** | R1 | Evaluator: Validity (CIM-10, LOINC, ATC, Geography, UCUM) | `technique.md:73` | `tests/test_profiling.py` | Tier 2 |
| **FEAT-PRF-07** | R1 | Evaluator: Timeliness (Future Dates, Dates < 1900) | `technique.md:73` | `tests/test_profiling.py` | Tier 2 |
| **FEAT-PRF-08** | R2 | Global Engine: QualityProfiler (Table & Dataset) | `SCOPE.md:35` | `tests/test_profiling.py` | Tier 3 |
| **FEAT-PRF-09** | R3 | Confrontation with Alterations Log (Recall >= 80%) | `technique.md:74` | `tests/test_profiling.py` | Tier 4 |
| **FEAT-PRF-10** | R4 | Baseline Quality Report Generation (Markdown & JSON) | `technique.md:73` | `tests/test_profiling.py` | Tier 5 |
| **FEAT-PRF-11** | R5 | CLI Commands (`bronze profile`, Rich UI) | `src/cli.py:307` | `tests/test_cli_profiling.py` | CLI Tests |

---

## 3. Test Tier Architecture (Étape 6)

### Tier 1: Schemas & Data Contracts
- **Objective**: Validate Pydantic v2 models and StrEnum for quality dimensions (`QualityDimension`, `ColumnMetric`, `DimensionScore`, `TableQualitySummary`, `RecallMetric`, `ProfilingReport`).

### Tier 2: 6 Dimension Evaluators
- **Objective**: Validate isolated dimension evaluators:
  - Completeness: detection of nulls, empty strings, and hospital sentinel codes (`-1`, `999`, `NA`, `ND`, `INCONNU`).
  - Accuracy: detection of composite date formats, textual approximate ages, UTF-8 Mojibake, and French comma decimal separators.
  - Consistency: detection of male pregnancies (codes Z34/Z35/O in males), temporal inversions, and health pyramid discrepancies.
  - Uniqueness: detection of primary key collisions and multi-facility suspected patient duplicates.
  - Validity: validation against reference terminologies, geographic boundaries, and UCUM units.
  - Timeliness: detection of future event dates and historical anomalies (< 1900).

### Tier 3: Global Quality Profiler Engine
- **Objective**: Validate dataset-wide profiling orchestration across all Bronze tables (`patients`, `encounters`, `conditions`, `observations`, `prescriptions`, `immunizations`, `dhis2_data_values`). Asserts deterministic scoring, empty-table resilience, and audit-column exclusion.

### Tier 4: Ground Truth Answer Key Confrontation & Recall
- **Objective**: Validate detection recall ($TP / (TP + FN)$) against `data/degraded/alterations_log.parquet`. Enforces global recall threshold $\ge 80.0\%$ (empirically measured at **99.9%**).

### Tier 5: Baseline Quality Report Generation
- **Objective**: Validate automated generation of `profiling_bronze.md` and `profiling_bronze.json`, with executive summary, 6D score matrix, table breakdown, and actionable silver cleaning recommendations.

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
├── docs/reports/
│   ├── profiling_bronze.md                     # Baseline Quality Report (Markdown)
│   └── profiling_bronze.json                   # Baseline Quality Report (JSON)
├── src/
│   ├── cli.py                                  # Typer CLI entrypoint
│   └── profiling/
│       ├── __init__.py                         # Public API exports
│       ├── schemas.py                          # Pydantic models & quality schemas
│       ├── dimensions.py                       # 6 normative dimension evaluators
│       ├── engine.py                           # QualityProfiler & recall comparison
│       └── reporter.py                         # Markdown and JSON report generators
├── tests/
│   ├── test_profiling.py                       # Étape 6 profiling test suite (Tiers 1-5)
│   └── test_cli_profiling.py                   # Étape 6 CLI Typer test suite
├── TEST_INFRA.md                               # This document
└── TEST_READY.md                               # Test suite readiness & execution summary
```

---

## 5. Execution Commands & Quality Gates

### Running All Étape 6 Tests
```bash
STRICT_E2E=1 uv run pytest tests/test_profiling.py tests/test_cli_profiling.py -v
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
- **Pass rate**: 100% of executed tests pass (335/335 tests).
- **Ruff linter**: 0 errors, 0 warnings.
- **Host Docker safety**: 0 host containers stopped or restarted (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).
- **Detection Recall**: Global recall $\ge 80\%$ on `alterations_log.parquet`.
