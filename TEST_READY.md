# Test Suite Readiness Notice — Étape 4 (Moteur de Dégradation Contrôlée)

**Date** : 2026-11-05  
**Projet** : Togo Health Data Pipeline (`fhir-pipeline`)  
**Auteurs** : Équipe d'Ingénierie Multi-Agents (`test_writer_etape4`, `worker_etape4`, `reviewer_etape4`, `challenger_etape4`, `auditor_etape4`)  
**Statut** : **TEST READY** (Suite de tests E2E Tiers 1-5 publiée, vérifiée et 100 % passante en mode `STRICT_E2E`)

---

## 1. Synthèse Exécutive

La suite de tests automatisée pour l'Étape 4 (Moteur de Dégradation Contrôlée et Stress-Test) est officiellement développée, validée et intégrée dans le dépôt aux chemins suivants :
- `tests/test_degradation.py` (Suite principale Tiers 1 à 5 pour le catalogue, mutateurs, journal d'altérations, moteur global et exportateurs)
- `tests/test_cli_degradation.py` (Validation des commandes Typer `pipeline degradation list-rules` et `pipeline degradation apply`)
- `TEST_INFRA.md` (Spécification détaillée de l'infrastructure de test)
- `TEST_READY.md` (Présent rapport de disponibilité et métriques)

### Métriques Clés :
- **Total des tests Étape 4 créés** : 46 tests unitaires et E2E
  - `tests/test_degradation.py` : 38 tests
  - `tests/test_cli_degradation.py` : 8 tests
- **Résultat d'exécution en mode STRICT_E2E** :
  - **46 tests passés avec succès sur 46 (100 % PASS, 0 skip, 0 fail en 4.08s)**.
  - Couverture complète des 5 Tiers :
    * **Tier 1 (Catalogue & Configuration)** : 8 tests (chargement YAML, Pydantic, complétude des 16 règles obligatoires, unicité, descriptions en français, tables et colonnes cibles, bornes des taux `[0.0, 1.0]`).
    * **Tier 2 (Mutateurs Unitaires)** : 15 tests (dates mixtes, âges approximatifs, coquilles patronymes, suppression accents, inversion nom/prénom, libellés cliniques libres, séparateur virgule, unités UCUM altérées, sentinelles, valeurs manquantes, mojibake encodage, noms de structures sanitaires).
    * **Tier 3 (Journal d'Altérations & Réversibilité)** : 4 tests (schéma PyArrow strict, modèle Pydantic, sérialisation Parquet et JSONL, réversibilité intégrale / corrigé de référence, absence de mutation non tracée).
    * **Tier 4 (Moteur de Dégradation Global)** : 7 tests (exécution sur les 6 tables cliniques, respect du taux cible +/- 5%, injection de doublons patients pour Splink, déterminisme bit-à-bit SHA-256 sous graine fixe, divergence entre graines distinctes, robustesse aux cas limites).
    * **Tier 5 (Exportateurs Multi-Formats)** : 4 tests (Excel `.xlsx` multi-onglets, CSV délimiteur point-virgule, JSON/FHIR altéré avec anomalies documentées, agrégats DHIS2 dégradés).
    * **Commandes CLI Typer** : 8 tests (aide en français, options `--rate`, `--seed`, `--output-dir`, `--detailed`, validation des taux invalides).
- **Tests globaux du projet** : **234 tests passés sur 234** en mode `STRICT_E2E=1` (100 % de succès).
- **Régression** : 0 régression sur l'ensemble des 188 tests existants (Étapes 0, 1, 2 et 3).
- **Conformité Ruff** : 0 erreur de linting (`ruff check .`), 0 erreur de formatage (`ruff format --check .`).
- **Sécurité des conteneurs hôtes** : Les 5 conteneurs Docker hôtes préexistants (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`) demeurent strictement préservés et actifs sans aucune altération.
- **Autonomie réseau** : 100 % des tests s'exécutent hors ligne, sans requête sortante.

---

## 2. Commandes d'Exécution

### 1. Exécution Ciblée Étape 4 (Mode Strict)
```bash
STRICT_E2E=1 uv run pytest tests/test_degradation.py tests/test_cli_degradation.py -v
```

### 2. Exécution de la Suite Complète du Pipeline
```bash
uv run pytest
```

### 3. Contrôle de Style et Formatage Ruff
```bash
uv run ruff check .
uv run ruff format --check .
```
