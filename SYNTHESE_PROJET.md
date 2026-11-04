# RAPPORT DE SYNTHÈSE GLOBALE DU PROJET — FHIR-PIPELINE TOGO

**Sous-titre** : Pipeline de standardisation et d’interopérabilité de données de santé : de sources fragmentées (DHIS2, Excel, systèmes propriétaires) vers FHIR R4, OpenHIE et OMOP CDM 5.4, avec un jeu de données propre et exportable pour l’IA  
**Date d'émission** : 4 novembre 2026  
**Auteur** : Équipe d'Analyse Multi-Agents (Business Spec Miner, Technical Spec Miner, Explorer Coherence, Synthesis Writer)  
**Destinataires** : Porteur de projet, Architectes techniques, Évaluateurs et Auditeurs  
**Statut du document** : Document de référence — Audit préalable et cadrage d'implémentation (Phase 1)

---

## Sommaire Exécutif

1. [Résumé Exécutif & Vision Globale](#1-résumé-exécutif--vision-globale)
   - 1.1 Contexte Sanitaire et Problématique de Fragmentation au Togo
   - 1.2 Postulat Fondamental, Éthique et Conformité Légale
   - 1.3 Objectifs Primaires et Secondaires
   - 1.4 Périmètre Fonctionnel Formel (Inclusions et Exclusions)
2. [Architecture Technique et Pipeline de Données](#2-architecture-technique-et-pipeline-de-données)
   - 2.1 Modèle Medallion Data Lakehouse Adapté à la Santé
   - 2.2 Composants d'Infrastructure et Pile Logicielle
   - 2.3 Principes Inviolables d'Intégrité Opérationnelle
3. [Spécification des Étapes du Pipeline (Roadmap Technique 0 à 21)](#3-spécification-des-étapes-du-pipeline-roadmap-technique-0-à-21)
   - 3.1 Découpage Général et Enchaînement Séquentiel
   - 3.2 Spécification Détaillée des 22 Étapes
4. [État des Lieux Actuel du Dépôt et Diagnostic d'Environnement](#4-état-des-lieux-actuel-du-dépôt-et-diagnostic-denvironnement)
   - 4.1 Diagnostic Factuel des Fichiers du Dépôt
   - 4.2 Diagnostic de l'Environnement Système Hôte
5. [Audit de Cohérence et Matrice des Discordances Inter-Documentaires](#5-audit-de-cohérence-et-matrice-des-discordances-inter-documentaires)
   - 5.1 Matrice d'Analyse des 18 Anomalies, Incohérences et Omissions Détectées
   - 5.2 Analyse Approfondie des Divergences Majeures
6. [Questions Décisionnelles et Arbitrages Requis de l'Utilisateur](#6-questions-décisionnelles-et-arbitrages-requis-de-lutilisateur)
   - 6.1 Tableau des Choix Structurants et Recommandations
   - 6.2 Fiches Détaillées des Décisions à Arbitrer
7. [Plan d'Action et Recommandations Immédiates](#7-plan-daction-et-recommandations-immédiates)
   - 7.1 Étape 0 : Cadrage du Socle et Initialisation du Dépôt
   - 7.2 Étape 1 : Déploiement de l'Infrastructure et Outillage CLI
   - 7.3 Jalons de Suivi et Gouvernance Multi-Agents

---

## 1. Résumé Exécutif & Vision Globale

### 1.1 Contexte Sanitaire et Problématique de Fragmentation au Togo

Dans la majorité des systèmes de santé d'Afrique de l'Ouest, et particulièrement au **Togo**, l'information sanitaire souffre d'un cloisonnement structurel aigu. Bien que des flux de données soient régulièrement collectés au sein des formations sanitaires (centres de soins périphériques, hôpitaux de district, centres hospitaliers régionaux et universitaires), ces données demeurent **fragmentées, hétérogènes, non standardisées et inexploitables** tant pour le suivi épidémiologique en temps utile que pour la recherche clinique ou l'entraînement de modèles d'intelligence artificielle.

L'analyse des documents sources (`Definition  Projet.md`, lignes 9-17) met en exergue sept verrous majeurs :

1. **Hétérogénéité extrême des formats de collecte** : Coexistence de flux d'agrégats mensuels issus de l'outil national de surveillance (DHIS2), de cahiers et classeurs Excel hétéroclites tenus localement par le personnel soignant, d'extraits CSV provenant de logiciels de gestion hospitalière propriétaires fermés, et de registres physiques saisis tardivement a posteriori.
2. **Absence d'Identifiant Unique du Patient (IUP / Master Patient Index)** : Un patient donné est identifié sous des matricules disparates selon l'établissement fréquenté. De surcroît, les états civils comportent fréquemment un **âge approximatif** (*« environ 35 ans »*) en lieu et place d'une date de naissance exacte. Les patronymes et prénoms, issus des langues locales (éwé, mina, kabiyè, tem, moba, etc.), subissent des variations graphiques, des inversions ordre nom/prénom ou des translittérations multiples (ex. *« Kodjo »* vs *« Koudjo »*, *« Afi »* vs *« Afiavi »*).
3. **Libellés cliniques textuels libres en français sans codification** : Les diagnostics et actes sont consignés sous forme de chaînes textuelles non contrôlées (ex. *« palu simple »*, *« Paludisme non compliqué »*, *« ACCÈS PALUSTRE »*) sans rattachement formel aux nomenclatures internationales de référence (CIM-10 / ICD-10, SNOMED CT, LOINC, ATC).
4. **Instabilité et imprécision du référentiel territorial et sanitaire** : Les dénominations des régions administratives/sanitaires, des districts et des formations sanitaires (Unités de Soins Périphériques - USP, Centres Médico-Sociaux - CMS, Hôpitaux) varient selon les agents de saisie, en l'absence d'une nomenclature nationale partagée et persistante par code unique.
5. **Collecte intermittente et synchronisation asynchrone** : En raison des contraintes d'infrastructure réseau, la saisie s'effectue souvent hors ligne avec téléversements périodiques différés, provoquant des conflits d'horodatage, des duplications d'enregistrements et des ruptures de version.
6. **Mélange conceptuel entre données agrégées et données individuelles** : Une confusion critique prévaut entre les statistiques agrégées de santé publique (comptages de cas pour les programmes verticaux DHIS2) et les données cliniques unitaires de parcours patient (*Tracker*). Le pipeline traite formellement cette distinction : un agrégat DHIS2 n'est jamais assimilé à un patient, mais transformé en ressource populationnelle FHIR (`MeasureReport`), tandis que les épisodes cliniques deviennent des ressources `Encounter` / `Condition`.
7. **Cadre légal et éthique strict** : L'exploitation des données de santé impose la conformité intégrale avec la **Loi n° 2019-014 relative à la protection des données à caractère personnel au Togo** et avec la **Convention de Malabo de l'Union Africaine**. Les principes de minimisation, de consentement, de pseudonymisation robuste et de traçabilité d'audit intégrale sont non négociables.

### 1.2 Postulat Fondamental, Éthique et Conformité Légale

Le projet repose sur un postulat technique et déontologique inviolable (`Definition  Projet.md`, ligne 25 ; `AGENT.md`, section 2, règle 8) :

> **« 100 % des données du projet sont synthétiques ou issues de jeux publics ouverts. Aucune donnée réelle de patient togolais n'est utilisée. »**

Toutes les cohortes cliniques, identités, séjours et consultations sont générés de manière algorithmique tout en reproduisant fidèlement les distributions épidémiologiques, démographiques et territoriales du Togo. Les données agrégées sont extraites de l'instance de démonstration publique officielle de DHIS2 (`https://play.dhis2.org/demo`). Si un fichier contenant des données réelles venait à être introduit dans le pipeline, les règles d'intégrité ordonnent l'interruption immédiate des opérations et la notification d'alerte.

### 1.3 Objectifs Primaires et Secondaires

#### Objectif Principal
Développer un pipeline de données automatisé, modulaire, déterministe et reproductible qui ingère des sources dégradées et hétérogènes de contexte togolais pour les transformer en :
1. Ressources **HL7 FHIR R4 (version 4.0.1)** validées et conformes à un profilage national togolais ;
2. Un entrepôt relationnel standardisé conforme au modèle de données commun **OMOP CDM 5.4** de la communauté OHDSI ;
3. Des jeux de données tabulaires analytiques au format **Apache Parquet (priorité absolue pour l'entraînement IA et l'analytique moderne)**, complétés par un **export miroir dénormalisé au format CSV (secondaire, pour interopérabilité statistique)**, pseudonymisés, typés et validés par contrats Pandera ;
4. Le tout avec une **traçabilité unitaire de bout en bout** permettant de relier chaque ressource générée à son enregistrement source d'origine.

#### Objectifs Secondaires
- **Alignement OpenHIE** : Démontrer l'intégration au sein d'une architecture OpenHIE (*Open Health Information Exchange*) articulant un Serveur FHIR opérationnel (HAPI FHIR JPA), une passerelle d'interopérabilité (OpenHIM), un Registre des Formations Sanitaires (*Facility Registry*), un Registre Client / Master Patient Index (*Client Registry* via Splink), et un Service Terminologique (*Terminology Service* via ConceptMaps FHIR).
- **Guide d'Implémentation FHIR Togo (IG)** : Définir formellement, compiler (via FHIR Shorthand / SUSHI) et publier un guide d'implémentation national avec profils, extensions (ex. précision de l'âge) et jeux de valeurs en français.
- **Transparence et Éthique IA** : Publier une **Fiche de Données (Datasheet)** accompagnant les exports Parquet, décrivant la genèse synthétique des données, les distributions réelles sous-jacentes, les biais introduits, les limites méthodologiques et les cas d'usage formellement déconseillés.

### 1.4 Périmètre Fonctionnel Formel (Inclusions et Exclusions)

Le périmètre du projet est strictement encadré par `Definition  Projet.md` (§5) et `AGENT.md` (§1) :

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  PÉRIMÈTRE INCLUS                                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Pathologies et domaines prioritaires (Togo) :                                        │
│   - Paludisme (formes simples et graves, pédiatrique, femme enceinte)                 │
│   - Infections respiratoires aiguës (IRA)                                             │
│   - Maladies diarrhéiques                                                              │
│   - VIH / SIDA (dépistage, suivi, lignes thérapeutiques ARV)                           │
│   - Tuberculose (dépistage, schéma thérapeutique)                                      │
│   - Maladies chroniques : Hypertension artérielle (HTA), Diabète                       │
│   - Santé maternelle et infantile (SMI) : consultations prénatales (CPN), accouchement │
│   - Vaccination : Programme Élargi de Vaccination (PEV Togo)                           │
│   - Malnutrition : aiguë, modérée, sévère                                              │
│ • Sources prises en charge :                                                           │
│   - DHIS2 (API dataValueSets démo publique)                                            │
│   - Fichiers Excel complexes (.xlsx / .xls, multi-onglets, cellules fusionnées)        │
│   - Extraits CSV de dossiers hospitaliers propriétaires simulés                        │
│   - Payloads et Bundles FHIR dégradés (erreurs de schémas, références orphelines)      │
│ • Cibles technologiques :                                                              │
│   - HAPI FHIR JPA R4 (4.0.1) sous OpenHIM                                              │
│   - OMOP CDM 5.4 (schéma relationnel avec vocabulaires Athena)                         │
│   - Apache Parquet (cible prioritaire IA/Lakehouse) & CSV dénormalisé (cible secondaire)│
│     avec validation stricte des schémas par Pandera                                    │
│ • Régime linguistique :                                                                │
│   - Français prioritaire pour la documentation, profils, libellés et ConceptMaps       │
│   - Identifiants de code (classes, fonctions, variables) en anglais                    │
│   - Documentation finale bilingue (Français d'abord, Anglais en miroir)                │
└────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  PÉRIMÈTRE EXCLU                                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ✕ Aucune interface utilisateur graphique (UI) : pas de portail web clinicien/patient   │
│ ✕ Aucune application clinique de saisie directe : le système est un moteur d'ingestion │
│ ✕ Aucun entraînement de modèles d'IA : livraison exclusive de jeux de données prêts    │
│ ✕ Aucun traitement en temps réel / streaming : traitement strict par lots (batch)      │
│ ✕ Aucune donnée réelle de patient : interdiction absolue de sources de production      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Technique et Pipeline de Données

### 2.1 Modèle Medallion Data Lakehouse Adapté à la Santé

Le pipeline adopte une architecture de type **Medallion Lakehouse**, segmentant le cycle de vie de la donnée en couches étanches et spécialisées. Chaque étape lit exclusivement la couche précédente et écrit dans la couche suivante, sans dépendance cyclique, garantissant que chaque composant peut être testé et réexécuté isolément.

```
+-----------------------------------------------------------------------------------------+
|                                    SOURCES HÉTÉROGÈNES                                   |
|   DHIS2 API (Agrégats)  |  Excel (Multi-feuilles)  |  CSV Cliniques  |  FHIR JSON Dégradé|
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v  [Étape 5 : Ingestion avec SHA-256]
+-----------------------------------------------------------------------------------------+
|  COUCHE RAW (data/raw/)                                                                 |
|  • Fichiers sources bit-à-bit strictement immuables (lecture seule absolue)              |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v  [Étape 5 : Structuration & Traçabilité]
+-----------------------------------------------------------------------------------------+
|  COUCHE BRONZE (data/bronze/)                                                            |
|  • Stockage Parquet typé avec 4 métadonnées obligatoires :                              |
|    - source_file (chemin relatif)    - ingested_at (horodatage UTC)                     |
|    - source_row (index de ligne)     - content_hash (empreinte SHA-256)                 |
+--------------------------------------------+--------------------------------------------+
                      |                      |
     [Échec lecture]  v                      v  [Étape 6 : Profilage Qualité Initial]
+--------------------------+                 |  [Étape 7 : Nettoyage & Normalisation YAML]
|  QUARANTAINE             |                 v
|  (data/quarantine/)      |   +----------------------------------------------------------+
|  • Rejets unitaires      |   |  COUCHE SILVER (data/silver/)                            |
|  • Code d'erreur codifié |   |  • Dates ISO 8601 & âges approximatifs avec indicateur   |
|  • Chemin du champ       |   |  • Normalisation noms/prénoms & adresses locales         |
|  • Contenu original brut |   |  • Unités cliniques UCUM & Libellés FR standardisés      |
|  • Zéro blocage du lot   |   |  • Valeurs sentinelles transformées en null explicite    |
+--------------------------+   |  • Journal exhaustif des modifications (audit trail)     |
              ^                +-----------------------------+----------------------------+
              |                                              |
              |                                              v  [Étape 8 : Splink MPI]
              |                                                 [Étape 9 : Modèle Canonique]
              |                +----------------------------------------------------------+
              +----------------+  MODÈLE CANONIQUE PYDANTIC (src/model/)                  |
              | (Erreur de     |  • Objets métiers stricts : Patient, Facility, Encounter,|
              |  validation)   |    Condition, Observation, Medication, Immunization      |
              |                +-----------------------------+----------------------------+
              |                                              |
              |                                              v  [Étape 10 : ConceptMaps]
              |                                                 [Étape 12 : Mapping FHIR R4]
              |                +----------------------------------------------------------+
              +----------------+  COUCHE GOLD FHIR (data/gold/fhir/)                      |
              | (Rejets HL7    |  • Bundles transactionnels ordonnés topologiquement      |
              |  Validator)    |  • Identifiants déterministes UUID v5                    |
              |                |  • Validés par HL7 Java Validator contre IG Togo         |
              |                +--------------+-----------------------------+-------------+
              |                               |                             |
              |                               v [Étape 14]                  v [Étape 15]
              |                +---------------------------+ +----------------------------+
              |                |  ARCHITECTURE OPENHIE     | |  ENTREPÔT OMOP CDM 5.4     |
              |                |  • Passerelle OpenHIM     | |  (PostgreSQL)              |
              |                |  • HAPI FHIR JPA (Docker) | |  • PERSON, VISIT, CONDITION|
              |                |  • Registres intégrés     | |  • Vocabulaires Athena     |
              |                +---------------------------+ +--------------+-------------+
              |                                                             |
              |                                                             v [Étape 17]
              |                                              +----------------------------+
              |                                              |  EXPORTS PARQUET POUR L'IA |
              |                                              |  • Tables aplaties séjour  |
              |                                              |  • Pseudonymisation salée  |
              |                                              |  • Validation Pandera      |
              |                                              |  • Datasheet éthique       |
              +----------------------------------------------+----------------------------+
```

### 2.2 Composants d'Infrastructure et Pile Logicielle

Le tableau suivant formalise la cartographie des composants technologiques, leurs versions cibles, leurs rôles et leurs justifications techniques :

| Composant | Technologie Spécifiée | Version Épinglée | Rôle dans l'Architecture | Justification Technique |
|---|---|---|---|---|
| **Runtime Principal** | Python | **3.11.x** | Cœur d'exécution du pipeline et de la CLI | Stabilité et compatibilité maximale avec l'écosystème de santé (`fhir.resources`, `splink`, `duckdb`). |
| **Gestionnaire de Dépendances** | `uv` / `pyproject.toml` | Dernier standard | Résolution et verrouillage des paquets | Déterminisme strict via `uv.lock`, rapidité d'installation, gestion native des versions Python. |
| **Ingestion Tabulaire** | Pandas / PyArrow | Latest stable | Lecture des fichiers Excel et CSV hétérogènes | Tolérance aux feuilles multiples, inférence robuste de types et conversion mémoire vers Parquet. |
| **Moteur SQL Analytique** | **DuckDB** | Latest stable | Moteur relationnel in-process et jointures | Exécution SQL analytique ultra-rapide directement sur fichiers Parquet, sans dépendance de serveur lourd. |
| **Validation Structurée** | **Pydantic** | **>= 2.6.0** | Validation du Modèle Canonique intermédiaire | Typage strict à l'exécution, messages d'erreurs codifiés en cas d'invalidation, sérialisation JSON fluide. |
| **Rapprochement d'Identités** | **Splink** | Latest (backend DuckDB)| Résolution probabiliste d'entités (MPI) | Modèle de Fellegi-Sunter sans dépendance de cluster Spark lourd, règles de blocage optimisées pour l'onomastique togolais. |
| **Similarité Textuelle** | RapidFuzz | Latest (backend C++) | Rapprochement flou des noms de centres et libellés | Calcul de distance de Levenshtein / Jaro-Winkler performant pour l'alignement sur les référentiels. |
| **Modèles FHIR Python** | `fhir.resources` | **7.1.0** (spécifique R4) | Sérialisation et validation objet FHIR R4 | Évite toute dérive vers FHIR R4B ou R5, garantit la conformité stricte avec la norme 4.0.1. |
| **Guide d'Implémentation** | SUSHI / FSH & IG Publisher | Latest npm / Java | Modélisation et compilation de l'IG Togo | Syntaxe déclarative concise (FHIR Shorthand), compilation automatisée en StructureDefinitions JSON. |
| **Validation Officielle HL7** | HL7 Java Validator | `validator_cli.jar` | Contrôle officiel de conformité de l'IG | Validateur de référence international HL7 exécuté en sous-processus Docker/JVM. |
| **Serveur FHIR** | **HAPI FHIR JPA** | Image Docker officielle | Entrepôt opérationnel FHIR R4 | Référence mondiale open-source pour le stockage, la recherche et le traitement de Bundles transactionnels. |
| **Base Relationnelle** | PostgreSQL | 15+ Docker | Persistance de HAPI FHIR et d'OMOP CDM | RDBMS robuste, éprouvé pour les gros volumes transactionnels et requis nativement par OHDSI. |
| **Passerelle Interopérabilité**| **OpenHIM Core & Console** | Images Docker officielles | Proxy sécurisé, routage et audit OpenHIE | Chiffrement TLS, authentification des flux inter-applicatifs, traçabilité des échanges de santé. |
| **Entrepôt Analytique OMOP**| OMOP CDM 5.4 | DDL officiel OHDSI | Modèle commun pour la recherche clinique | Format standard international pour les études observationnelles et l'entraînement d'IA en santé. |
| **Vocabulaires Médicaux** | OHDSI Athena | Release officielle | Dictionnaire terminologique unifié | Correspondance entre concepts sources et concepts standards internationaux (SNOMED, RxNorm, LOINC). |
| **Qualité OMOP** | Achilles & DQD | R packages (Docker) | Profilage statistique et vérification qualité | Data Quality Dashboard officiel d'OHDSI évaluant la plausibilité, la complétude et la conformité. |
| **Validation Schémas IA** | Pandera | Latest stable | Validation des schémas de données Parquet | Vérification stricte des distributions, plages de valeurs, types et absence de données manquantes critiques. |
| **Interface en Ligne de Commande**| Typer & Rich | Latest stable | CLI unifiée avec une commande par étape | Expérience développeur ergonomique, typage strict des arguments CLI, affichage d'avancement clair. |
| **Assurance Qualité Code** | Pytest, Ruff, Pre-commit | Latest stable | Linting, formatage et tests automatisés | Temps de lint quasi-instantané avec Ruff, tests TDD rigoureux (nominaux, limites, idempotence). |

### 2.3 Principes Inviolables d'Intégrité Opérationnelle

Conformément à la charte d'ingénierie (`AGENT.md`, §2) et aux spécifications (`Definition  Projet.md`, §7), le pipeline observe 8 principes intangibles :

1. **Immuabilité absolue des données brutes** : Le répertoire `data/raw/` est sanctuarisé en lecture seule. Aucune commande, aucun script et aucun agent n'est autorisé à modifier, renommer, écraser ou corriger un fichier source brut.
2. **Traçabilité totale et unitaire** : Toute entité produite à partir de la couche Bronze conserve quatre attributs d'audit : `source_file` (chemin du fichier d'origine), `source_row` (numéro de ligne ou identifiant source), `ingested_at` (horodatage UTC d'ingestion), et `content_hash` (empreinte cryptographique SHA-256 de la ligne source).
3. **Idempotence stricte et déterminisme par UUID v5** : L'exécution répétée du pipeline ou d'une étape sur les mêmes données produit un résultat strictement identique au bit près. Les identifiants de ressources FHIR sont obligatoirement calculés sous forme d'**UUID v5** dérivés d'un espace de noms (*namespace*) UUID fixe et de l'identifiant source (`source_file:source_row` ou ID métier). Tout appel à `uuid.uuid4()`, à l'horloge système non maîtrisée (`datetime.now()`) ou à des générateurs aléatoires sans graine fixe est formellement banni de la logique métier.
4. **Isolation étanche des couches** : Chaque étape est encapsulée, lit une couche clairement délimitée, écrit dans la suivante, et doit pouvoir être relancée de manière autonome sans état caché.
5. **Interdiction absolue des décisions cliniques silencieuses** : Aucun mapping terminologique ambigu ou score de similarité situé sous le seuil d'admissibilité ne peut être deviné ou validé automatiquement par le système. Tout enregistrement incertain reçoit le statut `"à revoir"` et est dirigé vers la file d'attente d'arbitrage humain (`docs/journal/A_VALIDER.md`). Il est formellement interdit d'inventer un code médical.
6. **Journalisation exhaustive de toute altération** : Aucune donnée n'est transformée ou corrigée sans génération d'une entrée de journal structurée consignant : champ modifié, ancienne valeur, nouvelle valeur, règle de transformation appliquée et justification.
7. **Quarantaine explicite (Zéro suppression silencieuse)** : Tout enregistrement corrompu, syntaxiquement invalide ou non conforme aux profils est consigné dans `data/quarantine/` avec un motif d'erreur normalisé, la localisation exacte du problème (JSONPath ou nom de colonne) et le contenu d'origine, sans provoquer l'arrêt brutal du traitement du lot (*fail-safe batch processing*).
8. **Mesurabilité objective et testabilité complète** : Chaque règle de normalisation possède un test unitaire nominal, un test de cas limite (*edge case*), un test d'idempotence et une métrique de qualité associée. Les chiffres de qualité publiés sont issus d'exécutions réelles et reproductibles, jamais estimés ou rédigés manuellement.

---

## 3. Spécification des Étapes du Pipeline (Roadmap Technique 0 à 21)

### 3.1 Découpage Général et Enchaînement Séquentiel

La feuille de route technique s'articule en **22 étapes séquentielles** (numérotées de 0 à 21). Chaque étape ne peut être engagée que si les critères de validation stricts de l'étape précédente ont été mesurés et validés.

```
Socle & Référentiels      Vérité Terrain & Ingestion     Nettoyage & Modèle           Standardisation & Cibles
┌───────────────────┐    ┌─────────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│ Étape 0 : Socle   │    │ Étape 3 : Vérité Terrain│    │ Étape 7 : Nettoyage   │    │ Étape 11 : Guide IG   │
│ Étape 1 : Infra   │───>│ Étape 4 : Dégradation   │───>│ Étape 8 : Splink MPI  │───>│ Étape 12 : FHIR R4    │
│ Étape 2 : Référent│    │ Étape 5 : Ingestion     │    │ Étape 9 : Modèle Cano │    │ Étape 13 : Valid. HL7 │
└───────────────────┘    │ Étape 6 : Profilage Init│    │ Étape 10 : Termino    │    │ Étape 14 : OpenHIE    │
                         └─────────────────────────┘    └───────────────────────┘    │ Étape 15 : OMOP CDM   │
                                                                                     │ Étape 16 : Qualité DQD│
                                                                                     │ Étape 17 : Exports IA │
                                                                                     │ Étape 18 : Rapport A/A│
                                                                                     │ Étape 19 : Sécurité   │
                                                                                     │ Étape 20 : CI/CD E2E  │
                                                                                     │ Étape 21 : Publication│
                                                                                     └───────────────────────┘
```

### 3.2 Spécification Détaillée des 22 Étapes

#### Étape 0 : Cadrage, Arborescence et Initialisation du Dépôt *(Étape de socle à formaliser)*
- **Objectifs** : Traiter les arbitrages utilisateurs, unifier la gestion de paquets sous `uv` avec `pyproject.toml`, déployer l'arborescence des répertoires prescrits par `AGENT.md`, renommer `Definition  Projet.md` en `definition_projet.md`, rédiger un `README.md` introductif bilingue, et initialiser les registres de mémoire (`docs/journal/`).
- **Validation** : Arborescence complète instanciée, `uv sync` fonctionnel sur environnement Python 3.11, premier commit git effectué sur la branche principale.

#### Étape 1 : Environnement et Outillage
- **Objectifs** : Rédiger le fichier `docker-compose.yml` orchestrant HAPI FHIR JPA, PostgreSQL et OpenHIM. Instancier le squelette de la CLI Typer dans `src/cli.py` prévoyant un sous-groupe de commandes par étape de pipeline. Configurer Ruff, Pytest, les hooks de pre-commit et le workflow d'intégration continue GitHub Actions.
- **Validation** : `docker compose up` démarre les services sans conflit de port ; la requête HTTP `GET http://localhost:8080/fhir/metadata` renvoie une ressource `CapabilityStatement` FHIR R4 valide ; la suite de tests triviale et le lint Ruff passent au vert en CI.

#### Étape 2 : Référentiels du Contexte Togolais
- **Objectifs** : Modéliser le référentiel territorial et sanitaire du Togo (6 régions sanitaires, 39 à 44 districts sanitaires, hôpitaux, CMS et USP) à partir des données publiques DHIS2 et des nomenclatures officielles (ou générer un référentiel synthétique cohérent clairement étiqueté). Définir le document d'architecture des systèmes d'URI du projet (systèmes d'identifiants patients, CodeSystems locaux, URIs d'organisations). Établir le catalogue des pathologies prioritaires togolaises avec leur cartographie cible (CIM-10, SNOMED CT, LOINC, ATC).
- **Validation** : Tables Parquet de référence générées ; chaque structure possède un identifiant unique immuable et une hiérarchie administrative complète ; absence totale de doublon sur les libellés normalisés.

#### Étape 3 : Génération des Données « Vérité Terrain »
- **Objectifs** : Produire une cohorte de référence parfaite (*Ground Truth*) exempte d'erreurs :
  - *Voie A* : Génération d'une population de base via Synthea (graine fixe), suivie d'un script de localisation supprimant les profils US Core et substituant les patronymes, adresses et prévalences par les réalités togolaises.
  - *Voie B* : Développement d'un générateur contextuel Python produisant directement des parcours cliniques complets (patients, consultations, diagnostics, constantes, prescriptions, vaccins, grossesses) selon les distributions épidémiologiques du Togo.
  - *Agrégats* : Extraction des jeux de données de statistiques mensuelles de l'instance démo publique DHIS2 (`dataValueSets`).
- **Validation** : Les données produites valident à 100 % contre les validateurs FHIR ; deux générations successives avec la même graine produisent des fichiers identiques au bit près.

#### Étape 4 : Moteur de Dégradation Contrôlée
- **Objectifs** : Développer un moteur d'altération paramétré injectant des anomalies réalistes dans la vérité terrain selon un catalogue d'erreurs versionné : dates en formats disparates, âges approximatifs textuels, variantes orthographiques et accents omis, libellés cliniques en français libre ou abrégé, séparateurs décimaux mixtes, doublons inter-établissements de patients, valeurs sentinelles (`-1`, `999`, `NA`), encodages corrompus, cellules Excel fusionnées, et références FHIR orphelines. Générer pour chaque lot le **journal d'altérations** (*corrigé* exhaustif).
- **Validation** : Le taux d'erreur mesuré dans les données dégradées correspond aux paramètres fixés à plus ou moins une marge d'erreur définie ; le journal d'altérations permet de recalculer l'original.

#### Étape 5 : Ingestion (Raw et Bronze)
- **Objectifs** : Développer un module d'ingestion spécialisé par format source (classeurs Excel multi-onglets, CSV à encodages multiples avec détection automatique `chardet`, JSON/Bundles FHIR bruts, flux d'API DHIS2). Copier les sources à l'identique dans `data/raw/` (lecture seule). Structurer les tables dans `data/bronze/` au format Parquet en ajoutant les 4 colonnes techniques (`source_file`, `source_row`, `ingested_at`, `content_hash` SHA-256). Isoler les fichiers physiquement corrompus dans `data/quarantine/`.
- **Validation** : Le comptage de lignes Bronze est égal au comptage de lignes sources ; le processus est idempotent ; un fichier corrompu n'arrête pas le lot.

#### Étape 6 : Profilage et Diagnostic Initial
- **Objectifs** : Évaluer automatiquement la qualité de la couche Bronze sur 6 dimensions normatives : complétude, exactitude, cohérence, unicité, validité, actualité. Détecter les valeurs aberrantes, formats non conformes et doublons probables. Générer automatiquement le rapport de qualité initial (*« Rapport Avant »*).
- **Validation** : Le rapport détecte les erreurs injectées à l'étape 4 avec un score de rappel mesuré et comparé au corrigé du journal d'altérations.

#### Étape 7 : Nettoyage et Normalisation (Silver)
- **Objectifs** : Appliquer une suite de règles de nettoyage déclaratives définies dans des fichiers de configuration YAML : standardisation des dates au format ISO 8601, déduction des dates de naissance pour les âges approximatifs avec flag `estimated_age_flag`, normalisation des patronymes togolais (conservation de la valeur brute originale dans `original_raw_name`), conversion des unités vers le standard UCUM, harmonisation des libellés français, réconciliation des formations sanitaires par similarité floue RapidFuzz (avec bascule en revue humaine si score < seuil), et conversion des sentinelles en `NULL`.
- **Validation** : Chaque règle possède sa suite de tests unitaires dédiés ; amélioration mesurée sur les 6 dimensions du rapport de qualité ; zéro modification de valeur sans trace dans le journal d'audit des transformations.

#### Étape 8 : Rapprochement des Patients (Master Patient Index - Splink)
- **Objectifs** : Configurer et calibrer un modèle probabiliste de rapprochement d'identités (Splink sur DuckDB) utilisant des règles de blocage (phonétique locale, région sanitaire, année de naissance approchée). Fixer trois seuils stricts : fusion automatique, revue manuelle (`docs/journal/A_VALIDER.md`), enregistrements distincts. Calculer un identifiant patient maître déterministe et une table de liaison sans jamais écraser les identifiants locaux sources.
- **Validation** : Précision et rappel calculés contre les doublons réels connus de l'étape 4 ; matrice de confusion publiée ; zéro fusion de dossiers présentant des sexes incompatibles.

#### Étape 9 : Pivot vers le Modèle Canonique
- **Objectifs** : Définir formellement les entités métiers en classes Pydantic v2 strictes (Patient, Structure, Consultation, Diagnostic, Examen, Médicament, Vaccination, Grossesse, Indicateur agrégé) avec héritage des attributs de traçabilité. Implémenter les modules de transformation de la couche Silver vers ce modèle intermédiaire unifié.
- **Validation** : 100 % des enregistrements retenus sont validés par les validateurs Pydantic ; les enregistrements rejetés sont dirigés en quarantaine avec codes d'erreur codifiés.

#### Étape 10 : Service Terminologique et ConceptMaps FHIR
- **Objectifs** : Charger dans DuckDB les nomenclatures CIM-10 (version française ouverte), LOINC, ATC et les vocabulaires Athena. Mettre en place un moteur de correspondance à 3 niveaux : correspondance exacte, correspondance approchée RapidFuzz avec seuil, et revue manuelle obligatoire sous le seuil. Exposer les tables de correspondances sous forme de ressources `ConceptMap` et `ValueSet` FHIR R4 réutilisables.
- **Validation** : Taux d'alignement publié par domaine clinique ; échantillon audité manuellement ; 100 % des correspondances consignent la méthode, le score et le statut (validé / à revoir) ; aucune promotion automatique de code incertain.

#### Étape 11 : Guide d'Implémentation FHIR « Togo » (IG)
- **Objectifs** : Rédiger en FHIR Shorthand (FSH) dans le dossier `ig/` la spécification formelle des profils nationaux togolais complets :
  - `TogoPatient` (données administratives, identifiants décentralisés, précision d'âge) ;
  - `TogoEncounter` (consultations externes, hospitalisations, centres périphériques) ;
  - `TogoCondition` (diagnostics, pathologies prioritaires codées en CIM-10 / SNOMED CT) ;
  - `TogoObservation` (constantes vitales, signes cliniques, résultats d'examens biologiques) ;
  - `TogoProcedure` (actes médico-chirurgicaux, accouchements, interventions de SMI) ;
  - `TogoMedicationRequest` (prescriptions, protocoles antipaludiques, antirétroviraux, antituberculeux) ;
  - `TogoImmunization` (vaccinations du PEV Togo, numéros de lots, calendrier vaccinal) ;
  - `TogoLocation` (formations sanitaires, niveaux de la pyramide sanitaire) ;
  - `TogoOrganization` (districts sanitaires, directions régionales de la santé).
  Définir les extensions requises (indicateur d'âge approximatif, modalité de consentement). Compiler l'IG avec SUSHI (via conteneur Docker dédié) et publier la documentation HTML via l'IG Publisher HL7.
- **Validation** : L'IG se compile avec 0 erreur bloquante ; les ressources synthétiques de la vérité terrain valident intégralement contre l'ensemble des profils nationaux générés.

#### Étape 12 : Transformation vers FHIR R4
- **Objectifs** : Développer les fonctions de transformation du Modèle Canonique vers les ressources FHIR R4 (utilisant `fhir.resources` épinglé R4). Dériver les identifiants FHIR déterministes par UUID v5. Résoudre les références inter-ressources à partir de l'index des identifiants. Convertir les agrégats DHIS2 en ressources `MeasureReport` (interdiction formelle de créer des ressources `Patient` sur des agrégats). Assembler les ressources au sein de Bundles de transaction ordonnés selon l'arbre des dépendances topologiques.
- **Validation** : 100 % des ressources produites valident structurellement avec `fhir.resources` ; zéro référence brisée ; reproductibilité idempotente garantie.

#### Étape 13 : Validation Officielle HL7 et Quarantaine
- **Objectifs** : Exécuter le validateur officiel HL7 Java (`validator_cli.jar`) en sous-processus contre l'ensemble des Bundles transactionnels générés, en appliquant les profils nationaux de l'IG Togo. Trier les retours en trois catégories (Error, Warning, Information). Écarter les ressources en erreur vers `data/quarantine/` avec journalisation du chemin JSON exact et du message du validateur. Produire le registre officiel des rejets.
- **Validation** : Zéro ressource en erreur dans la couche Gold finale ; chaque rejet est documenté et justifié ; taux de récupération calculé contre la vérité terrain.

#### Étape 14 : Déploiement et Intégration OpenHIE (OpenHIM & HAPI FHIR)
- **Objectifs** : Configurer la passerelle d'interopérabilité OpenHIM (définition des canaux, gestion des certificats, authentification, traçabilité des transactions). Charger séquentiellement sur HAPI FHIR JPA les ressources validées (d'abord Organisations et Lieux, puis Patients, puis Épisodes, Diagnostics, Actes cliniques et Traitements) via des transactions HTTP routées par OpenHIM. Implémenter les rôles OpenHIE (Facility Registry, Client Registry, Terminology Service, Shared Health Record).
  - *Gestion du périmètre DHIS2* : Brancher DHIS2 en source d'agrégats via son API publique de démonstration. Pour le volet « destination », générer et valider les payloads d'exportation d'indicateurs de santé publique conformes à la structure ADX / JSON `dataValueSets` de DHIS2. Étant donné le caractère éphémère et réinitialisé de l'instance publique `play.dhis2.org/demo`, la validation en destination repose sur un test d'intégration mocké simulant l'API d'ingestion DHIS2 sans dépendre de la persistance externe.
- **Validation** : Tests d'intégration automatisés validant les recherches FHIR, la lecture unitaire, la protection contre les accès non authentifiés (erreurs 401/403 hors OpenHIM), l'idempotence des transactions répétées et la conformité schématique des payloads d'indicateurs DHIS2 exportés.

#### Étape 15 : ETL FHIR vers OMOP CDM 5.4
- **Objectifs** : Initialiser le schéma OMOP CDM 5.4 sur base PostgreSQL et charger les vocabulaires standard Athena. Développer le moteur d'extraction et de chargement (ETL) transformant les ressources FHIR validées en tables relationnelles OMOP :
  - `Patient` $\rightarrow$ `PERSON` ;
  - `Encounter` $\rightarrow$ `VISIT_OCCURRENCE` ;
  - `Condition` $\rightarrow$ `CONDITION_OCCURRENCE` ;
  - `Observation` $\rightarrow$ `MEASUREMENT` (constantes et résultats chiffrés) et `OBSERVATION` (signes qualitatifs) ;
  - `Procedure` (actes cliniques et chirurgicaux) $\rightarrow$ `PROCEDURE_OCCURRENCE` ;
  - `MedicationRequest` $\rightarrow$ `DRUG_EXPOSURE` ;
  - `Immunization` $\rightarrow$ `DRUG_EXPOSURE` (concept d'ingrédient vaccinal standard, concept d'administration `32827 - EHR encounter record`, avec tracé du geste technique dans `PROCEDURE_OCCURRENCE` si codifié) ;
  - `Organization` / `Location` $\rightarrow$ `CARE_SITE` et `LOCATION`.
  - *Ségrégation stricte des données agrégées* : Les indicateurs agrégés de santé publique DHIS2 (`MeasureReport`) ne possèdent pas de correspondance unitaire patient et **sont formellement exclus des tables cliniques OMOP CDM**. Ils sont cantonnés dans FHIR et dans les tables Parquet analytiques de santé publique.
  - Conserver impérativement les codes et libellés sources dans les colonnes `*_source_value`. Assigner le concept standard `0` aux codes non alignés sans jamais masquer leur présence.
- **Validation** : Intégrité référentielle complète du schéma relationnel OMOP ; concordance exacte des volumétries avec les données FHIR individuelles sources ; zéro indicateur agrégé dans la table `PERSON` ; publication du taux de concept `0` par table clinique.

#### Étape 16 : Contrôle Qualité OHDSI (Achilles et Data Quality Dashboard)
- **Objectifs** : Exécuter les outils officiels de la communauté OHDSI (paquetages R Achilles et Data Quality Dashboard) sur l'entrepôt OMOP CDM 5.4. Évaluer systématiquement les règles de plausibilité, de complétude et de conformité du modèle.
- **Validation** : Rapport DQD généré et publié ; taux de conformité global documenté ; analyse et justification unitaire de chaque test DQD en échec.

#### Étape 17 : Exports Analytiques Parquet pour l'IA et Datasheet
- **Objectifs** : Générer des tables analytiques dénormalisées au format Parquet optimisées pour le Machine Learning (table aplatie par séjour/patient regroupant caractéristiques sociodémographiques, antécédents, diagnostics et constantes biologiques). Appliquer une pseudonymisation robuste par hachage cryptographique salé des identifiants et généralisation k-anonymat des variables quasi-identifiantes (dates et lieux). Valider les schémas via Pandera. Rédiger la **Fiche de Données (Datasheet)** documentant la provenance synthétique, les biais connus, les limites méthodologiques et les usages formellement proscrits.
- **Validation** : Schémas Parquet conformes aux contrats Pandera ; tests de non-régression prouvant l'absence de toute fuite d'identifiant direct ou variable cible (*data leakage*) ; Datasheet complète et validée.

#### Étape 18 : Rapport d'Impact Comparatif Avant / Après
- **Objectifs** : Développer un générateur automatisé produisant le rapport d'impact global mesurant les gains de qualité entre la couche Bronze dégradée et les couches finales Gold (FHIR / OMOP / Parquet) : gains de complétude, taux d'exactitude recouvrée, statistiques de rejets en quarantaine par motif, performance de déduplication Splink et couverture des mappings terminologiques.
- **Validation** : Le rapport complet (Markdown et HTML) se régénère de manière totalement automatisée et déterministe via une commande unique de la CLI.

#### Étape 19 : Audit de Sécurité et Note de Conformité Légale
- **Objectifs** : Réaliser un audit de sécurité complet du dépôt (recherche de secrets, vérification de l'absence de jetons ou mots de passe, gestion étanche des fichiers `.env` et `.env.example`). Rédiger une note formelle d'analyse juridique et de conformité évaluant les mesures prises au regard de la **Loi n° 2019-014 du Togo** sur la protection des données personnelles, du **RGPD** et de la **Convention de Malabo de l'Union Africaine**.
- **Validation** : Outil de détection de secrets (ex. `trufflehog` ou `git-secrets`) passant sans la moindre alerte en CI ; note de conformité rédigée et intégrée dans `docs/fr/conformite_legale.md`.

#### Étape 20 : Tests de Propriétés et Intégration Continue (CI/CD)
- **Objectifs** : Consolider la suite de tests automatisés : tests unitaires couvrant chaque fonction de nettoyage et de mapping, tests de propriétés (vérification de l'idempotence et du déterminisme strict sur exécutions multiples), tests de non-régression, et test d'intégration de bout en bout (E2E) exécutant l'ensemble de la chaîne du raw jusqu'aux exports Parquet sur une cohorte synthétique de 100 patients.
- **Validation** : Pipeline GitHub Actions intégralement vert ; exécution réussie du test E2E 100 patients en CI ; couverture de tests mesurée et conforme aux exigences.

#### Étape 21 : Documentation Finale et Publication
- **Objectifs** : Rédiger la documentation de clôture du projet : `README.md` bilingue (français d'abord, anglais en miroir) comportant le schéma d'architecture complet, les résultats chiffrés, le guide de reproduction en une commande unique Docker ; documentation technique exhaustive des règles de mapping et d'ingénierie ; publication du Guide d'Implémentation FHIR via GitHub Pages ; formalisation des licences (licence open-source pour le code, licence ouverte pour les données synthétiques).
- **Validation** : Un utilisateur extérieur, sans connaissance préalable du projet, est capable de cloner le dépôt et d'exécuter avec succès le pipeline complet en suivant exclusivement les instructions du `README.md`.

---

## 4. État des Lieux Actuel du Dépôt et Diagnostic d'Environnement

L'inspection factuelle du système hôte et des fichiers de travail met en lumière un décalage substantiel entre l'ambition des spécifications documentaires et l'état réel d'initialisation du dépôt.

### 4.1 Diagnostic Factuel des Fichiers du Dépôt

| Fichier / Répertoire | Taille Physique | Nombre de Lignes | Diagnostic et Écart Constaté |
|---|---|---|---|
| `/home/bi2l/projet/fhir-pipeline/README.md` | **0 octet** | 0 ligne | **Anomalie critique** : Le fichier d'accueil du dépôt est strictement vide. Il ne contient aucune mention du projet, aucune instruction d'installation, ni la description obligatoire exigée par `Definition  Projet.md` (§8). |
| `/home/bi2l/projet/fhir-pipeline/requirements.txt` | **0 octet** | 0 ligne | **Vide** : Aucune dépendance Python n'est déclarée. |
| `/home/bi2l/projet/fhir-pipeline/.env.example` | **0 octet** | 0 ligne | **Vide** : Aucun modèle de configuration d'environnement n'est fourni. |
| `/home/bi2l/projet/fhir-pipeline/.env` | **0 octet** | 0 ligne | **Vide** : Fichier local non initialisé. |
| `/home/bi2l/projet/fhir-pipeline/pyproject.toml` | *Inexistant* | - | **Absent** : Le fichier de configuration canonique exigé tant par `AGENT.md` que par `technique.md` n'existe pas encore à la racine. |
| `/home/bi2l/projet/fhir-pipeline/Definition  Projet.md` | 5 746 octets | 71 lignes | **Présent avec anomalie typographique** : Comporte une double espace dans son nom de fichier. Document de cadrage métier de référence. |
| `/home/bi2l/projet/fhir-pipeline/AGENT.md` | 13 610 octets | 307 lignes | **Présent** : Charte d'ingénierie normative très complète et directive. |
| `/home/bi2l/projet/fhir-pipeline/technique.md` | 14 334 octets | 156 lignes | **Présent** : Spécification technique et feuille de route détaillée. |
| `/home/bi2l/projet/fhir-pipeline/.gitignore` | 12 octets | 3 lignes | **Présent mais minimaliste** : Exclut uniquement `.venv/` et `.env`. Doit être enrichi pour exclure les caches (`__pycache__`, `.pytest_cache`, `.duckdb`, etc.). |
| **Dépôt Git (`.git/`)** | - | 0 commit | **Branche master vierge** : La commande `git log` échoue (`fatal: your current branch 'master' does not have any commits yet`). Aucun historique de versionnement n'a été initialisé. |
| **Arborescence du Code (`src/`, `data/`, etc.)** | *Inexistante* | - | Les répertoires prescrits (`src/`, `config/`, `data/`, `tests/`, `docs/`, `terminology/`, `ig/`) ne sont pas créés. Le dépôt est au stade de pré-développement strict. |

### 4.2 Diagnostic de l'Environnement Système Hôte

L'interrogation directe de la machine Linux (`bi2l`) révèle plusieurs discordances d'infrastructure matérielle et logicielle :

```bash
$ python3 --version
Python 3.15.0

$ which python3.11
which: no python3.11 in (/home/bi2l/.gemini/antigravity-cli/bin:/usr/local/bin:/usr/bin:...)

$ which uv
which: no uv in (/home/bi2l/.gemini/antigravity-cli/bin:/usr/local/bin:/usr/bin:...)

$ which node
which: no node in (/home/bi2l/.gemini/antigravity-cli/bin:/usr/local/bin:/usr/bin:...)

$ java -version
openjdk version "25.0.4.1" 2026-08-18
OpenJDK Runtime Environment (Red_Hat-25.0.4.1.1-1) (build 25.0.4.1+1)

$ docker --version
Docker version 29.9.3, build 5457199

$ docker info
Cannot connect to the Docker daemon at unix:///home/bi2l/.docker/desktop/docker.sock. Is the docker daemon running?
```

#### Analyse d'impact des constats d'environnement :
1. **Écart de version Python (Python 3.15.0 hôte vs Python 3.11 requis)** : Les spécifications exigent expressément **Python 3.11**. Or, l'interpréteur système par défaut et l'environnement virtuel local (`.venv`) tournent actuellement sous **Python 3.15.0** (une version expérimentale / future non stabilisée dans l'écosystème open-source). De nombreuses dépendances critiques en data science et santé (notamment les extensions C/Rust de `DuckDB`, `PyArrow`, `Splink`, `Pandera` ou `fhir.resources`) ne disposent pas de *wheels* binaires précompilées pour Python 3.15 et échoueront à la compilation.
2. **Absence de l'outil `uv`** : Bien qu'`AGENT.md` prescrive la gestion des dépendances via `uv`, l'exécutable n'est pas présent dans le système.
3. **Absence de Node.js** : La commande `node` est absente de la machine. Cela bloque l'exécution locale de l'outil **SUSHI** (`fsh-sushi`), requis à l'Étape 11 pour compiler le Guide d'Implémentation FHIR.
4. **Démon Docker arrêté** : Bien que le client Docker 29.9.3 soit installé, le service Docker Desktop / démon n'est pas actif à cet instant, empêchant le démarrage des conteneurs HAPI FHIR, PostgreSQL et OpenHIM.

---

## 5. Audit de Cohérence et Matrice des Discordances Inter-Documentaires

L'audit croisé approfondi mené sur `AGENT.md`, `Definition  Projet.md`, `technique.md` et les retours d'investigation révèle **18 anomalies, contradictions ou zones de sous-spécification**.

### 5.1 Matrice d'Analyse des 18 Anomalies, Incohérences et Omissions Détectées

| N° | Sujet / Domaine | Description de la Discordance | Sources Documentaires en Conflit | Criticité | Impact Opérationnel |
|---|---|---|---|---|---|
| **1** | **Gestionnaire de dépendances Python** | `technique.md` prescrit `pip`, tandis qu'`AGENT.md` impose `uv`. Le dépôt contient un `requirements.txt` vide sans `pyproject.toml`, et `uv` n'est pas installé sur l'hôte. | `technique.md:7` vs `AGENT.md:47` | **Élevée** | Risque d'échec immédiat des scripts d'installation, absence de lockfile reproductible, divergence d'outillage entre agents. |
| **2** | **Version de l'interpréteur Python** | `AGENT.md` et `technique.md` imposent formellement Python 3.11. L'environnement local hôte tourne sous Python 3.15.0 et `python3.11` est absent du PATH. | `technique.md:7`, `AGENT.md:47` vs Environnement Hôte | **Bloquante** | Incompatibilité de compilation binaire des packages scientifiques (`DuckDB`, `Pandas`, `Splink`, `PyArrow`). |
| **3** | **Numérotation de la Roadmap (Étape 0)** | `AGENT.md` indique que la roadmap comprend les « étapes 0 à 21 ». Or, `technique.md` commence directement à l'« Étape 1 ». L'Étape 0 n'existe nulle part. | `AGENT.md:21` vs `technique.md:16` | **Moyenne** | Impossibilité pour l'agent Coordinateur de formaliser des fiches de tâches conformes (`T-0-xx`) pour les travaux de setup initial. |
| **4** | **Stratégie de Vérité Terrain (Voie A vs B)** | `technique.md` présente la voie Synthea et le générateur Python comme deux options alternatives (« Voie A », « Voie B »). `Definition  Projet.md` exige « Les deux ». | `Definition  Projet.md:51` vs `technique.md:32-35` | **Moyenne** | Dispersion de l'effort d'ingénierie : customiser Synthea en Java pour le Togo représente une charge colossale face au générateur Python. |
| **5** | **Langue des sous-paquets `src/`** | `AGENT.md` exige que les identifiants de code soient en anglais (l.17), mais liste les sous-dossiers de `src/` en français (`nettoyage`, `rapprochement`, etc., l.69). | `AGENT.md:17` vs `AGENT.md:69-71` | **Moyenne** | Conflit de convention Python : les noms de dossiers sous `src/` sont des modules importables en code (`import src.nettoyage`). |
| **6** | **Anomalie typographique du nom de fichier** | Le fichier de cadrage s'intitule physiquement `'Definition  Projet.md'` avec deux espaces consécutifs entre les mots. | Fichier sur le système de fichiers hôte | **Faible** | Fragilité dans les scripts shell, Dockerfiles, Makefiles et pipelines CI en cas d'omission des guillemets d'échappement. |
| **7** | **SGBD d'hébergement pour OMOP CDM 5.4** | Le stockage analytique est confié à DuckDB, mais l'Étape 16 exige l'exécution d'Achilles et DQD (en R OHDSI). Le rôle de PostgreSQL pour OMOP n'est pas explicité. | `technique.md:9,125,130` vs `AGENT.md:55` | **Élevée** | OHDSI DatabaseConnector supporte mal DuckDB pour Achilles/DQD ; PostgreSQL conteneurisé est impératif pour faire tourner la suite OHDSI standard. |
| **8** | **Modalité d'intégration d'OpenHIM en batch** | Le projet exclut le temps réel et fonctionne par lots CLI. OpenHIM est pourtant prévu avec canaux et authentification devant HAPI FHIR. | `Definition  Projet.md:46` vs `technique.md:18,117` | **Moyenne** | Flou architectural : la CLI doit-elle poster ses Bundles sur le port OpenHIM (reverse proxy) ou directement sur l'API HAPI FHIR ? |
| **9** | **Poids et licences des terminologies (Athena/SNOMED)** | `AGENT.md` interdit les dépendances réseau et impose des jeux de test < 1 Mo. Or, Athena et CIM-10/SNOMED complets pèsent plusieurs Go et requièrent des licences. | `AGENT.md:123` vs `technique.md:26,91,125` | **Élevée** | Impossibilité de versionner les bases terminologiques complètes dans git. Nécessite un sous-ensemble minimaliste (*mock*) pour les tests. |
| **10** | **Vacuité des fichiers d'accueil du dépôt** | `README.md`, `requirements.txt`, `.env.example` sont à 0 octet et aucun code source n'est présent. | Système de fichiers du dépôt | **Moyenne** | Aucune documentation d'accueil immédiatement utilisable pour un tiers clonant le projet à cet instant. |
| **11** | **Dualité des conventions de journalisation** | `AGENT.md` prescrit la tenue de `docs/journal/` (`JOURNAL.md`, `A_VALIDER.md`), tandis que le framework Teamwork consigne dans `.agents/teamwork/`. | `AGENT.md:276-281` vs Pratiques Teamwork | **Faible** | Risque de confusion sur le lieu de persistance des arbitrages humains : clarification requise entre logs éphémères et logs git pérennes. |
| **12** | **Dépendances externes non conteneurisées (Java 25 & Node)** | `technique.md` évoque l'installation locale de Java et Node (pour SUSHI), mais Node est manquant sur l'hôte et Java est en version 25. | `technique.md:18` vs Environnement Hôte | **Élevée** | Bloque l'exécution de SUSHI pour l'Étape 11 si Node n'est pas conteneurisé ou installé sur la machine. |
| **13** | **Rupture de chaîne sur la ressource FHIR `Procedure`** | `technique.md:125` prescrit « actes vers PROCEDURE_OCCURRENCE », mais `technique.md:100` omet `Procedure` dans les profils de l'IG Togo, et la synthèse initiale l'avait masqué à l'Étape 15. | `technique.md:100` vs `technique.md:125` | **Élevée** | Impossibilité de modéliser les actes médicaux, chirurgicaux ou obstétricaux togolais (accouchements, césariennes, actes SMI). |
| **14** | **Asymétrie de périmètre DHIS2 (Source vs Destination)** | `Definition  Projet.md:40` restreint DHIS2 aux **sources** (excluant DHIS2 des cibles), alors que `technique.md:119` en fait une destination d'indicateurs sans considérer l'instance démo publique éphémère. | `Definition  Projet.md:40` vs `technique.md:119` | **Moyenne** | Risque de dérive de périmètre (*scope creep*) et d'échec sur l'instance publique `play.dhis2.org/demo` sans persistance garantie. |
| **15** | **Contradiction interne sur les formats d'export IA** | `Definition  Projet.md:33` prescrit « exports Parquet et CSV », tandis que les sections suivantes (`l.41`, `AGENT.md:50`, `technique.md:135`) ne citent que « Parquet ». | `Definition  Projet.md:33` vs `Definition  Projet.md:41` | **Faible** | Ambiguïté sur les livrables de l'Étape 17 pour les utilisateurs ne disposant pas d'outils compatibles Parquet. |
| **16** | **Incertitude du découpage sanitaire togolais (Zone sensible #6)** | `AGENT.md:107` classe la hiérarchie sanitaire en zone sensible n°6, et `technique.md:24` note une incertitude sur le découpage officiel (35 vs 39 vs 44 districts), sans décision formalisée. | `AGENT.md:107`, `technique.md:24` vs Découpage réel Togo | **Élevée** | Risque d'incohérence dans l'arborescence des formations sanitaires, les règles de blocage Splink et l'agrégation épidémiologique. |
| **17** | **Absence d'arbitrage sur l'environnement de build SUSHI** | Node.js est absent de l'hôte, mais aucune décision ne tranchait entre conteneurisation Docker ou installation de Node.js sur la machine hôte. | Diagnostic système vs `technique.md:18` | **Élevée** | Blocage potentiel de la compilation FSH lors de l'Étape 11 si la stratégie d'outillage n'est pas actée dès l'Étape 0/1. |
| **18** | **Ambiguïté OMOP sur les Vaccinations et Agrégats DHIS2** | L'Étape 15 ne précisait pas la table OMOP cible pour `Immunization`, ni le traitement des agrégats DHIS2 face au modèle OMOP strictement centré patient. | `technique.md:125` vs Spécification OMOP CDM 5.4 | **Moyenne** | Risque de violation de l'intégrité conceptuelle OMOP si des agrégats populationnels étaient injectés dans les tables cliniques `PERSON`. |

### 5.2 Analyse Approfondie des Divergences Majeures

#### 5.2.1 Discordance Outillage & Environnement Python (`uv` vs `pip` & Python 3.11 vs 3.15)
Il s'agit du point de blocage technique le plus critique. L'incompatibilité entre la version 3.15.0 présente sur le système et les prérequis des bibliothèques de la stack (DuckDB, Splink, PyArrow, Pandera) empêchera toute installation propre si l'environnement n'est pas recalibré sur **Python 3.11**. Par ailleurs, l'adoption d'`uv` représente un gain majeur de reproductibilité grâce à son lockfile déterministe (`uv.lock`), évitant les dérives de versions de `pip`.

#### 5.2.2 Dualité des Voies de Génération de Vérité Terrain (Synthea vs Python ad hoc)
`technique.md` présente Synthea (Voie A) et le générateur Python (Voie B) comme deux alternatives, tandis que `Definition  Projet.md` indique souhaiter « les deux ». Dans la pratique du génie logiciel :
- **Synthea** est conçu pour le système de santé nord-américain (US Core). L'adapter au Togo requiert d'écrire des modules G-CODER en Java, de purger les profils américains, puis de relocaliser les données a posteriori.
- **Le générateur Python dédié (Voie B)** permet de produire nativement les pathologies prioritaires togolaises, les formats imparfaits et la hiérarchie sanitaire exacte en quelques centaines de lignes de code maîtrisées.
Développer les deux voies simultanément dès la phase initiale doublerait la charge de travail sans valeur ajoutée immédiate. La recommandation technique est de faire de la **Voie B le flux principal**, et de traiter la Voie A en extension ultérieure.

#### 5.2.3 SGBD Cible pour OMOP CDM 5.4
DuckDB est un formidable moteur analytique in-process, mais l'écosystème OHDSI (notamment **Achilles** et **Data Quality Dashboard**, rédigés en langage R) s'appuie historiquement sur l'infrastructure **PostgreSQL** via `DatabaseConnector`. Tenter d'exécuter DQD directement sur DuckDB est expérimental et source d'incompatibilités majeures. Puisque PostgreSQL est déjà déployé via Docker pour HAPI FHIR, y adjoindre une base de données dédiée `omop_cdm` est la solution d'architecture la plus robuste et standard.

#### 5.2.4 Discordance sur les Actes Cliniques et le Profil FHIR `Procedure`
L'analyse de `technique.md` révèle une lacune de conception dans le document source initial : l'Étape 11 énumérait 8 profils (`Patient`, `Encounter`, `Observation`, `Condition`, `MedicationRequest`, `Immunization`, `Location`, `Organization`) en omettant la ressource `Procedure`, alors même que l'Étape 15 exigeait explicitement « actes vers PROCEDURE_OCCURRENCE ».
Les actes cliniques (particulièrement obstétricaux, chirurgicaux et actes de soins préventifs de la SMI) sont indissociables des pathologies prioritaires togolaises définies dans le périmètre (ex. accouchements, césariennes, pansements, ponctions). La suppression silencieuse des actes dans la première version de synthèse masquait le problème sans le résoudre. La remédiation consiste à intégrer formellement le profil `TogoProcedure` dans l'IG FHIR (Étape 11) et à restaurer l'ETL vers `PROCEDURE_OCCURRENCE` (Étape 15).

#### 5.2.5 Rôle et Faisabilité Opérationnelle de DHIS2 en Destination
Dans `Definition  Projet.md` (§5), DHIS2 est formellement circonscrit au statut de « Source ». Néanmoins, `technique.md` (Étape 14) évoque le rôle de DHIS2 en récepteur d'indicateurs.
L'analyse d'infrastructure démontre qu'interagir en écriture réelle avec l'instance publique officielle de démonstration (`https://play.dhis2.org/demo`) est hautement risqué : cette instance est mutualisée mondialement, ses bases de données sont réinitialisées périodiquement de manière automatisée, et les comptes de démonstration disposent de droits d'écriture volatils. 
Pour résoudre cette contradiction sans dérive de périmètre, le projet cadre l'Étape 14 comme la production et la validation de **fichiers d'exportation d'indicateurs conformes à la norme d'échange DHIS2** (format ADX et JSON `dataValueSets`), testés contre un mock d'API DHIS2 conteneurisé ou simulé, sans dépendance de persistance sur l'instance publique.

#### 5.2.6 Articulation des Formats d'Export IA (Parquet Prioritaire vs CSV Miroir)
`Definition  Projet.md` mentionne à la ligne 33 « exports Parquet et CSV », puis ne mentionne plus que « Parquet » à la ligne 41 et dans l'ensemble des autres documents techniques.
Pour satisfaire aux exigences modernes du Machine Learning tout en garantissant une accessibilité maximale :
- **Apache Parquet est la cible prioritaire absolue** : il préserve les types stricts (int, float, date, datetime), offre une compression par colonnes optimale (Snappy/ZSTD) et s'intègre nativement avec Polars, DuckDB et Pandas sans perte de métadonnées.
- **Le format CSV est conservé à titre secondaire** : un export dénormalisé miroir au format CSV (encodage UTF-8, séparateur virgule, sans troncature) est généré en fin d'Étape 17 pour les utilisateurs ou analystes exploitant des outils bureautiques ou statistiques ne lisant pas nativement Parquet.

#### 5.2.7 Modélisation OMOP CDM : Vaccinations et Étanchéité des Agrégats
Le modèle relationnel OMOP CDM 5.4 est conçu autour de la table pivot `PERSON` : chaque ligne des tables cliniques doit obligatoirement être rattachée à un individu identifié via `person_id`.
Or, le pipeline brasse deux types d'informations hétérogènes :
1. **Les vaccinations (`TogoImmunization`)** : Données individuelles. Selon les conventions OHDSI, une vaccination est mappée vers `DRUG_EXPOSURE` (avec le concept de produit/antigène vaccinal en `drug_concept_id`, et `drug_type_concept_id = 32827 - EHR encounter record`). Si un code d'acte d'injection est tracé, il peut également faire l'objet d'un enregistrement dans `PROCEDURE_OCCURRENCE`.
2. **Les agrégats DHIS2 (`MeasureReport`)** : Comptages statistiques populationnels non nominatifs (ex. « 142 cas de paludisme dans le district de Tone en mars »). **Il est strictement proscrit d'injecter des agrégats dans la table `PERSON` ou dans les tables cliniques OMOP**, sous peine de corrompre les calculs épidémiologiques d'Achilles et DQD. Les agrégats sont persistés sous forme de ressources FHIR `MeasureReport` dans HAPI FHIR et exportés dans une table Parquet dédiée `gold_dhis2_indicators.parquet`.

---

## 6. Questions Décisionnelles et Arbitrages Requis de l'Utilisateur

Afin de permettre le démarrage serein et structuré des développements, l'arbitrage formel de l'utilisateur est sollicité sur les 9 choix structurants suivants. La question cosmétique sur le renommage de fichier est reléguée au rang de simple règle d'hygiène à l'Étape 0 (Section 7.1), cédant la place à des arbitrages d'ingénierie majeurs (exécution de SUSHI et référentiel territorial).

### 6.1 Tableau des Choix Structurants et Recommandations

| N° | Décision Structurante | Options Offertes à l'Arbitrage | Recommandation Technique Motivée |
|---|---|---|---|
| **D-01** | **Gestionnaire de dépendances et gestion du lockfile** | **A.** `uv` avec `pyproject.toml` (suppression de `requirements.txt`).<br>**B.** `pip` standard avec `pyproject.toml` ou `requirements.txt`. | **Option A (`uv`)** : Déterminisme absolu via `uv.lock`, rapidité d'exécution, gestion automatique des versions Python, conformité à `AGENT.md:47`. |
| **D-02** | **Normalisation de la version d'interpréteur Python** | **A.** Figer et installer **Python 3.11 strict** (via `uv python install 3.11`).<br>**B.** Tenter de compiler sur Python 3.15 hôte. | **Option A (Python 3.11 strict)** : Seule version garantissant la disponibilité des wheels binaires précompilées pour Splink, DuckDB, PyArrow et Pandera. |
| **D-03** | **Normalisation linguistique des sous-paquets `src/`** | **A.** Standardiser tous les noms de packages en **anglais** (`src/profiling`, `src/cleaning`, `src/matching`, `src/canonical_model`, etc.).<br>**B.** Conserver les noms en français de la ligne 69 d'`AGENT.md` (`src/profilage`, `src/nettoyage`, etc.). | **Option A (Anglais)** : Respecte la règle d'`AGENT.md:17` (« identifiants de code en anglais ») et les conventions universelles PEP 8, éliminant les imports franglais. |
| **D-04** | **Priorité d'implémentation de la Vérité Terrain (Étape 3)** | **A.** Générateur Python contextuel (**Voie B**) en priorité n°1 ; Synthea (**Voie A**) reporté en enrichissement ultérieur.<br>**B.** Synthea en priorité n°1.<br>**C.** Développer simultanément les deux voies de front. | **Option A (Voie B Python prioritaire)** : Alignement immédiat sur la pyramide sanitaire togolaise et les pathologies cibles sans la lourdeur du portage Java de Synthea. |
| **D-05** | **Moteur de stockage pour OMOP CDM 5.4 et OHDSI** | **A.** Base **PostgreSQL conteneurisée dédiée** (dans la pile `docker-compose.yml`).<br>**B.** Base locale in-process DuckDB. | **Option A (PostgreSQL)** : Indispensable pour exécuter nativement OHDSI Achilles et DQD en R via DatabaseConnector sans blocage dialectal SQL. |
| **D-06** | **Modalité d'intégration d'OpenHIM dans le flux batch** | **A.** OpenHIM agit en **proxy de médiation transactionnel actif** : la CLI Typer envoie les Bundles sur OpenHIM qui authentifie et route vers HAPI.<br>**B.** OpenHIM déployé à titre d'illustration architecturale, la CLI chargeant directement dans HAPI FHIR.<br>**C.** Double mode configurable via drapeau CLI (`--use-openhim` / `--direct-hapi`). | **Option C (Double mode, OpenHIM par défaut)** : Valide concrètement l'architecture OpenHIE tout en conservant une voie rapide de contournement pour les tests de gros volumes. |
| **D-07** | **Stratégie d'exécution de SUSHI / FHIR Shorthand (Étape 11)** | **A.** **Conteneur Docker Node.js dédié** encapsulant SUSHI et Java IG Publisher.<br>**B.** Installation directe de **Node.js (v20 LTS) et npm sur l'hôte**. | **Option A (Conteneur Docker dédié)** : Préserve l'étanchéité de l'environnement hôte (qui ne contient pas Node), garantit la portabilité CI/CD et standardise le build. |
| **D-08** | **Référentiel territorial sanitaire du Togo (Zone sensible #6)** | **A.** **Découpage officiel récent à 6 régions et 44 districts sanitaires**, enrichi d'un catalogue synthétique d'USP/CMS/CHR/CHU codifié.<br>**B.** Arbre hiérarchique brut extrait de l'instance démo publique DHIS2.<br>**C.** Ancien découpage administratif togolais à 35 ou 39 districts. | **Option A (44 districts officiels validés)** : Reflète l'organisation sanitaire togolaise actuelle, assure des clés de blocage exactes pour Splink et respecte la validation humaine requise. |
| **D-09** | **Gestion des Vocabulaires Volumineux (Athena, CIM-10)** | **A.** Versionner un **mock/extrait synthétique minimaliste (< 1 Mo)** pour les tests et la CI, et script de téléchargement externe pour les tables complètes.<br>**B.** Versionner les vocabulaires complets via Git LFS.<br>**C.** Téléchargement dynamique à la volée pendant les tests. | **Option A (Mock minimaliste < 1 Mo dans git)** : Conforme à `AGENT.md:123` (tests < 1 Mo sans réseau) et respecte les contraintes de taille du dépôt git. |

### 6.2 Fiches Détaillées des Décisions à Arbitrer

Chaque décision structurante fait l'objet d'une fiche technique autonome exposant les enjeux, les options envisageables, leur analyse comparative et la recommandation d'ingénierie.

---

#### Fiche D-01 : Gestionnaire de dépendances Python et gestion du lockfile

* **Contexte et enjeux** :
  `technique.md` (l.7) prescrit l'utilisation de `pip`, alors qu'`AGENT.md` (l.47) impose formellement `uv`. Le dépôt initial présente un fichier `requirements.txt` vide de 0 octet et aucun fichier `pyproject.toml`. L'outil `uv` n'est pas encore installé sur la machine de développement. L'enjeu est de garantir la reproductibilité absolue des environnements de calcul entre agents et développeurs, et de prévenir les dérives de versions (*dependency drift*).
* **Options envisageables** :
  - **Option A (`uv` avec `pyproject.toml`)** : Adopter `uv` comme gestionnaire universel de projet et de paquets, centraliser les métadonnées dans un fichier standardisé `pyproject.toml` (PEP 517/621) et figer l'arbre complet des dépendances dans un lockfile `uv.lock`.
  - **Option B (`pip` standard avec `requirements.txt`)** : Conserver le modèle historique Python basé sur `pip` et `requirements.txt`, potentiellement secondé par `pip-tools` (`pip-compile`).
* **Analyse comparative** :
  - *Avantages Option A* : Résolution de dépendances ultra-rapide (développée en Rust, 10 à 100 fois plus rapide que pip) ; lockfile universel et déterministe garantissant une stricte reproductibilité au bit près ; capacité native de gérer et d'installer les versions de Python elles-mêmes (`uv python install 3.11`) ; alignement direct sur la directive prioritaire d'`AGENT.md:47`.
  - *Inconvénients / Risques Option A* : Nécessite l'installation d'un binaire standalone `uv` sur l'hôte à l'Étape 0 (installation triviale par script officiel ou pip).
  - *Avantages Option B* : Outil standard disponible par défaut avec tout interpréteur Python.
  - *Inconvénients / Risques Option B* : `pip` ne gère pas nativement de fichier de verrouillage (*lockfile*) déterministe ; lenteur de résolution ; risque élevé de divergence de sous-dépendances lors des builds CI ou des relances multi-agents.
* **Recommandation technique motivée** :
  **Option A (`uv`)**. La contrainte d'intégrité et de reproductibilité stricte du projet rend le lockfile déterministe indispensable. `uv` résout par ailleurs nativement le blocage de l'interpréteur Python (Fiche D-02).
* **Impact sur la Roadmap** :
  Étape 0 : installation de `uv`, création de `pyproject.toml`, suppression de `requirements.txt` et génération de `uv.lock`.

---

#### Fiche D-02 : Normalisation de la version d'interpréteur Python

* **Contexte et enjeux** :
  `AGENT.md` (l.47) et `technique.md` (l.7) fixent impérativement l'environnement sur **Python 3.11**. Or, l'inspection factuelle du système hôte révèle que l'interpréteur système actif et l'environnement virtuel local `.venv` tournent sous **Python 3.15.0** (version expérimentale de développement). De nombreuses bibliothèques clés du projet (`duckdb`, `pyarrow`, `splink`, `pandera`, `pydantic-v2`, `fhir.resources`) contiennent des extensions natives en C/C++/Rust et ne disposent pas de binaires précompilés (*wheels*) pour Python 3.15.
* **Options envisageables** :
  - **Option A (Python 3.11 strict)** : Télécharger et configurer un interpréteur CPython 3.11 dédié au projet via `uv python install 3.11` et forcer l'environnement virtuel sur cette version.
  - **Option B (Python 3.15 hôte)** : Conserver Python 3.15 et tenter de compiler l'ensemble des dépendances depuis leurs sources C/Rust.
* **Analyse comparative** :
  - *Avantages Option A* : Compatibilité immédiate à 100 % avec l'ensemble des packages du projet via des wheels `manylinux` précompilées ; temps d'installation de quelques secondes ; stabilité éprouvée en production data science ; conformité stricte aux spécifications contractuelles.
  - *Inconvénients / Risques Option A* : Nécessite le téléchargement ponctuel (~30 Mo) du binaire CPython 3.11 managé par `uv`.
  - *Avantages Option B* : Aucun.
  - *Inconvénients / Risques Option B* : Échec immédiat garanti lors de l'installation de `pyarrow` et `duckdb` (absence de support de Python 3.15 par les bibliothèques C++ sous-jacentes) ; blocage intégral de l'avancement dès l'Étape 0.
* **Recommandation technique motivée** :
  **Option A (Python 3.11 strict)**. Il s'agit d'une condition sine qua non de faisabilité technique.
* **Impact sur la Roadmap** :
  Étape 0 : exécution de `uv venv --python 3.11` pour recréer `.venv` sous Python 3.11 certifié.

---

#### Fiche D-03 : Normalisation linguistique de l'architecture des sous-paquets `src/`

* **Contexte et enjeux** :
  Le document `AGENT.md` présente une contradiction interne : la règle 1.3 (l.17) ordonne expressément : *« Identifiants de code (fonctions, variables, classes) en anglais »*, tandis que la section 4 (l.69-71) énumère les sous-répertoires de `src/` en langue française (`src/profilage`, `src/nettoyage`, `src/rapprochement`, `src/modele`, etc.). En Python, les noms de répertoires sous `src/` constituent directement les modules et paquetages importés dans le code source (`import src.profilage`).
* **Options envisageables** :
  - **Option A (Nomenclature anglophone intégrale dans `src/`)** : Nommer tous les répertoires et modules en anglais (`src/profiling`, `src/cleaning`, `src/matching`, `src/canonical_model`, `src/terminology`, `src/ig`, `src/fhir_transform`, `src/omop_etl`, `src/export_ai`, `src/evaluation`).
  - **Option B (Nomenclature francophone issue de la ligne 69)** : Conserver les dossiers en français (`src/profilage`, `src/nettoyage`, etc.).
  - **Option C (Architecture hybride)** : Paquets de premier niveau en français, sous-modules et fonctions en anglais.
* **Analyse comparative** :
  - *Avantages Option A* : Cohérence syntaxique parfaite avec la règle 1.3 d'`AGENT.md` ; respect des standards de la communauté Python internationale (PEP 8) ; élimine le mélange dysfonctionnel « franglais » dans les instructions d'importation (`from src.cleaning.normalizer import clean_patronymic`) ; intégration naturelle avec les librairies open-source du domaine (FHIR, OHDSI). Les documentations, docstrings, rapports de qualité et libellés de données restent intégralement en français.
  - *Inconvénients / Risques Option A* : Écart formel avec la liste illustrative de la ligne 69 d'`AGENT.md`.
  - *Avantages Option B* : Respect littéral de la liste de la ligne 69.
  - *Inconvénients / Risques Option B* : Viole la ligne 17 d'`AGENT.md` ; engendre des instructions d'import incohérentes et peu idiomatiques (`from src.rapprochement.mpi import SplinkMatcher`).
  - *Inconvénients / Risques Option C* : Confusion maximale de maintenance pour les développeurs.
* **Recommandation technique motivée** :
  **Option A (Anglais pour les packages et le code)**. C'est la convention standard en génie logiciel et la seule manière d'harmoniser les règles 1.3 et 4 d'`AGENT.md`. La documentation technique et fonctionnelle demeure en français.
* **Impact sur la Roadmap** :
  Étape 0 : instanciation des répertoires de code sous leurs dénominations normalisées en anglais.

---

#### Fiche D-04 : Priorisation méthodologique de la Vérité Terrain (Étape 3)

* **Contexte et enjeux** :
  `Definition  Projet.md` (l.51) exprime le souhait d'avoir « Les deux », tandis que `technique.md` (l.32-35) distingue deux approches méthodologiques pour générer la vérité terrain (*Ground Truth*) : la Voie A (génération via l'outil Java Synthea avec surcouche de relocalisation) et la Voie B (générateur Python ad hoc calibré sur le contexte togolais). L'enjeu est d'optimiser l'effort d'ingénierie et d'éviter la dispersion des ressources sur deux générateurs redondants dès la phase initiale.
* **Options envisageables** :
  - **Option A (Voie B prioritaire en Phase 1/2)** : Développer le générateur Python contextuel en priorité n°1 pour couvrir immédiatement l'intégralité des pathologies togolaises et des structures sanitaires. Reporter la Voie A (Synthea) en extension ultérieure.
  - **Option B (Voie A prioritaire)** : Implémenter en priorité la customisation de Synthea en Java.
  - **Option C (Développement conjoint simultané)** : Implémenter de front les deux générateurs dès l'Étape 3.
* **Analyse comparative** :
  - *Avantages Option A* : Maîtrise totale du code en pur Python (zéro dépendance Java externe) ; modélisation directe et fidèle des distributions épidémiologiques du Togo (paludisme, SMI, drépanocytose, malnutrition) ; production native d'identités togolaises (patronymes, âges approximatifs, découpage territorial) ; agilité maximale et vélocité accrue.
  - *Inconvénients / Risques Option A* : Nécessite de formaliser les règles génératrices cliniques dans le code Python.
  - *Avantages Option B* : Réutilisation de la mécanique de simulation physiologique multi-états de Synthea.
  - *Inconvénients / Risques Option B* : Synthea est fortement ancré dans le modèle médical américain (profils US Core, terminologies RxNorm/SNOMED US, organisation en assurances privées). L'adapter au Togo impose d'écrire des modules G-CODER en Java, de purger les extensions US Core et de reconstruire la démographie, représentant une charge disproportionnée par rapport aux objectifs du projet.
  - *Inconvénients / Risques Option C* : Risque majeur de dispersion de la charge de développement, de retard sur la roadmap et d'incohérences de volumétries entre les deux voies.
* **Recommandation technique motivée** :
  **Option A (Voie B prioritaire)**. Le générateur Python contextuel répond directement aux spécifications métiers togolaises avec une complexité d'ingénierie maîtrisée.
* **Impact sur la Roadmap** :
  Étape 3 : réalisation prioritaire du module Python `src/generation/contextual_generator.py` ; formalisation de l'architecture Synthea en jalon optionnel de phase ultérieure.

---

#### Fiche D-05 : Moteur de stockage pour OMOP CDM 5.4 et outillage OHDSI

* **Contexte et enjeux** :
  Le pipeline s'appuie sur DuckDB pour le traitement analytique rapide in-process des couches Bronze, Silver et Gold. Cependant, les Étapes 15 et 16 imposent le chargement des données dans le schéma relationnel OMOP CDM 5.4 et l'exécution des outils de contrôle qualité officiels de la communauté OHDSI (**Achilles** et **Data Quality Dashboard - DQD**). Ces outils, développés en R, s'appuient sur le connecteur `DatabaseConnector`.
* **Options envisageables** :
  - **Option A (Base PostgreSQL conteneurisée dédiée)** : Déployer une instance PostgreSQL 15 au sein de `docker-compose.yml` hébergeant la base de données relationnelle `omop_cdm`.
  - **Option B (Base DuckDB locale in-process pour OMOP)** : Tenter d'héberger les tables OMOP CDM directement dans une base DuckDB locale.
  - **Option C (Architecture duale PostgreSQL + Parquet)** : Héberger le schéma de référence OMOP sous PostgreSQL pour certifier Achilles/DQD, et exporter les tables OMOP en Parquet pour l'apprentissage automatique (Étape 17).
* **Analyse comparative** :
  - *Avantages Option A / C* : PostgreSQL est la plateforme de référence universellement testée et supportée par l'écosystème OHDSI (DatabaseConnector, Achilles, DQD, Atlas) ; zéro friction lors de l'exécution des scripts SQLRender OHDSI ; cohabitation parfaite dans la pile Docker existante (qui héberge déjà PostgreSQL pour HAPI FHIR).
  - *Inconvénients / Risques Option A / C* : Nécessite la gestion d'un conteneur de base de données persistant avec volume Docker.
  - *Avantages Option B* : Aucun service serveur à maintenir, stockage dans un fichier unique `.duckdb`.
  - *Inconvénients / Risques Option B* : Incompatibilités sévères entre le dialecte SQL de DuckDB et les requêtes OHDSI SQLRender ; pilote `DatabaseConnector` R expérimental et non officiellement certifié pour DQD sous DuckDB ; risque de blocage complet de l'Étape 16.
* **Recommandation technique motivée** :
  **Option C (PostgreSQL conteneurisé pour OMOP + exports Parquet)**. C'est l'unique garantie d'exécuter avec succès la suite qualité officielle OHDSI tout en fournissant des fichiers Parquet optimisés pour l'IA.
* **Impact sur la Roadmap** :
  Étape 1 : ajout de la base `omop_cdm` dans le conteneur PostgreSQL du `docker-compose.yml`. Étape 15 : ETL vers PostgreSQL. Étape 17 : export des tables OMOP vers Parquet.

---

#### Fiche D-06 : Modalité d'intégration d'OpenHIM dans le pipeline batch

* **Contexte et enjeux** :
  Le projet s'inscrit formellement dans une architecture OpenHIE, prévoyant une passerelle d'interopérabilité OpenHIM en amont du serveur HAPI FHIR JPA (`technique.md:117`). Parallèlement, `Definition  Projet.md` (l.46) exclut les flux en temps réel au profit de traitements par lots (batch) via une interface CLI Typer. Il convient d'arbitrer le positionnement opérationnel exact d'OpenHIM dans cette chaîne d'ingestion.
* **Options envisageables** :
  - **Option A (Proxy de médiation actif strict)** : Tous les Bundles FHIR émis par la CLI Typer transitent obligatoirement par le port d'écoute d'OpenHIM, qui authentifie la requête, journalise la transaction et réachemine vers HAPI FHIR.
  - **Option B (Déploiement architectural illustratif)** : OpenHIM est configuré dans Docker pour valider l'architecture OpenHIE, mais la CLI batch communique directement avec l'API REST de HAPI FHIR pour maximiser les performances d'ingestion.
  - **Option C (Double mode configurable par paramètre CLI)** : Mode par défaut via OpenHIM (`--use-openhim`), avec possibilité de basculer en ingestion directe (`--direct-hapi`) lors des chargements massifs ou des tests unitaires de performance.
* **Analyse comparative** :
  - *Avantages Option A* : Démontre la conformité OpenHIE à 100 % ; traçabilité unitaire de chaque transaction dans la console web d'OpenHIM ; validation des mécanismes d'authentification et de contrôle d'accès.
  - *Inconvénients / Risques Option A* : Pénalité de latence sur les gros volumes de données découpés en centaines de Bundles.
  - *Avantages Option B* : Débit d'ingestion maximal sans surcharge réseau intermédiaire.
  - *Inconvénients / Risques Option B* : OpenHIM reste un composant passif non sollicité lors des exécutions régulières du pipeline.
  - *Avantages Option C* : Combine les bénéfices des deux approches : validation stricte OpenHIE en intégration et flexibilité lors des tests lourds.
* **Recommandation technique motivée** :
  **Option C (Double mode configurable, OpenHIM par défaut)**. Permet de prouver formellement la conformité OpenHIE sans pénaliser les phases d'expérimentation rapide.
* **Impact sur la Roadmap** :
  Étape 1 : configuration des canaux OpenHIM dans `docker-compose.yml`. Étape 14 : implémentation de l'adaptateur HTTP client prenant en charge le routage proxy ou direct.

---

#### Fiche D-07 : Stratégie d'exécution de SUSHI / FHIR Shorthand (Étape 11)

* **Contexte et enjeux** :
  L'Étape 11 impose la compilation du Guide d'Implémentation Togo rédigé en FHIR Shorthand (FSH) au moyen de l'outil officiel **SUSHI** (`fsh-sushi`), suivi de la publication via l'**IG Publisher** HL7. Or, le diagnostic de l'environnement hôte (Section 4.2) montre que **la commande `node` n'est pas installée sur la machine hôte**. SUSHI étant une application Node.js distribuée via npm, son mode d'exécution conditionne le succès de l'Étape 11.
* **Options envisageables** :
  - **Option A (Conteneur Docker Node.js dédié pour SUSHI)** : Définir un service ou un conteneur éphémère Docker exécutant une image Node (ex. `node:20-alpine`) intégrant `fsh-sushi` préinstallé, orchestré via la CLI (`docker run -v ./ig:/workspace ...`).
  - **Option B (Installation directe de Node.js et npm sur la machine hôte)** : Installer la distribution binaire de Node.js (version 20 LTS) et npm directement sur le système d'exploitation hôte.
  - **Option C (Conteneur communautaire combiné SUSHI + IG Publisher Java)** : Utiliser l'image Docker officielle de la communauté HL7 intégrant conjointement SUSHI, Java et l'IG Publisher.
* **Analyse comparative** :
  - *Avantages Option A / C* : Préservation absolue de l'étanchéité de l'hôte (aucun binaire npm polluant la machine) ; reproductibilité garantie sur n'importe quel poste de travail et dans la CI GitHub Actions ; indépendance vis-à-vis des versions de Node du système.
  - *Inconvénients / Risques Option A / C* : Nécessite que le démon Docker soit démarré ; léger temps de montage des volumes partagés.
  - *Avantages Option B* : Exécution directe en ligne de commande locale plus rapide sans intermédiaire conteneurisé.
  - *Inconvénients / Risques Option B* : Alourdit les prérequis d'installation de la machine hôte ; expose à des divergences de versions locales de Node.js entre contributeurs.
* **Recommandation technique motivée** :
  **Option A (Conteneur Docker dédié pour SUSHI)** avec extension vers l'Option C pour la publication finale de l'IG. Cette approche respecte le principe d'isolation des dépendances externes.
* **Impact sur la Roadmap** :
  Étape 1 : rédaction du script/Dockerfile pour le build FSH conteneurisé. Étape 11 : exécution de la compilation SUSHI dans le conteneur Docker.

---

#### Fiche D-08 : Référentiel territorial et cartographie sanitaire de référence du Togo (Zone sensible #6)

* **Contexte et enjeux** :
  `AGENT.md` (l.107) classe expressément le « Référentiel des formations sanitaires et hiérarchie administrative » dans les **8 zones à validation humaine obligatoire** (Zone sensible n°6). L'organisation administrative et sanitaire du Togo a connu des évolutions récentes : le découpage historique comptait 35 districts sanitaires, ultérieurement étendu à 39 districts, puis à **44 districts sanitaires répartis en 6 régions sanitaires** (Savanes, Kara, Centrale, Plateaux, Maritime, Grand Lomé) dans les derniers plans de développement sanitaire du Ministère de la Santé et de l'Hygiène Publique. De son côté, l'instance publique démo de DHIS2 propose un arbre d'unités d'organisation propre non spécifique. Il est critique de fixer le référentiel géographique officiel avant d'élaborer les clés de blocage du Master Patient Index (Splink, Étape 8) et les profils `TogoLocation` / `TogoOrganization` (Étape 11).
* **Options envisageables** :
  - **Option A (Découpage officiel récent à 6 régions et 44 districts sanitaires)** : Modéliser le référentiel complet stabilisé du Togo : 6 régions sanitaires, 44 districts sanitaires officiels, enrichi d'un annuaire synthétique cohérent des formations sanitaires classées selon les 4 niveaux de la pyramide togolaise (CHU nationaux, CHR régionaux, Hôpitaux de District / Préfectoraux, CMS et USP périphériques).
  - **Option B (Alignement strict sur l'arbre de l'instance démo publique DHIS2)** : Utiliser directement les unités d'organisation (OrgUnits) exposées par l'API démo de DHIS2.
  - **Option C (Découpage intermédiaire historique à 39 districts sanitaires)** : Adopter le découpage à 39 districts utilisé dans certaines publications épidémiologiques antérieures.
* **Analyse comparative** :
  - *Avantages Option A* : Alignement rigoureux avec la réalité administrative contemporaine du système de santé togolais ; cohérence parfaite pour l'entraînement de modèles d'IA sur des données contextualisées ; précision maximale pour les règles de blocage géographique de Splink ; satisfaction pleine et entière du contrôle humain de la Zone sensible #6.
  - *Inconvénients / Risques Option A* : Exige la formalisation d'une table de référence complète dans `data/reference/togo_health_geography.parquet` lors de l'Étape 2.
  - *Avantages Option B* : Récupération automatisée sans saisie de référentiel.
  - *Inconvénients / Risques Option B* : L'instance publique `play.dhis2.org/demo` utilise souvent des jeux de données de démonstration non togolais (ex. districts de Sierra Leone ou entités fictives), ce qui briserait le réalisme contextuel du pipeline.
  - *Avantages Option C* : Aucun avantage par rapport au découpage actuel.
  - *Inconvénients / Risques Option C* : Obsolescence institutionnelle.
* **Recommandation technique motivée** :
  **Option A (Référentiel officiel récent à 6 régions et 44 districts sanitaires)**. Le catalogue de référence sera produit dès l'Étape 2 sous forme d'une table Parquet immuable validée par l'humain.
* **Impact sur la Roadmap** :
  Étape 2 : génération et validation formelle de `data/reference/togo_health_geography.parquet` (6 régions, 44 districts, nomenclature USP/CMS/CHR/CHU). Étape 8 : intégration comme variables de blocage Splink.

---

#### Fiche D-09 : Stratégie de gestion des vocabulaires terminologiques volumineux Athena et nomenclatures

* **Contexte et enjeux** :
  `AGENT.md` (l.123) impose une règle d'intégrité stricte : *« Aucun test ne dépend du réseau ni de données hors dépôt. Utiliser de petits jeux de test versionnés (moins de 1 Mo) »*. Par ailleurs, les référentiels terminologiques complets (Athena pour OMOP CDM incluant SNOMED CT, LOINC, RxNorm, CIM-10) dépassent plusieurs giga-octets décompressés et sont soumis à des contrats de licence de redistribution (ex. SNOMED International). Il convient de concilier la portabilité des tests unitaires et la capacité à exécuter un pipeline complet.
* **Options envisageables** :
  - **Option A (Mock/extrait synthétique < 1 Mo dans git + script de téléchargement externe)** : Versionner dans le dépôt git un extrait terminologique ultra-léger (< 1 Mo) couvrant 100 % des codes cliniques des pathologies prioritaires du Togo, et fournir une commande CLI (`pipeline terminology fetch-athena`) téléchargeant les tables volumineuses dans un répertoire local exclu de git (`data/terminology_cache/`).
  - **Option B (Stockage des vocabulaires complets via Git LFS)** : Héberger les archives de plusieurs Go dans Git Large File Storage au sein du dépôt.
  - **Option C (Téléchargement dynamique en ligne à l'exécution des tests)** : Télécharger les concepts au fil de l'eau via les API web OHDSI ou HL7.
* **Analyse comparative** :
  - *Avantages Option A* : Respect intégral de la règle des tests < 1 Mo sans dépendance réseau ; exécution ultra-rapide des suites de tests Pytest en CI ; conformité totale avec les droits de propriété intellectuelle et licences de distribution ; légèreté du clonage du dépôt.
  - *Inconvénients / Risques Option A* : Nécessite une étape de téléchargement externe pour basculer sur un jeu de données réel exhaustif de plusieurs millions de concepts.
  - *Avantages Option B* : Intégralité des données présente lors d'un clone complet avec LFS.
  - *Inconvénients / Risques Option B* : Clonage prohibitif en bande passante ; saturation des quotas Git LFS ; violation potentielle des clauses de redistribution de SNOMED CT.
  - *Inconvénients / Risques Option C* : Fragilité extrême des tests en cas de coupure réseau ou de modification d'API distante ; violation formelle de la règle d'`AGENT.md:122`.
* **Recommandation technique motivée** :
  **Option A (Mock minimaliste < 1 Mo versionné + script externe)**. C'est la seule solution compatible avec les règles de gouvernance du projet.
* **Impact sur la Roadmap** :
  Étape 0/2 : versionnage de `terminology/sample_vocabularies.parquet` (< 1 Mo). Étape 10 : développement du script de chargement externe.

---

## 7. Plan d'Action et Recommandations Immédiates

Dès validation des arbitrages par l'utilisateur, l'équipe propose la feuille de route séquentielle suivante pour enclencher la réalisation :

### 7.1 Étape 0 : Cadrage du Socle et Initialisation du Dépôt *(Immédiat)*

1. **Actions d'hygiène et normalisation documentaire préventive** :
   - **Action H-01 : Normalisation typographique de `Definition  Projet.md`** : Renommer physiquement le fichier `'Definition  Projet.md'` en `'definition_projet.md'` (en conservant un lien symbolique ou une trace git propre via `git mv`). Cette mesure d'hygiène élémentaire élimine les risques d'erreur d'échappement d'espace dans les scripts bash, les Dockerfiles et les pipelines CI sans nécessiter d'arbitrage fonctionnel lourd.
   - **Action H-02 : Initialisation du `README.md` introductif bilingue** : Sortir `README.md` de son état de vacuité actuel (0 octet) en rédigeant la présentation globale du projet, les objectifs sanitaires togolais, le postulat de données 100 % synthétiques et les instructions de lancement rapide.

2. **Initialisation de l'environnement Python 3.11 et gestionnaire de paquets** :
   - Télécharger et installer `uv` sur l'hôte.
   - Instancier l'interpréteur CPython 3.11 via `uv python install 3.11`.
   - Créer le fichier `pyproject.toml` canonique fixant les métadonnées, la contrainte Python (`>=3.11,<3.12`), les dépendances scientifiques épinglées et la configuration des linters/testeurs (`ruff`, `pytest`).
   - Supprimer le fichier `requirements.txt` vide et générer le lockfile déterministe `uv.lock` via `uv sync`.

3. **Mise en place de l'arborescence des dossiers normalisée en anglais** :
   - Créer l'architecture des répertoires conformément aux arbitrages D-01 et D-03 :
     ```bash
     mkdir -p data/raw data/bronze data/silver data/gold/fhir data/gold/omop data/gold/ai data/quarantine data/truth data/reference
     mkdir -p src/ingestion src/profiling src/cleaning src/matching src/canonical_model src/terminology src/ig src/fhir_transform src/validation src/loading src/omop_etl src/export_ai src/degradation src/generation
     mkdir -p config terminology ig tests docs/fr docs/en docs/journal
     ```

4. **Initialisation des journaux pérennes du projet** :
   - Créer `docs/journal/JOURNAL.md` (journal chronologique append-only).
   - Créer `docs/journal/DECISIONS.md` (registre des arbitrages formalisés D-01 à D-09).
   - Créer `docs/journal/A_VALIDER.md` (file d'attente d'arbitrage humain pour les cas cliniques incertains).

5. **Initialisation des gabarits d'environnement** :
   - Compléter `.env.example` avec l'ensemble des variables requises (connexions PostgreSQL, HAPI FHIR, OpenHIM, URL démo DHIS2, sel cryptographique de pseudonymisation).

6. **Premier commit Git fondateur** :
   - Valider le socle initial sur la branche principale `master` / `main`.

### 7.2 Étape 1 : Déploiement de l'Infrastructure et Outillage CLI

1. **Orchestration Docker Compose** :
   - Écrire `docker-compose.yml` orchestrant :
     - Service 1 : PostgreSQL 15 (avec deux bases : `hapi_fhir` et `omop_cdm`).
     - Service 2 : HAPI FHIR JPA v6.8.0+ configuré sur la base PostgreSQL.
     - Service 3 : OpenHIM Core & OpenHIM Console pour la passerelle de médiation.
   - Démarrer le démon Docker et valider le démarrage unitaire des conteneurs.
2. **Implémentation du squelette de la CLI Typer** :
   - Créer le point d'entrée `src/cli.py` intégrant le groupe de commandes Typer modulaire : `pipeline raw`, `pipeline bronze`, `pipeline silver`, `pipeline fhir`, `pipeline omop`, `pipeline export`, etc.
3. **Outillage de Qualité et CI/CD** :
   - Configurer `ruff` dans `pyproject.toml` (règles de linting et de formatage).
   - Configurer `pytest` et rédiger les premiers tests unitaires de validation de l'environnement.
   - Mettre en place les workflows GitHub Actions dans `.github/workflows/ci.yml`.

### 7.3 Jalons de Suivi et Gouvernance Multi-Agents

Conformément à `AGENT.md` (§13), la transition vers l'implémentation opérationnelle s'effectuera sous la gouvernance suivante :
- **COORDINATEUR** : Découpage de l'Étape 1 en fiches de tâches élémentaires (`T-1-01`, `T-1-02`, etc.) avec assignation stricte d'un seul propriétaire par fichier.
- **TESTEUR** : Rédaction des tests en amont (TDD) échouant avant que le code ne soit produit.
- **IMPLÉMENTEUR** : Développement ciblé sur branche dédiée sans refactoring opportuniste.
- **RELECTEUR** : Revue indépendante rejouant tests et linters sans se fier aux déclarations d'implémentation.
- **HUMAIN** : Arbitrage unique et souverain sur les 8 zones sensibles d'AGENT.md et les 9 décisions structurantes de la section 6.

---

*Le présent rapport de synthèse constitue la référence contractuelle et technique pour la clôture de la Phase 1 d'exploration et le lancement de la Phase 2 d'implémentation du pipeline.*
