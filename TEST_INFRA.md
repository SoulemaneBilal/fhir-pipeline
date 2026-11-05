# Test Infrastructure Specification — Étape 2 (Référentiels & Vocabulaires)

## 1. Test Philosophy

The test infrastructure for the Togo Health Data Pipeline (`fhir-pipeline`) adheres to the core engineering principles articulated in `AGENT.md`, `SYNTHESE_PROJET.md`, and architectural decisions `docs/journal/DECISIONS.md`:

1. **Opaque-Box Specification Verification**:
   Tests verify behavioral contracts, schema definitions, and domain invariants as specified in authoritative requirements (`ORIGINAL_REQUEST.md`, `PROJECT.md`, ADR D-08, ADR D-09, VAL-001, VAL-002), without coupling to ephemeral implementation details.

2. **Offline-First & Zero Network Dependencies**:
   Conforming to `AGENT.md` (l. 121-125), all tests execute in complete network isolation. No external HTTP requests, API calls to remote terminology servers (Athena/UMLS/WHO), or internet downloads are permitted during test execution.

3. **Strict Determinism**:
   Conforming to `AGENT.md` (l. 25-44), identifiers must be deterministic (UUID v5 derived from national namespaces and entity codes). Pseudo-random operations are seeded (`sample_seed = 42`). Tests must be 100% idempotent and order-independent.

4. **Lightweight Test Mocks (< 1 MB in Git)**:
   Conforming to ADR D-09, test datasets (notably `terminology/sample_vocabularies.parquet`) must remain strictly under 1,000,000 bytes (< 1 MB) when versioned in Git, preventing repository bloat while covering 100% of the priority pathology concepts.

5. **Host Environment Protection**:
   Tests must never alter, restart, or terminate pre-existing Docker containers running on the host system (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).

6. **Progressive Testability & Strict Mode**:
   During milestone execution, tests adapt gracefully to milestones in progress (reporting skipped status with explicit dependency identification if an artifact is not yet built), while providing a `STRICT_E2E=1` gate mode for final milestone acceptance (M5) where missing artifacts cause strict test failures.

---

## 2. Feature Inventory & Traceability Matrix

| Feature ID | Requirement | Domain / Target | Authoritative Source | Test Suite File | Test Tiers |
|---|---|---|---|---|---|
| **FEAT-GEO-01** | R1, ADR D-08 | 6 Health Regions & 44 Districts | `ORIGINAL_REQUEST.md`, ADR D-08 | `tests/test_geography.py` | Tier 1, Tier 3 |
| **FEAT-GEO-02** | R1 | 4-Level Facility Pyramid (CHU, CHR, Hospital, CMS/USP) | `SYNTHESE_PROJET.md`, `technique.md` | `tests/test_geography.py` | Tier 1, Tier 3 |
| **FEAT-GEO-03** | R1 | Deterministic UUID v5 & Uniqueness `(district, name)` | `AGENT.md`, `PROJECT.md` | `tests/test_geography.py` | Tier 2 |
| **FEAT-GEO-04** | R1 | Hierarchy Integrity & Zero Orphans | ADR D-08, VAL-001 | `tests/test_geography.py` | Tier 3 |
| **FEAT-GEO-05** | R1 | Facility Filtering & Query Performance | `PROJECT.md` | `tests/test_geography.py` | Tier 4 |
| **FEAT-URI-01** | R2 | National Canonical Base URI & SIDs | `docs/architecture_uri.md`, `PROJECT.md` | `tests/test_uris.py` | Tier 1 |
| **FEAT-URI-02** | R2 | Local CodeSystems & Standard Vocabularies | `docs/architecture_uri.md`, `PROJECT.md` | `tests/test_uris.py` | Tier 1, Tier 2 |
| **FEAT-URI-03** | R2 | Profile StructureDefinitions & Documentation Match | `docs/architecture_uri.md` | `tests/test_uris.py` | Tier 3 |
| **FEAT-VOC-01** | R3, ADR D-09 | Mock Parquet Schema & Size (< 1 MB) | ADR D-09, `AGENT.md` | `tests/test_terminology.py` | Tier 1, Tier 2 |
| **FEAT-VOC-02** | R3, VAL-002 | 9 Priority Pathologies Coverage | `docs/journal/A_VALIDER.md`, `PROJECT.md` | `tests/test_terminology.py` | Tier 1 |
| **FEAT-VOC-03** | R3 | 4 Target Vocabularies (ICD-10, SNOMED, LOINC, ATC) | `technique.md`, `PROJECT.md` | `tests/test_terminology.py` | Tier 1, Tier 3 |
| **FEAT-VOC-04** | R3 | Vital Signs LOINC & Essential Drugs ATC Mappings | `SYNTHESE_PROJET.md`, `PROJECT.md` | `tests/test_terminology.py` | Tier 3 |
| **FEAT-VOC-05** | R3 | Offline Concept Lookup Performance | `AGENT.md` | `tests/test_terminology.py` | Tier 4 |
| **FEAT-CLI-01** | R4 | Reference Subcommands Registration & Help | `PROJECT.md`, `src/cli.py` | `tests/test_cli_etape2.py` | Tier 1 |
| **FEAT-CLI-02** | R4 | Terminology Subcommands Registration & Help | `PROJECT.md`, `src/cli.py` | `tests/test_cli_etape2.py` | Tier 1 |
| **FEAT-CLI-03** | R4 | Execution with Reference Datasets Present | `PROJECT.md` | `tests/test_cli_etape2.py` | Tier 2, Tier 4 |
| **FEAT-REG-01** | R5 | Non-Regression on Pre-Existing 65 Tests | `ORIGINAL_REQUEST.md` | `tests/test_*.py` | All |

