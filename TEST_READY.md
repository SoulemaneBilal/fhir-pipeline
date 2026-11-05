# Test Suite Readiness Notice — Étape 5 (Ingestion Raw, Bronze & Quarantaine)

**Date** : 2026-11-05  
**Projet** : Togo Health Data Pipeline (`fhir-pipeline`)  
**Auteurs** : Équipe d'Ingénierie Multi-Agents (`test_writer_etape5`, `worker_etape5`, `reviewer_etape5`, `challenger_etape5`, `auditor_etape5`)  
**Statut** : **TEST READY** (Suite de tests E2E Tiers 1-6 publiée, vérifiée et 100 % passante en mode `STRICT_E2E`)

---

## 1. Synthèse Exécutive

La suite de tests automatisée pour l'Étape 5 (Ingestion Multi-Formats : Raw, Bronze et Quarantaine) est officiellement développée, validée et intégrée dans le dépôt aux chemins suivants :
- `tests/test_ingestion.py` (Suite principale Tiers 1 à 6 pour les modèles, lecteurs, couche Raw, couche Bronze, quarantaine résiliente et moteur global)
- `tests/test_cli_ingestion.py` (Validation des commandes Typer `pipeline raw ingest`, `pipeline raw status`, `pipeline bronze convert`, `pipeline bronze validate`)
- `TEST_INFRA.md` (Spécification détaillée de l'infrastructure de test)
- `TEST_READY.md` (Présent rapport de disponibilité et métriques)

### Métriques Clés :
- **Total des tests Étape 5 créés** : 44 tests unitaires et E2E
  - `tests/test_ingestion.py` : 32 tests
  - `tests/test_cli_ingestion.py` : 12 tests
- **Résultat d'exécution en mode STRICT_E2E** :
  - **44 tests passés avec succès sur 44 (100 % PASS, 0 skip, 0 fail en 1.60s)**.
  - Couverture complète des 6 Tiers :
    * **Tier 1 (Modèles & Schémas)** : Schémas Pydantic / PyArrow (`SourceFormat`, `RawFileRecord`, `RawManifest`, `QuarantineRecord`, `AUDIT_COLUMNS`, `BRONZE_AUDIT_SCHEMA`).
    * **Tier 2 (Lecteurs Multi-Formats)** : Excel multi-feuilles (`.xlsx`, `.xls`), CSV délimiteurs multiples (`,`, `;`, `\t`, `|`) et encodages (`utf-8`, `latin-1`, `cp1252`) avec préservation des diacritiques français togolais, Bundles FHIR R4 JSON, exports DHIS2 `dataValueSets`, renifleur `detect_source_type`.
    * **Tier 3 (Couche Raw & SHA-256)** : Copie bit-à-bit strictement conforme, calcul SHA-256 par bloc de 64 Ko, manifeste d'ingestion `raw_manifest.json`, idempotence absolue et audit de corruption `verify_raw_integrity`.
    * **Tier 4 (Couche Bronze Parquet)** : Injection systématique des 4 métadonnées obligatoires (`source_file`, `source_row`, `ingested_at`, `content_hash`), égalité stricte des comptes de lignes (`len(df_bronze) == len(source_valid_rows)`), tables Parquet typées DuckDB/PyArrow, déterminisme SHA-256.
    * **Tier 5 (Quarantaine Résiliente & Règle d'Or)** : Isolement de binaires corrompus et JSON malformés avec fiches d'incidents codifiées ; vérification absolue que l'incident n'interrompt pas le lot (fichiers valides convertis à 100%).
    * **Tier 6 (Moteur Global & Pipeline E2E)** : `IngestionEngine`, `run_ingestion_pipeline`, simulation `--dry-run` et métriques de synthèse.
    * **Commandes CLI Typer** : Groupes `raw` (`ingest`, `status`) et `bronze` (`convert`, `validate`) avec aide en français, options complètes et gestion d'erreurs.
- **Tests globaux du projet** : **278 tests passés sur 278** en mode `STRICT_E2E=1` (100 % de succès).
- **Régression** : 0 régression sur l'ensemble des 234 tests existants (Étapes 0, 1, 2, 3 et 4).
- **Conformité Ruff** : 0 erreur de linting (`ruff check .`), 0 erreur de formatage (`ruff format --check .`).
- **Sécurité des conteneurs hôtes** : Les 5 conteneurs Docker hôtes préexistants (`backend`, `backend-db`, `fhir`, `icd-api`, `frontend`) demeurent strictement préservés, actifs et sains.
- **Autonomie réseau** : 100 % des tests s'exécutent hors ligne, sans requête sortante.

---

## 2. Commandes d'Exécution

### 1. Exécution Ciblée Étape 5 (Mode Strict)
```bash
STRICT_E2E=1 uv run pytest tests/test_ingestion.py tests/test_cli_ingestion.py -v
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
