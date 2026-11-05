# Test Infrastructure Specification — Étape 3 (Génération Vérité Terrain & Agrégats DHIS2)

## 1. Test Philosophy

The test infrastructure for the Togo Health Data Pipeline (`fhir-pipeline`) adheres to the core engineering principles articulated in `AGENT.md`, `SYNTHESE_PROJET.md`, and architectural decisions `docs/journal/DECISIONS.md`:

1. **Opaque-Box Specification Verification**:
   Tests verify behavioral contracts, schema definitions, clinical rules, and domain invariants as specified in authoritative requirements (`ORIGINAL_REQUEST.md`, `SCOPE.md`, ADR D-04, ADR D-08, ADR D-09, VAL-001, VAL-002, VAL-003), without coupling to ephemeral implementation details.

2. **Offline-First & Zero Network Dependencies**:
   Conforming to `AGENT.md` (§ 2.4, l. 121-125), all tests execute in complete network isolation. Outbound network requests to external terminology servers, live DHIS2 instances (`play.dhis2.org/demo`), or package repositories are forbidden during test runs. The DHIS2 test engine validates automatic fallback to local deterministic synthetic aggregates.

3. **Strict Mathematical Determinism (Bit-for-Bit Parquet)**:
   Conforming to `AGENT.md` (l. 25-44) and ADR D-04, all generation processes must be strictly reproducible. Two consecutive runs with the same pseudo-random seed (`--seed 42`) must produce bit-for-bit identical Apache Parquet files (matching SHA-256 cryptographic checksums and identical DataFrames). PRNG isolation (`random.Random(seed)`) prevents global state leakage.

4. **100% Real-World Reference Adherence**:
   Every entity generated in the synthetic cohort must strictly reference the authoritative frozen tables:
   - 100% of healthcare facilities, district codes, and region codes match `data/reference/togo_health_geography.parquet`.
   - 100% of diagnostic (ICD-10), concept (SNOMED CT), observation (LOINC), and medication/vaccine (ATC) codes match `terminology/sample_vocabularies.parquet`.

5. **Host Environment Protection**:
   Tests must never alter, restart, or terminate pre-existing Docker containers running on the host system (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).

6. **Progressive Testability & Strict Mode Gate**:
   During milestone implementation, tests adapt gracefully to milestones in progress (reporting skipped status with explicit milestone identification if an artifact is not yet built), while providing a `STRICT_E2E=1` gate mode for milestone acceptance where any missing artifact or broken requirement triggers a strict test failure.

---

## 2. Feature Inventory & Traceability Matrix

