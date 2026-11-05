# Test Infrastructure Specification — Étape 4 (Moteur de Dégradation Contrôlée)

## 1. Test Philosophy

The test infrastructure for the Togo Health Data Pipeline (`fhir-pipeline`) adheres to the core engineering principles articulated in `AGENT.md`, `SYNTHESE_PROJET.md`, and architectural decisions `docs/journal/DECISIONS.md`:

1. **Opaque-Box Specification Verification**:
   Tests verify behavioral contracts, schema definitions, clinical rules, and domain invariants as specified in authoritative requirements (`ORIGINAL_REQUEST.md`, `SCOPE.md`, ADR D-04, ADR D-08, ADR D-09, VAL-001, VAL-002, VAL-003), without coupling to ephemeral implementation details.

2. **Offline-First & Zero Network Dependencies**:
   Conforming to `AGENT.md` (§ 2.4, l. 121-125), all tests execute in complete network isolation. Outbound network requests to external terminology servers, live DHIS2 instances (`play.dhis2.org/demo`), or package repositories are forbidden during test runs.

3. **Strict Mathematical Determinism (Bit-for-Bit Parquet)**:
   Conforming to `AGENT.md` (l. 25-44) and ADR D-04, all generation and degradation processes must be strictly reproducible. Two consecutive runs with the same pseudo-random seed (`--seed 42`) must produce bit-for-bit identical Apache Parquet files and alteration logs (matching SHA-256 cryptographic checksums). PRNG isolation (`random.Random(seed)`) prevents global state leakage.

4. **100% Real-World Reference Adherence & Traceability**:
   Every alteration injected into the synthetic cohort must be exhaustively recorded in the `AlterationRecord` journal (`alteration_id`, `table_name`, `row_id`, `column_name`, `original_value`, `altered_value`, `rule_id`, `description`), establishing a reversible gold-standard answer key (*corrigé*).

5. **Host Environment Protection**:
   Tests must never alter, restart, or terminate pre-existing Docker containers running on the host system (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).

6. **Progressive Testability & Strict Mode Gate**:
   Tests provide a `STRICT_E2E=1` gate mode for milestone acceptance where missing artifacts or broken contracts trigger a strict failure.

---

## 2. Feature Inventory & Traceability Matrix (Étape 4)

| Feature ID | Requirement | Domain / Target | Authoritative Source | Test Suite File | Test Tiers |
|---|---|---|---|---|---|
| **FEAT-DEG-01** | R1, AGENT.md | YAML Error Catalog & Declarative Rules | `technique.md:52` | `tests/test_degradation.py` | Tier 1 |
| **FEAT-DEG-02** | R1 | 16 Canonical Rules (MANDATORY_RULE_IDS) | `tests/test_degradation.py:54` | `tests/test_degradation.py` | Tier 1 |
| **FEAT-DEG-03** | R1 | Unit Mutators (Dates, Ages, Names, Accents) | `technique.md:53-54` | `tests/test_degradation.py` | Tier 2 |
| **FEAT-DEG-04** | R1 | Unit Mutators (Clinical, Decimals, Units, Sentinels) | `technique.md:55-58` | `tests/test_degradation.py` | Tier 2 |
| **FEAT-DEG-05** | R1 | Unit Mutators (Missing, Mojibake, Facility Variants) | `technique.md:59-61` | `tests/test_degradation.py` | Tier 2 |
| **FEAT-DEG-06** | R2 | Alteration Journal (Pydantic & PyArrow Schema) | `technique.md:62` | `tests/test_degradation.py` | Tier 3 |
| **FEAT-DEG-07** | R2 | Reversibility (Ground Truth Reconstruction) | `technique.md:64` | `tests/test_degradation.py` | Tier 3 |
| **FEAT-DEG-08** | R3 | Full Engine Run & Target Rate Adherence (+/- 5%) | `technique.md:64` | `tests/test_degradation.py` | Tier 4 |
| **FEAT-DEG-09** | R3 | Inter-facility Patient Duplication for Splink | `technique.md:57` | `tests/test_degradation.py` | Tier 4 |
| **FEAT-DEG-10** | R3 | Bit-for-Bit Determinism (SHA-256 Identical) | `technique.md:48` | `tests/test_degradation.py` | Tier 4 |
| **FEAT-DEG-11** | R4 | Multi-Format Exporters (Excel, CSV, FHIR, DHIS2) | `technique.md:63` | `tests/test_degradation.py` | Tier 5 |
| **FEAT-DEG-12** | R5 | CLI Commands (`degradation apply`, `list-rules`) | `src/cli.py:1230` | `tests/test_cli_degradation.py` | CLI Tests |