---

## 3. Test Architecture (Tiers 1 to 4)

The test suite is structured into four progressive tiers:

### Tier 1: Feature Coverage (Schema & Mandatory Entities)
- **Objective**: Verify that datasets and modules exist, follow the prescribed schema, and contain all mandatory reference entities.
- **Geography**: Confirms presence of columns (`facility_id`, `facility_code`, `name`, `normalized_name`, `category`, `pyramid_level`, `district_code`, `district_name`, `region_code`, `region_name`, `country_code`, `country_name`), exactly 6 health regions, exactly 44 health districts, and all 4 facility pyramid levels.
- **Terminology**: Confirms presence of standard columns (`concept_id`, `concept_name`, `domain_id`, `vocabulary_id`, `concept_code`, `pathology_group`), all 9 priority pathologies (Malaria, ARI, Diarrhea, HIV, TB, HTA, Diabetes, SMI, Malnutrition), PEV vaccines, and all 4 vocabularies (ICD-10, SNOMED CT, LOINC, ATC).
- **URIs**: Confirms presence and syntactic validity of canonical base URIs, SIDs, CodeSystems, and StructureDefinitions.
- **CLI**: Confirms subcommands are registered in Typer hierarchy and produce French descriptions via `--help`.

### Tier 2: Boundary & Corner Cases
- **Objective**: Enforce strict invariants, null safety, boundary sizes, and format specifications.
- **Geography**: Validates that all `facility_id`s conform to the RFC 4122 UUID v5 specification (`^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`). Verifies zero nulls across mandatory columns. Enforces strict uniqueness of `(district_code, normalized_name)` and verifies normalization properties (lowercase, no diacritics, trimmed whitespace).
- **Terminology**: Verifies file size of `sample_vocabularies.parquet` is strictly `< 1,000,000` bytes (ADR D-09). Checks for non-empty concept codes, valid domain assignments, and standard concept flags.
- **URIs**: Checks for trailing slashes, scheme validation (HTTP/HTTPS), and namespace segregation.