| Feature ID | Requirement | Domain / Target | Authoritative Source | Test Suite File | Test Tiers |
|---|---|---|---|---|---|
| **FEAT-GEN-01** | R1, ADR D-04 | 6 Clinical Parquet Files Generation (`data/truth/`) | `ORIGINAL_REQUEST.md:179` | `tests/test_generation.py` | Tier 1 |
| **FEAT-GEN-02** | R2 | DHIS2 Monthly Aggregates (JSON & Parquet) | `ORIGINAL_REQUEST.md:181` | `tests/test_generation.py` | Tier 1 |
| **FEAT-GEN-03** | R1, AGENT.md | RFC 4122 UUID v5 Non-Null Primary Keys | `AGENT.md:29` | `tests/test_generation.py` | Tier 1 |
| **FEAT-GEN-04** | R1 | Strict Referential Integrity (Foreign Keys, 0 Orphelins) | `SCOPE.md:25` | `tests/test_generation.py` | Tier 1 |
| **FEAT-GEN-05** | R1 | Strict Typed PyArrow Schemas & Required Columns | `SCOPE.md:25` | `tests/test_generation.py` | Tier 1 |
| **FEAT-GEN-06** | R1 | Cohort Boundary Sizing (count=1, count=50, count<=0 rejection) | `ORIGINAL_REQUEST.md:175` | `tests/test_generation.py` | Tier 2 |
| **FEAT-GEN-07** | R2 | DHIS2 Resilient Offline Fallback (Invalid URL Handling) | `ORIGINAL_REQUEST.md:184` | `tests/test_generation.py` | Tier 2 |
| **FEAT-GEN-08** | R1 | Clinical Integrity: No Male Pregnancy (Z34, O80, O82, SMI) | `SYNTHESE_PROJET.md:477` | `tests/test_generation.py` | Tier 2 |
| **FEAT-GEN-09** | R1 | Clinical Integrity: Pediatric PEV Vaccines Only (< 5 years) | `ORIGINAL_REQUEST.md:177` | `tests/test_generation.py` | Tier 2 |
| **FEAT-GEN-10** | R1 | Clinical Integrity: Adult Chronic Conditions (HTA, Diabetes) | `SCOPE.md:28` | `tests/test_generation.py` | Tier 2 |
| **FEAT-GEN-11** | R1, VAL-003 | Approximate Age Rule (July 1st `-07-01`, `approximate-year`) | `docs/journal/A_VALIDER.md` | `tests/test_generation.py` | Tier 2 |
| **FEAT-GEN-12** | R1, R4 | Strict Bit-for-bit Determinism (SHA-256 Identical at Seed 42) | `ORIGINAL_REQUEST.md:195` | `tests/test_generation.py` | Tier 3 |
| **FEAT-GEN-13** | R1, R4 | Pseudo-Random Divergence (Seed 42 vs Seed 43) | `AGENT.md:32` | `tests/test_generation.py` | Tier 3 |
| **FEAT-GEN-14** | R2, R4 | DHIS2 Aggregate Determinism (Matching SHA-256) | `SCOPE.md:34` | `tests/test_generation.py` | Tier 3 |
| **FEAT-GEN-15** | R1, R4 | 100% Geography Reference Adherence (`togo_health_geography`) | ADR D-08, R4 | `tests/test_generation.py` | Tier 4 |
| **FEAT-GEN-16** | R1, R4 | 100% Terminology Adherence (`sample_vocabularies.parquet`) | ADR D-09, VAL-002 | `tests/test_generation.py` | Tier 4 |
| **FEAT-GEN-17** | R1 | Healthcare Pyramid Distribution (~72% L1) & Referral Tracking | ADR D-08, `technique.md` | `tests/test_generation.py` | Tier 4 |
| **FEAT-CLI-01** | R3 | CLI `generation` Group & Subcommands French Help | `ORIGINAL_REQUEST.md:186` | `tests/test_cli_generation.py` | Tier 1 |
| **FEAT-CLI-02** | R3 | CLI `generation run` Execution & Rich Summary Table | `ORIGINAL_REQUEST.md:188` | `tests/test_cli_generation.py` | Tier 2 |
| **FEAT-CLI-03** | R3 | CLI `generation dhis2-demo` Execution & Offline Fallback | `ORIGINAL_REQUEST.md:189` | `tests/test_cli_generation.py` | Tier 2 |
| **FEAT-CLI-04** | R3 | CLI Invalid Arguments Handling (Count <= 0, Unknown Options) | `ORIGINAL_REQUEST.md:190` | `tests/test_cli_generation.py` | Tier 2 |

---

## 3. Test Architecture (Tiers 1 to 4)

### Tier 1: Feature Coverage (Core Data & Schemas)
- **Objective**: Verify that generator functions and outputs conform to schema specifications without null primary keys or orphaned relationships.
- **Clinical Parquet Outputs**: Confirms generation of `patients.parquet`, `encounters.parquet`, `conditions.parquet`, `observations.parquet`, `prescriptions.parquet`, and `immunizations.parquet` in target output directory.
- **DHIS2 Outputs**: Confirms generation of `dhis2_data_values.json` (`dataValueSets` format) and `dhis2_data_values.parquet` with identical row counts.
- **Primary Key Integrity**: Verifies 100% of primary keys are non-null, unique, and valid RFC 4122 UUID v5 strings.
- **Referential Integrity**: Verifies strict foreign key relationships across all 6 clinical tables with zero orphan records.
- **Schema & Types**: Validates column presence and types across all entities.

### Tier 2: Boundary & Corner Cases (Clinical & Resilience Rules)
- **Cohort Boundary Sizes**: Confirms `--count 1` generates a valid minimal cohort without zero-division exceptions. Asserts `--count 0` or negative counts raise `ValueError`.
- **DHIS2 Offline Fallback**: Injects unreachable URL (`http://invalid-dhis2-test-url.local`) and validates graceful fallback to synthetic monthly aggregates without crashing or raising unhandled network exceptions.
- **Clinical Sex Invariant**: Formally checks that NO male patient (`gender == 'male'`) is assigned pregnancy, antenatal, or delivery diagnoses (ICD-10 `Z34`, `O80`, `O82`, or any chapter `O` code; pathology group `SMI`).
- **Pediatric Immunization Invariant**: Formally checks that all pediatric PEV vaccines (BCG, Polio, Pentavalent, PCV13, Rota, RR, VAA) are administered strictly to children aged under 5 years.
- **Chronic Conditions Invariant**: Asserts that adult chronic conditions (Hypertension `I10` and Type 2 Diabetes `E11.9`) are absent in infants (< 5 years) and concentrated in adults.
- **VAL-003 Compliance**: Formally asserts that 100% of patients with `estimated_age_flag = True` have a birth date ending on July 1st (`-07-01`) and `age_precision` set to `'approximate-year'`.