---

## 3. Test Tier Architecture

### Tier 1: Catalog & Configuration
- **Objective**: Validate the declarative catalog `config/degradation_rules.yaml` and its Pydantic loader models.
- **Rule Completeness**: Asserts all 16 mandatory rule IDs are defined with unique keys and French descriptions (>= 10 chars).
- **Bounds Checking**: Asserts all default rates are strictly bounded in `[0.0, 1.0]`.

### Tier 2: Unit Mutators
- **Objective**: Validate isolated, deterministic mutation functions with seeded PRNGs.
- **Scope**: Date format variations, approximate ages, onomastic spelling variants, diacritic loss, inverted name order, free-text clinical terms, decimal comma separators, distorted measurement units, sentinel codes, missing values, mojibake encoding corruption, and facility name variations.

### Tier 3: Alteration Journal & Reversibility
- **Objective**: Validate the append-only alteration log as an audit answer key (*corrigé*).
- **Reversibility**: Confirms that applying the journal inverse transformation on degraded tables restores 100% of the original Ground Truth dataset.

### Tier 4: Engine Execution, Rate Adherence & Determinism
- **Objective**: Validate end-to-end degradation on all 6 clinical tables (`patients`, `encounters`, `conditions`, `observations`, `prescriptions`, `immunizations`).
- **Rate Adherence**: Formally checks that the proportion of affected patients matches the configured target rate within +/- 5% tolerance.
- **Splink Duplicates**: Validates injection of duplicated patients across health facilities with distinct UUIDs under `RULE-DUPL-001`.
- **Bit-for-Bit Determinism**: Asserts matching SHA-256 hashes across consecutive runs with `--seed 42`.

### Tier 5: Multi-Format Exporters
- **Objective**: Validate export functions preparing raw sources for Étape 5.
- **Formats**: Multi-sheet Excel workbook (`.xlsx`), proprietary semicolon-separated CSV (`.csv`), broken FHIR JSON bundles, and altered DHIS2 aggregates.

---

## 4. Directory Layout

```
fhir-pipeline/
├── config/
│   └── degradation_rules.yaml                  # Declarative error catalog (16 rules)
├── data/
│   ├── reference/
│   │   └── togo_health_geography.parquet       # Frozen reference table (185 facilities, 44 districts)
│   ├── truth/                                  # Ground Truth cohort (Étape 3)
│   └── degraded/                               # Degraded datasets & alteration logs (Étape 4)
├── src/
│   ├── cli.py                                  # Typer CLI entrypoint
│   └── degradation/
│       ├── __init__.py                         # Public API exports
│       ├── schemas.py                          # Pydantic models & PyArrow schemas
│       ├── catalog.py                          # DegradationCatalog loader & registry
│       ├── mutators.py                         # 12 pure seeded mutation functions
│       ├── engine.py                           # DegradationEngine & apply_degradation
│       └── exporters.py                        # Multi-format exporters (Excel, CSV, FHIR, DHIS2)
├── tests/
│   ├── test_degradation.py                     # Étape 4 degradation test suite (Tiers 1-5)
│   └── test_cli_degradation.py                 # Étape 4 CLI Typer test suite
├── TEST_INFRA.md                               # This document
└── TEST_READY.md                               # Test suite readiness & execution summary
```

---

## 5. Execution Commands & Quality Gates

### Running All Étape 4 Tests
```bash
STRICT_E2E=1 uv run pytest tests/test_degradation.py tests/test_cli_degradation.py -v
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
- **Pass rate**: 100% of executed tests pass (234/234 tests).
- **Ruff linter**: 0 errors, 0 warnings.
- **Host Docker safety**: 0 host containers stopped or restarted (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`).
- **Network isolation**: 0 external network requests during test runs.