### Tier 3: Cross-Feature Integrity & Domain Mappings
- **Objective**: Verify relationships between entities across modules, parent-child links, and clinical mappings.
- **Geography**: Asserts that every facility's `district_code` maps to an official district belonging to the facility's `region_code`. Ensures no orphan districts exist (every district has valid facilities and maps to its exact region). Confirms `pyramid_level` aligns strictly with `category` (Level 4 ↔ CHU, Level 3 ↔ CHR, Level 2 ↔ Hospital, Level 1 ↔ CMS/USP).
- **Terminology**: Validates specific clinical mappings for priority pathologies:
  - Vital signs LOINC codes: Blood pressure systolic (`8480-6`), diastolic (`8462-4`), glycemia (`1558-6` / `2345-7`), body temperature (`8310-5`), body weight (`29463-7`), MUAC (`89270-3` / `56072-2`).
  - Essential medications ATC codes: ACT antimalarial (`P01BF01`), ARV TLD (`J05AR13`), TB RHZE (`J04AM06` / `J04AK02`), SRO (`A07CA`), Amlodipine (`C08CA01`), Metformin (`A10BA02`).
- **URIs vs Documentation**: Verifies programmatic URIs match specification in `docs/architecture_uri.md`.

### Tier 4: Workload, Performance & Adversarial Validation
- **Objective**: Validate query response times, offline simulated lookup performance, and robustness against invalid inputs.
- **Geography**: Benchmarks filtering facilities by region, district, and level (< 50ms). Adversarial test on validator functions passing corrupt/duplicate records to ensure proper rejection.
- **Terminology**: Tests sub-millisecond offline dictionary lookup by concept code and pathology group.
- **CLI**: Tests command execution against generated datasets with exit code 0, and validates failure handling on invalid arguments.

---

## 4. Directory Layout

```
fhir-pipeline/
├── data/
│   └── reference/
│       └── togo_health_geography.parquet   # Frozen reference table (M2)
├── terminology/
│   └── sample_vocabularies.parquet         # Mock vocabularies < 1 MB (M3)
├── docs/
│   ├── architecture_uri.md                 # URI Architecture specification (M1)
│   └── journal/
│       ├── DECISIONS.md                    # ADR D-08, D-09
│       └── A_VALIDER.md                    # VAL-001, VAL-002
├── src/
│   ├── cli.py                              # Typer CLI entrypoint
│   └── terminology/
│       ├── __init__.py
│       ├── uris.py                         # Canonical URI constants (M1)
│       ├── geography.py                    # Geography model & validators (M2)
│       └── pathologies.py                  # Clinical catalog & validators (M3)
├── tests/
│   ├── conftest.py                         # Shared fixtures
│   ├── test_socle.py                       # Étape 0 baseline tests
│   ├── test_docker_compose.py              # Étape 1 container orchestration tests
│   ├── test_cli.py                         # Étape 1 CLI tests
│   ├── test_uris.py                        # Étape 2 URI architecture tests
│   ├── test_geography.py                   # Étape 2 Geography & Facility tests
│   ├── test_terminology.py                 # Étape 2 Pathologies & Mock tests
│   └── test_cli_etape2.py                  # Étape 2 CLI commands tests
├── TEST_INFRA.md                           # This document
└── TEST_READY.md                           # Test suite readiness & execution summary
```

---

## 5. Execution Commands & Quality Gates

### Running the Full Test Suite
```bash
uv run pytest -v
```

### Running Étape 2 Specific Test Suites
```bash
uv run pytest tests/test_uris.py tests/test_geography.py tests/test_terminology.py tests/test_cli_etape2.py -v
```

### Running in Strict Acceptance Gate Mode (Milestone M5)
```bash
STRICT_E2E=1 uv run pytest -v
```

### Code Quality & Linting
```bash
uv run ruff check .
uv run ruff format --check .
```

### Pass Criteria
- **Pass rate**: 100% of non-skipped tests pass.
- **Ruff linter**: 0 errors, 0 warnings.
- **Host Docker safety**: 0 host containers stopped or restarted.
- **Network calls**: 0 outbound network requests during testing.