### Tier 3: Strict Determinism & Mathematical Reproducibility
- **Binary Bit-for-Bit Reproducibility**: Executes two consecutive generations with identical parameters (`seed=42`, `count=50`) into separate directories. Compares binary SHA-256 checksums across all 6 Parquet files to guarantee bit-for-bit identity, and validates DataFrame equality (`pd.testing.assert_frame_equal`).
- **Seed Divergence**: Confirms that different seeds (`seed=42` vs `seed=43`) produce non-identical datasets and different SHA-256 hashes.
- **DHIS2 Determinism**: Confirms that two consecutive runs of the DHIS2 offline aggregate generator with identical seed produce identical SHA-256 hashes.

### Tier 4: Real-World & 100% Reference Adherence
- **Geography Adherence (100%)**: Asserts 100% of `facility_id`, `district_code`, and `region_code` in `encounters.parquet` exist in `data/reference/togo_health_geography.parquet`.
- **Terminology Adherence (100%)**: Asserts 100% of `icd10_code`, `snomed_code`, `loinc_code`, and `atc_code` in `conditions`, `observations`, `prescriptions`, and `immunizations` exist in `terminology/sample_vocabularies.parquet`.
- **Healthcare Pyramid Realism**: Verifies encounter distribution mirrors the Togolese health system pyramid:
  - Level 1 (CMS / USP): 60% to 85% of total encounters.
  - Level 2 (CHP / District Hospital): 8% to 30% of total encounters.
  - Level 3 & 4 (CHR / CHU): 2% to 20% of total encounters.
  - Referral tracking (`referral_from_facility_id`) references valid upstream facilities.

---

## 4. Directory Layout

```
fhir-pipeline/
├── data/
│   ├── reference/
│   │   └── togo_health_geography.parquet       # Frozen reference table (185 facilities, 44 districts, 6 regions)
│   └── truth/                                  # Target directory for generated Ground Truth
│       ├── patients.parquet
│       ├── encounters.parquet
│       ├── conditions.parquet
│       ├── observations.parquet
│       ├── prescriptions.parquet
│       ├── immunizations.parquet
│       └── dhis2/
│           ├── dhis2_data_values.json
│           └── dhis2_data_values.parquet
├── terminology/
│   └── sample_vocabularies.parquet             # Mock vocabularies < 1 MB (81 concepts, 9 pathologies + PEV)
├── src/
│   ├── cli.py                                  # Typer CLI entrypoint
│   └── generation/
│       ├── __init__.py                         # Generator exports
│       ├── schemas.py                          # PyArrow & Pydantic schemas
│       ├── demographics.py                     # Togolese onomastics & demographic pyramid
│       ├── clinical_rules.py                   # Clinical pathways, 9 pathologies, LOINC, ATC, PEV
│       ├── contextual_generator.py             # Ground Truth orchestrator
│       └── dhis2_generator.py                  # DHIS2 aggregate engine & offline fallback
├── tests/
│   ├── conftest.py                             # Shared fixtures
│   ├── test_socle.py                           # Baseline tests
│   ├── test_docker_compose.py                  # Container configuration tests
│   ├── test_cli.py                             # General CLI tests
│   ├── test_uris.py                            # URI architecture tests
│   ├── test_geography.py                       # Geography & pyramid tests
│   ├── test_terminology.py                     # Terminology & pathology tests
│   ├── test_cli_etape2.py                      # Étape 2 CLI tests
│   ├── test_generation.py                      # Étape 3 Ground Truth & DHIS2 test suite (Tiers 1-4)
│   └── test_cli_generation.py                  # Étape 3 CLI Typer test suite
├── TEST_INFRA.md                               # This document
└── TEST_READY.md                               # Test suite readiness & execution summary
```

---

## 5. Execution Commands & Quality Gates

### Running All Étape 3 Tests
```bash
uv run pytest tests/test_generation.py tests/test_cli_generation.py -v
```

### Running Full Project Test Suite
```bash
uv run pytest -v
```

### Running in Strict Acceptance Gate Mode (CI Gate)
```bash
STRICT_E2E=1 uv run pytest -v
```

### Code Quality & Linting
```bash
uv run ruff check .
uv run ruff format --check .
```

### Acceptance Gate Criteria
- **Pass rate**: 100% of executed tests pass.
- **Ruff linter**: 0 errors, 0 warnings.
- **Host Docker safety**: 0 host containers stopped or restarted (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).
- **Network isolation**: 0 external network requests during test runs.
