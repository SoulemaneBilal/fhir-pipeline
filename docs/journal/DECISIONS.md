# REGISTRE DES DÉCISIONS D'ARCHITECTURE DU PROJET (ADR)

**Projet** : Pipeline d'Interopérabilité et de Standardisation de Données de Santé — Togo (`fhir-pipeline`)  
**Statut global** : Validé et opposable  
**Dernière mise à jour** : 4 novembre 2026  
**Source d'arbitrage** : `SYNTHESE_PROJET.md` (Section 6)  

---

## Sommaire des Décisions Validées

- [D-01 : Gestionnaire de dépendances Python et gestion du lockfile](#d-01--gestionnaire-de-dépendances-python-et-gestion-du-lockfile)
- [D-02 : Normalisation de la version d'interpréteur Python](#d-02--normalisation-de-la-version-dinterpréteur-python)
- [D-03 : Normalisation linguistique de l'architecture des sous-paquets `src/`](#d-03--normalisation-linguistique-de-larchitecture-des-sous-paquets-src)
- [D-04 : Priorisation méthodologique de la Vérité Terrain (Étape 3)](#d-04--priorisation-méthodologique-de-la-vérité-terrain-étape-3)
- [D-05 : Moteur de stockage pour OMOP CDM 5.4 et outillage OHDSI](#d-05--moteur-de-stockage-pour-omop-cdm-54-et-outillage-ohdsi)
- [D-06 : Modalité d'intégration d'OpenHIM dans le pipeline batch](#d-06--modalité-dintégration-dopenhim-dans-le-pipeline-batch)
- [D-07 : Stratégie d'exécution de SUSHI / FHIR Shorthand (Étape 11)](#d-07--stratégie-dexécution-de-sushi--fhir-shorthand-étape-11)
- [D-08 : Référentiel territorial et cartographie sanitaire du Togo (Zone sensible #6)](#d-08--référentiel-territorial-et-cartographie-sanitaire-du-togo-zone-sensible-6)
- [D-09 : Stratégie de gestion des vocabulaires terminologiques volumineux Athena](#d-09--stratégie-de-gestion-des-vocabulaires-terminologiques-volumineux-athena)

---

### D-01 : Gestionnaire de dépendances Python et gestion du lockfile

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  `technique.md` (l.7) prescrivait `pip`, alors qu'`AGENT.md` (l.47) imposait formellement `uv`. Le dépôt initial contenait un fichier `requirements.txt` vide (0 octet) sans fichier `pyproject.toml`.
* **Décision retenue** :  
  **Option A (`uv` avec `pyproject.toml`)** : Adopter `uv` comme gestionnaire universel de projet et d'environnements. Centraliser les métadonnées et dépendances dans un fichier `pyproject.toml` canonique (PEP 517/621), supprimer `requirements.txt` et figer l'arbre des dépendances dans le lockfile déterministe `uv.lock`.
* **Justification** :  
  Vitesse d'exécution 10 à 100 fois supérieure à pip, lockfile universel garantissant la reproductibilité absolue entre postes et agents, alignement contractuel sur `AGENT.md:47`.
* **Conséquences** :  
  À l'Étape 0 : installation de `uv`, création de `pyproject.toml`, suppression de `requirements.txt`, génération de `uv.lock` via `uv sync`.

---

### D-02 : Normalisation de la version d'interpréteur Python

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  `AGENT.md` (l.47) et `technique.md` (l.7) imposent impérativement Python 3.11. L'environnement hôte actif disposait de Python 3.15.0 (version de développement sans wheels binaires pour `duckdb`, `pyarrow`, `splink`, `pandera`).
* **Décision retenue** :  
  **Option A (Python 3.11 strict)** : Télécharger et isoler un interpréteur CPython 3.11 via `uv python install 3.11`, fixer la contrainte `requires-python = ">=3.11,<3.12"` dans `pyproject.toml`, et construire l'environnement virtuel `.venv` sur cette base.
* **Justification** :  
  Seule version garantissant la disponibilité immédiate des binaires compilés (`manylinux`) pour la pile scientifique. Élimine tout risque d'échec de compilation C/C++/Rust.
* **Conséquences** :  
  Environnement `.venv` recréé sous Python 3.11 certifié dès l'Étape 0.

---

### D-03 : Normalisation linguistique de l'architecture des sous-paquets `src/`

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  `AGENT.md` contenait une contradiction interne entre la règle 1.3 (l.17 : « Identifiants de code en anglais ») et la section 4 (l.69-71 : énumération des répertoires en français `src/profilage`, `src/nettoyage`...). En Python, les noms de dossiers sous `src/` sont des modules importables en code (`import src.nettoyage`).
* **Décision retenue** :  
  **Option A (Nomenclature anglophone intégrale dans `src/`)** : Standardiser tous les noms de packages et sous-modules en anglais :
  `src/ingestion`, `src/profiling`, `src/cleaning`, `src/matching`, `src/canonical_model`, `src/terminology`, `src/ig`, `src/fhir_transform`, `src/validation`, `src/loading`, `src/omop_etl`, `src/export_ai`, `src/degradation`, `src/generation`.
* **Justification** :  
  Conformité stricte avec PEP 8 et la règle 1.3 d'`AGENT.md`. Élimine le mélange dysfonctionnel « franglais » dans les instructions d'import. La documentation technique, les docstrings, les commentaires et les rapports restent intégralement en français.
* **Conséquences** :  
  Création de l'arborescence des 14 packages sous `src/` en anglais à l'Étape 0. Mise à jour de la section 4 d'`AGENT.md`.

---

### D-04 : Priorisation méthodologique de la Vérité Terrain (Étape 3)

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  `definition_projet.md` exprimait le souhait d'avoir « Les deux », tandis que `technique.md` présentait Synthea (Voie A) et le générateur Python (Voie B) comme deux alternatives concurrentes. Développer les deux voies de front dès le départ risquait de doubler la charge sans valeur ajoutée immédiate.
* **Décision retenue** :  
  **Option A (Voie B Python prioritaire en Phase 1/2)** : Développer le générateur Python contextuel (`src/generation/contextual_generator.py`) en priorité n°1 pour couvrir nativement 100 % des pathologies prioritaires togolaises, les âges approximatifs et la pyramide sanitaire. Reporter l'adaptation lourde de Synthea (Voie A) en jalon d'extension ultérieur.
* **Justification** :  
  Synthea est fortement ancré dans le modèle de santé américain (US Core, assurances privées). L'adapter au Togo requiert l'écriture de modules G-CODER complexes en Java. Le générateur Python dédié offre une maîtrise absolue, une exécution légère et une adéquation directe avec les objectifs sanitaires togolais.
* **Conséquences** :  
  Concentration des développements de l'Étape 3 sur le générateur contextuel Python.

---

### D-05 : Moteur de stockage pour OMOP CDM 5.4 et outillage OHDSI

* **Statut** : Validé (Option C)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  Le pipeline s'appuie sur DuckDB pour le traitement in-process rapide, mais les Étapes 15 et 16 imposent l'exécution de la suite officielle de certification OHDSI (**Achilles** et **Data Quality Dashboard** en langage R). DuckDB présente des incompatibilités sévères avec le pilote R `DatabaseConnector` et les requêtes SQLRender d'OHDSI.
* **Décision retenue** :  
  **Option C (PostgreSQL conteneurisé dédié pour OMOP + exports Parquet)** : Héberger le schéma relationnel OMOP CDM 5.4 sous une base PostgreSQL 15 dédiée (`omop_cdm`) dans Docker Compose afin de garantir l'exécution sans friction d'Achilles et DQD, et exporter les tables OMOP en Parquet à l'Étape 17 pour l'IA et l'analytique locale DuckDB.
* **Justification** :  
  PostgreSQL est la plateforme de référence universellement éprouvée par la communauté OHDSI. Cohabite naturellement avec le conteneur PostgreSQL déjà requis pour HAPI FHIR.
* **Conséquences** :  
  Provisionnement de la base `omop_cdm` dans `docker-compose.yml` (Étape 1). ETL vers PostgreSQL (Étape 15). Exports Parquet (Étape 17).

---

### D-06 : Modalité d'intégration d'OpenHIM dans le pipeline batch

* **Statut** : Validé (Option C)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  Le projet s'inscrit dans une architecture OpenHIE prévoyant la passerelle OpenHIM devant HAPI FHIR, mais fonctionne par lots (batch) via une CLI Typer sans flux temps réel.
* **Décision retenue** :  
  **Option C (Double mode configurable via CLI, OpenHIM par défaut)** : Configurer la CLI pour router par défaut les transactions FHIR à travers la passerelle OpenHIM (`--use-openhim`) assurant authentification, traçabilité et métriques de médiation. Prévoir un drapeau d'ingestion directe (`--direct-hapi`) pour les tests lourds de volumétrie ou les benchmarks de performance.
* **Justification** :  
  Prouve concrètement la conformité à l'architecture OpenHIE sans pénaliser les phases de tests intensifs ou de chargements massifs.
* **Conséquences** :  
  Configuration des canaux OpenHIM dans `docker-compose.yml` (Étape 1). Adaptateur client HTTP prenant en charge les deux modes dans `src/loading/` (Étape 14).

---

### D-07 : Stratégie d'exécution de SUSHI / FHIR Shorthand (Étape 11)

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  L'Étape 11 requiert la compilation du Guide d'Implémentation Togo (FSH) au moyen de l'outil Node.js **SUSHI** (`fsh-sushi`). L'inspection de l'hôte a révélé l'absence de Node.js sur la machine de développement.
* **Décision retenue** :  
  **Option A (Conteneur Docker Node.js dédié pour SUSHI)** : Exécuter la compilation SUSHI et l'IG Publisher dans un conteneur éphémère Docker dédié encapsulant Node.js 20 LTS et `fsh-sushi` (`docker run --rm -v ./ig:/workspace ...`), sans installer Node sur la machine hôte.
* **Justification** :  
  Préserve l'étanchéité et la propreté de l'environnement hôte. Garantit une parfaite reproductibilité sur n'importe quel poste ou runner CI/CD GitHub Actions.
* **Conséquences** :  
  Scripts de build conteneurisés dans `src/ig/` (Étape 11).

---

### D-08 : Référentiel territorial et cartographie sanitaire du Togo (Zone sensible #6)

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  `AGENT.md` (l.107) classe la hiérarchie sanitaire en zone sensible n°6 (validation humaine obligatoire). `technique.md` (l.24) mentionnait une hésitation entre 35, 39 et 44 districts sanitaires.
* **Décision retenue** :  
  **Option A (Découpage officiel récent à 6 régions et 44 districts sanitaires)** : Adopter formellement l'organisation territoriale actuelle du Ministère de la Santé du Togo : **6 régions sanitaires** (Savanes, Kara, Centrale, Plateaux, Maritime, Grand Lomé) et **44 districts sanitaires**, complétés par le catalogue structuré des 4 niveaux d'établissements (CHU, CHR, Hôpitaux Préfectoraux/District, CMS et USP).
* **Justification** :  
  Reflète la réalité administrative contemporaine du système de santé togolais. Fournit des clés de blocage exactes pour le modèle de rapprochement Splink (Étape 8) et l'agrégation épidémiologique.
* **Conséquences** :  
  Génération et gel de la table de référence validée `data/reference/togo_health_geography.parquet` dès l'Étape 2.

---

### D-09 : Stratégie de gestion des vocabulaires terminologiques volumineux Athena

* **Statut** : Validé (Option A)  
* **Date d'arbitrage** : 4 novembre 2026  
* **Contexte** :  
  `AGENT.md` (l.123) exige : *« Aucun test ne dépend du réseau ni de données hors dépôt. Utiliser de petits jeux de test versionnés (moins de 1 Mo) »*. Or, les tables terminologiques Athena (OMOP, SNOMED CT, LOINC, CIM-10) dépassent plusieurs giga-octets et sont soumises à des licences de redistribution.
* **Décision retenue** :  
  **Option A (Mock minimaliste < 1 Mo versionné dans Git + script de téléchargement externe)** : Versionner dans le dépôt git un extrait terminologique synthétique ultraléger (< 1 Mo) sous `terminology/sample_vocabularies.parquet` couvrant 100 % des codes cliniques des pathologies prioritaires togolaises. Fournir une commande CLI Typer (`pipeline terminology fetch-athena`) téléchargeant les tables volumineuses complètes dans un répertoire local exclu de Git (`data/terminology_cache/`).
* **Justification** :  
  Permet d'exécuter l'intégralité des tests unitaires et de la suite CI GitHub Actions en totale autonomie sans accès réseau et en quelques secondes. Respecte les droits de propriété intellectuelle des terminologies internationales.
* **Conséquences** :  
  Création du mock de test à l'Étape 2. Développement de la commande de téléchargement externe à l'Étape 10. Exclusion de `data/terminology_cache/` dans `.gitignore`.
