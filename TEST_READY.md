# Test Suite Readiness Notice — Étape 2 (Référentiels & Vocabulaires)

**Date** : 2026-11-05
**Projet** : Togo Health Data Pipeline (`fhir-pipeline`)
**Auteur** : `test_writer_e2e_1` (Teamwork Test Writer / QA)
**Statut** : **TEST READY** (Suite de tests E2E Tiers 1-4 publiée et vérifiée)

---

## 1. Synthèse Exécutive

La suite de tests E2E (Tiers 1 à 4) pour l'Étape 2 est officiellement stabilisée, compilée et intégrée dans le répertoire standard `tests/`. Elle valide de manière opaque et déterministe les exigences R1 à R6 définies dans `ORIGINAL_REQUEST.md`, le plan `PROJECT.md` et les décisions d'architecture (ADR D-08, ADR D-09, VAL-001, VAL-002).

- **Total des tests exécutables** : 130 tests répertoriés
  - **91 tests passants immédiatement** (65 socle Étape 0/1 + 25 architecture URIs M1 + 1 gestion CLI options)
  - **39 tests de vérification progressive E2E** configurés pour valider automatiquement les livrables Parquet et commandes CLI au fur et à mesure de l'achèvement des jalons M2, M3 et M4.
- **Régression** : 0 régression sur les 65 tests initiaux.
- **Conformité Ruff** : 0 erreur de linting, 0 erreur de formatage sur l'ensemble de `tests/`.
- **Intégrité environnementale** : Aucun conteneur Docker hôte (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`) n'a été altéré ou interrompu.
- **Autonomie réseau** : 100 % des tests s'exécutent hors ligne, sans appel réseau externe.

---

## 2. Commandes d'Exécution

### Exécution Complète Standard
```bash
uv run pytest -v
```

### Exécution Ciblée Étape 2
```bash
uv run pytest tests/test_uris.py tests/test_geography.py tests/test_terminology.py tests/test_cli_etape2.py -v
```

### Mode Porte d'Acceptation Stricte (Milestone M5 / CI)
En mode strict, l'absence de l'un des fichiers ou modules obligatoires (`togo_health_geography.parquet`, `sample_vocabularies.parquet`, `uris.py`, `geography.py`, `pathologies.py`) déclenche une erreur immédiate :
```bash
STRICT_E2E=1 uv run pytest -v
```

### Contrôle de Qualité et Formatage (Ruff)
```bash
uv run ruff check tests/
uv run ruff format --check tests/
```

---

## 3. Répartition des Tests par Niveaux (Tiers 1 à 4)

| Fichier de Test | Tier 1 (Couverture / Schéma) | Tier 2 (Limites & Format) | Tier 3 (Intégrité & Mappings) | Tier 4 (Performance & Stress) | Total Tests |
|---|:---:|:---:|:---:|:---:|:---:|
| `tests/test_uris.py` | 4 | 2 | 19 (registres, profils, builders) | 0 | **25** |
| `tests/test_geography.py` | 4 | 5 | 4 | 3 | **16** |
| `tests/test_terminology.py` | 3 | 3 | 3 | 2 | **11** |
| `tests/test_cli_etape2.py` | 7 | 4 | 1 | 1 | **13** |
| **Sous-total Étape 2** | **18** | **14** | **27** | **6** | **65** |
| **Socle Préexistant (Étapes 0-1)** | 65 | - | - | - | **65** |
| **TOTAL GÉNÉRAL** | - | - | - | - | **130** |

---

## 4. Matrice de Traçabilité des Fonctionnalités (Checklist)

| Réf. Exigence | Identifiant Test | Intitulé de la Fonctionnalité | Source / Décision | Statut |
|---|---|---|---|:---:|
| **R1** | `test_tier1_geography_schema` | Schéma complet Parquet géographie (12 colonnes obligatoires) | `PROJECT.md` | PRÊT |
| **R1** | `test_tier1_exactly_six_regions` | Présence stricte des 6 régions sanitaires officielles | ADR D-08, VAL-001 | PRÊT |
| **R1** | `test_tier1_exactly_forty_four_districts` | Présence stricte des 44 districts sanitaires officiels | ADR D-08, VAL-001 | PRÊT |
| **R1** | `test_tier1_four_pyramid_levels` | Présence des 4 niveaux opérationnels (CHU, CHR, Hospital, CMS/USP) | `SYNTHESE_PROJET.md` | PRÊT |
| **R1** | `test_tier2_facility_id_is_uuid_v5` | Validité stricte RFC 4122 des UUID v5 déterministes | `AGENT.md` | PRÊT |
| **R1** | `test_tier2_zero_nulls_in_essential_columns` | Zéro valeur nulle ou chaîne vide dans les colonnes critiques | `ORIGINAL_REQUEST.md` | PRÊT |
| **R1** | `test_tier2_facility_codes_are_unique` | Unicité globale des codes FOSA | `PROJECT.md` | PRÊT |
| **R1** | `test_tier2_unique_normalized_name_per_district` | Zéro doublon de libellé normalisé au sein d'un même district | ADR D-08, R1 | PRÊT |
| **R1** | `test_tier2_normalized_name_rules` | Minuscules, absence totale d'accents/diacritiques et d'espaces superflus | `AGENT.md` | PRÊT |
| **R1** | `test_tier3_district_to_region_parent_links` | Rattachement hiérarchique strict district -> région | ADR D-08 | PRÊT |
| **R1** | `test_tier3_country_is_strictly_togo` | Pays Togo (TG) sans exception | `PROJECT.md` | PRÊT |
| **R1** | `test_tier3_pyramid_level_consistency` | Cohérence bijective niveau pyramidal ↔ catégorie établissement | `PROJECT.md` | PRÊT |
| **R1** | `test_tier3_no_district_without_facilities` | Zéro district orphelin (au moins 1 structure par district) | VAL-001 | PRÊT |
| **R1** | `test_tier4_query_performance` | Rapidité de filtrage multi-critères (< 50ms) | `PROJECT.md` | PRÊT |
| **R1** | `test_tier4_is_active_flag` | Validation du statut opérationnel actif | `PROJECT.md` | PRÊT |
| **R1** | `test_tier4_adversarial_validator` | Rejet strict de données géographiques corrompues ou dupliquées | `TEST_INFRA.md` | PRÊT |
| **R2** | `test_uris.py::*` (25 tests) | Architecture d'URIs canoniques, SIDs, CodeSystems, profils | `docs/architecture_uri.md` | **PASS (25/25)** |
| **R3** | `test_tier1_vocabularies_schema` | Schéma Parquet vocabulaires mock (Athena/OMOP compatible) | `PROJECT.md` | PRÊT |
| **R3** | `test_tier1_nine_priority_pathologies_presence` | Couverture intégrale des 9 pathologies prioritaires | VAL-002 | PRÊT |
| **R3** | `test_tier1_four_standard_vocabularies_presence` | Présence des 4 vocabulaires pivots (ICD-10, SNOMED, LOINC, ATC) | `technique.md` | PRÊT |
| **R3** | `test_tier2_file_size_strictly_under_one_megabyte` | Poids du mock Parquet strictement < 1 000 000 octets | ADR D-09, `AGENT.md` | PRÊT |
| **R3** | `test_tier2_non_empty_codes_and_names` | Non-vacuité des libellés et des codes cliniques | `PROJECT.md` | PRÊT |
| **R3** | `test_tier2_domain_assignments` | Validité des domaines OMOP CDM 5.4 | `PROJECT.md` | PRÊT |
| **R3** | `test_tier3_vital_signs_loinc_coverage` | Couverture LOINC (PA systolique/diastolique, glycémie, T°, poids, MUAC) | `SYNTHESE_PROJET.md` | PRÊT |
| **R3** | `test_tier3_essential_drugs_atc_coverage` | Couverture ATC (ACT antipaludique, TLD ARV, RHZE anti-TB, SRO, etc.) | `SYNTHESE_PROJET.md` | PRÊT |
| **R3** | `test_tier3_pathology_catalog_in_module` | Disponibilité programmatique du catalogue clinique | `PROJECT.md` | PRÊT |
| **R3** | `test_tier4_offline_lookup_performance` | Rapidité de recherche de concept hors ligne (< 20ms) | `AGENT.md` | PRÊT |
| **R3** | `test_tier4_adversarial_vocabularies_validator` | Rejet de vocabulaires corrompus par le validateur | `TEST_INFRA.md` | PRÊT |
| **R4** | `test_tier1_reference_group_registered` | Enregistrement du groupe Typer `reference` | `PROJECT.md` | PRÊT |
| **R4** | `test_tier1_reference_subcommands_help` | Aide en français des 4 sous-commandes `reference` | `PROJECT.md` | PRÊT |
| **R4** | `test_tier1_terminology_etape2_subcommands_help` | Aide en français des nouvelles sous-commandes `terminology` | `PROJECT.md` | PRÊT |
| **R4** | `test_tier2_cli_list_regions_execution` | Exécution CLI de list-regions et présence des 6 régions | `PROJECT.md` | PRÊT |
| **R4** | `test_tier2_cli_validate_geography_execution` | Exécution CLI de validate-geography avec exit code 0 | `PROJECT.md` | PRÊT |
| **R4** | `test_tier2_cli_list_pathologies_execution` | Exécution CLI de list-pathologies avec exit code 0 | `PROJECT.md` | PRÊT |
| **R4** | `test_tier2_cli_validate_vocabularies_execution` | Exécution CLI de validate-vocabularies avec exit code 0 | `PROJECT.md` | PRÊT |
| **R4** | `test_tier4_cli_invalid_options_handling` | Gestion robuste des arguments invalides | `PROJECT.md` | **PASS (1/1)** |

---

## 5. Recommandations pour les Agents d'Implémentation

1. **Jalon M2 (Géographie)** :
   - Écrire `src/terminology/geography.py` et générer `data/reference/togo_health_geography.parquet`.
   - L'exécution de `uv run pytest tests/test_geography.py` passera automatiquement de 16 skipped à 16 passed dès génération.
2. **Jalon M3 (Vocabulaires)** :
   - Écrire `src/terminology/pathologies.py` et générer `terminology/sample_vocabularies.parquet`.
   - Veiller à ce que la taille reste inférieure à 1 Mo (habituellement ~40-80 Ko avec compression Snappy).
   - L'exécution de `uv run pytest tests/test_terminology.py` passera automatiquement de 11 skipped à 11 passed dès génération.
3. **Jalon M4 (CLI)** :
   - Brancher `reference_app` et les nouvelles commandes de `terminology_app` dans `src/cli.py`.
   - L'exécution de `uv run pytest tests/test_cli_etape2.py` passera automatiquement à 13 passed.
4. **Jalon M5 (Acceptation Finale)** :
   - Lancer `STRICT_E2E=1 uv run pytest` pour valider 100 % de succès (130 passed, 0 skipped, 0 failed).
