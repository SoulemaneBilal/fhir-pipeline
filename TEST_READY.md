# Test Suite Readiness Notice — Étape 3 (Génération Vérité Terrain & Agrégats DHIS2)

**Date** : 2026-11-05  
**Projet** : Togo Health Data Pipeline (`fhir-pipeline`)  
**Auteur** : `test_writer_etape3` (Teamwork Test Writer / QA)  
**Statut** : **TEST READY** (Suite de tests E2E Tiers 1-4 publiée, vérifiée et 100 % passante en mode STRICT_E2E)

---

## 1. Synthèse Exécutive

La suite de tests automatisée pour l'Étape 3 (Générateur de Vérité Terrain et Agrégats Statistiques DHIS2) est officiellement développée, validée et intégrée dans le dépôt aux chemins suivants :
- `tests/test_generation.py` (Suite principale Tiers 1 à 4 pour le moteur de génération clinique et DHIS2)
- `tests/test_cli_generation.py` (Validation des commandes Typer `pipeline generation run` et `pipeline generation dhis2-demo`)
- `TEST_INFRA.md` (Spécification détaillée de l'infrastructure de test)
- `TEST_READY.md` (Présent rapport de disponibilité et métriques)

### Métriques Clés :
- **Total des tests Étape 3 créés** : 27 tests unitaires et E2E
  - `tests/test_generation.py` : 18 tests
  - `tests/test_cli_generation.py` : 9 tests
- **Résultat d'exécution en mode STRICT_E2E** :
  - **27 tests passés avec succès sur 27 (100 % PASS, 0 skip, 0 fail en 7.81s)**.
  - Couverture complète des 4 Tiers :
    * Tier 1 : 6 tables Parquet + 2 fichiers DHIS2, clés UUID v5 non-nulles, intégrité référentielle, schémas typés.
    * Tier 2 : Cas limites (`count=1`, `count=50`, rejets `count<=0`), repli hors-ligne DHIS2, règles cliniques (interdiction grossesse hommes, vaccins PEV pédiatriques uniquement, pathologies chroniques adultes, règle VAL-003 des âges estimés au 1er juillet).
    * Tier 3 : Déterminisme strict bit-à-bit (SHA-256 identiques à graine égale, divergence à graines distinctes).
    * Tier 4 : 100 % adhérence géographique (`togo_health_geography.parquet`), 100 % adhérence terminologique (`sample_vocabularies.parquet`), pyramide sanitaire (~72 % niveau 1).
- **Tests globaux du projet** : 188 tests passés, 0 skippé, 0 échec en mode `STRICT_E2E=1` (100 % de succès).
- **Régression** : 0 régression sur l'ensemble des 161 tests existants (Étapes 0, 1 et 2).
- **Conformité Ruff** : 0 erreur de linting (`ruff check .`), 0 erreur de formatage (`ruff format --check .`).
- **Sécurité des conteneurs hôtes** : Les 5 conteneurs Docker hôtes préexistants (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`) demeurent strictement préservés et actifs sans aucune altération.
- **Autonomie réseau** : 100 % des tests s'exécutent hors ligne, sans requête sortante.

---

## 2. Commandes d'Exécution

### 1. Exécution Ciblée Étape 3
```bash
uv run pytest tests/test_generation.py tests/test_cli_generation.py -v
```

### 2. Exécution Complète du Projet
```bash
uv run pytest -v
```

### 3. Exécution en Mode Porte d'Acceptation Stricte (CI Gate)
```bash
STRICT_E2E=1 uv run pytest -v
```

### 4. Contrôle Qualité et Formatage (Ruff)
```bash
uv run ruff check tests/test_generation.py tests/test_cli_generation.py
uv run ruff format --check tests/test_generation.py tests/test_cli_generation.py
```

---

## 3. Répartition des Tests par Niveaux (Tiers 1 à 4)

| Fichier de Test | Tier 1 (Couverture / Schémas) | Tier 2 (Cas Limites & Clinique) | Tier 3 (Déterminisme) | Tier 4 (Adhérence Référentiels) | Total Tests | Statut STRICT_E2E |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `tests/test_generation.py` | 5 | 7 | 3 | 3 | **18** | **18/18 PASS** |
| `tests/test_cli_generation.py` | 3 | 6 | - | - | **9** | **9/9 PASS** |
| **Total Étape 3** | **8** | **13** | **3** | **3** | **27** | **27/27 PASS** |
| **Socle Antérieur (Étapes 0, 1, 2)** | 161 | - | - | - | **161** | **161/161 PASS** |
| **TOTAL GÉNÉRAL DU PROJET** | - | - | - | - | **188** | **188/188 PASS** |

---

## 4. Matrice de Traçabilité des Exigences Étape 3

| Exigence | ID Test | Description Fonctionnelle | Règle / Référentiel | Statut |
|---|---|---|---|:---:|
| **R1** | `test_tier1_clinical_parquet_files_exist_and_non_empty` | Génération effective des 6 tables Parquet cliniques dans `data/truth/` | ADR D-04, R1 | **PASS** |
| **R1** | `test_tier1_primary_keys_non_null_and_uuid_v5` | Validité stricte RFC 4122 des clés primaires UUID v5 et unicité | `AGENT.md:29` | **PASS** |
| **R1** | `test_tier1_referential_integrity_foreign_keys` | Intégrité référentielle stricte entre séjours, diagnostics, actes et patients | `SCOPE.md` | **PASS** |
| **R1** | `test_tier1_expected_columns_and_types` | Conformité des schémas PyArrow et présence de toutes les colonnes requises | `schemas.py` | **PASS** |
| **R1** | `test_tier2_boundary_count_minimal_cohort` | Génération aux bornes : cohorte minimale `count=1` sans division par zéro | `ORIGINAL_REQUEST.md` | **PASS** |
| **R1** | `test_tier2_boundary_count_zero_or_negative_raises_error` | Rejet explicite avec `ValueError` de `count=0` ou count négatif | `ORIGINAL_REQUEST.md` | **PASS** |
| **R1** | `test_tier2_clinical_no_male_with_pregnancy` | Règle clinique absolue : zéro diagnostic de grossesse (CIM-10 Z34, O80, O82, SMI) chez un patient masculin | `SYNTHESE_PROJET.md:477` | **PASS** |
| **R1** | `test_tier2_clinical_no_adult_with_pediatric_pev_vaccines` | Règle clinique : vaccins pédiatriques PEV Togo strictement réservés aux enfants < 5 ans | `ORIGINAL_REQUEST.md:177` | **PASS** |
| **R1** | `test_tier2_clinical_chronic_conditions_adults_only` | Règle clinique : HTA et Diabète de type 2 absents chez les nourrissons (< 5 ans) | `SCOPE.md` | **PASS** |
| **R1** | `test_tier2_val003_estimated_age_july_first_and_precision` | Conformité VAL-003 : date au 1er juillet (`-07-01`) et précision `'approximate-year'` pour âges estimés | VAL-003 | **PASS** |
| **R1** | `test_tier3_determinism_identical_seed_identical_files_sha256` | Déterminisme strict bit-à-bit : SHA-256 identiques sur tous les Parquet pour `seed=42` | `AGENT.md:25-44` | **PASS** |
| **R1** | `test_tier3_determinism_different_seeds_produce_different_data` | Divergence garantie des données et des hash SHA-256 entre graines différentes (42 vs 43) | `AGENT.md:32` | **PASS** |
| **R1** | `test_tier4_100_percent_geography_reference_adherence` | 100% des structures, districts et régions concordent avec `togo_health_geography.parquet` | ADR D-08 | **PASS** |
| **R1** | `test_tier4_100_percent_terminology_reference_adherence` | 100% des codes CIM-10, SNOMED, LOINC et ATC concordent avec `sample_vocabularies.parquet` | ADR D-09, VAL-002 | **PASS** |
| **R1** | `test_tier4_healthcare_pyramid_distribution_and_referrals` | Pyramide sanitaire : 60-85% des séjours au Niveau 1 (CMS/USP) et traçabilité des transferts | ADR D-08 | **PASS** |
| **R2** | `test_tier1_dhis2_files_exist_and_match` | Génération des agrégats DHIS2 en format JSON `dataValueSets` et Parquet tabulaire | `ORIGINAL_REQUEST.md:181` | **PASS** |
| **R2** | `test_tier2_dhis2_offline_fallback_with_invalid_url` | Résilience du repli hors-ligne en cas d'URL inaccessible sans crash ni timeout | `ORIGINAL_REQUEST.md:184` | **PASS** |
| **R2** | `test_tier3_dhis2_determinism_identical_seed` | Déterminisme strict des agrégats mensuels DHIS2 (SHA-256 identiques pour graine fixe) | `SCOPE.md` | **PASS** |
| **R3** | `test_cli_generation_group_help` | Enregistrement du groupe Typer `generation` et aide en français | `ORIGINAL_REQUEST.md:186` | **PASS** |
| **R3** | `test_cli_generation_run_help` | Options `--count`, `--seed`, `--output-dir` documentées dans `generation run --help` | `ORIGINAL_REQUEST.md:188` | **PASS** |
| **R3** | `test_cli_generation_dhis2_demo_help` | Options `--api-url`, `--output-dir` documentées dans `generation dhis2-demo --help` | `ORIGINAL_REQUEST.md:189` | **PASS** |
| **R3** | `test_cli_generation_run_execution` | Exécution effective de `pipeline generation run` créant les fichiers Parquet réels | `ORIGINAL_REQUEST.md:188` | **PASS** |
| **R3** | `test_cli_generation_dhis2_demo_execution` | Exécution effective de `pipeline generation dhis2-demo` avec export des agrégats | `ORIGINAL_REQUEST.md:189` | **PASS** |
| **R3** | `test_cli_generation_run_invalid_count_rejected` | Rejet propre des valeurs count <= 0 avec code retour non-nul | `ORIGINAL_REQUEST.md:190` | **PASS** |
| **R3** | `test_cli_generation_run_unknown_option_rejected` | Rejet des options CLI inconnues pour `generation run` (exit code 2) | Typer CLI | **PASS** |
| **R3** | `test_cli_generation_dhis2_unknown_option_rejected` | Rejet des options CLI inconnues pour `generation dhis2-demo` (exit code 2) | Typer CLI | **PASS** |
