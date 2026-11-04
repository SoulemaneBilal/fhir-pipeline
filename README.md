# fhir-pipeline — Plateforme d'Interopérabilité et de Standardisation de Données de Santé (Togo)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![uv](https://img.shields.io/badge/packaged%20with-uv-purple.svg)](https://github.com/astral-sh/uv)
[![Standard HL7 FHIR R4](https://img.shields.io/badge/FHIR-R4%20(4.0.1)-firebrick.svg)](https://hl7.org/fhir/R4/)
[![OMOP CDM](https://img.shields.io/badge/OMOP%20CDM-5.4-darkblue.svg)](https://ohdsi.github.io/CommonDataModel/)
[![Architecture](https://img.shields.io/badge/Architecture-OpenHIE-forestgreen.svg)](https://openhie.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Vision et Présentation du Projet

Le projet **fhir-pipeline** est une infrastructure moderne de données en santé conçue pour relever le défi structurel du cloisonnement et de la fragmentation des informations médicales en Afrique de l'Ouest, avec un ancrage spécifique dans le contexte sanitaire de la République Togolaise.

Le pipeline transforme des sources hétérogènes, imparfaites et dégradées (agrégats DHIS2, classeurs Excel complexes, extraits de dossiers médicaux propriétaires simulés, Bundles FHIR invalides) en :
1. **Ressources HL7 FHIR R4 (4.0.1)** validées et profilées selon un Guide d'Implémentation national togolais ;
2. Un entrepôt relationnel standardisé conforme au modèle de données commun **OMOP CDM 5.4** de la communauté OHDSI, certifié par les outils officiels Achilles et Data Quality Dashboard (DQD) ;
3. Des jeux de données analytiques optimisés pour la science des données et l'apprentissage automatique au format **Apache Parquet (cible prioritaire)**, complétés par des **exports miroirs dénormalisés au format CSV**, documentés par une Fiche de Données (Datasheet) ;
4. Une intégration au sein d'une architecture interopérable conforme aux principes **OpenHIE** (*Open Health Information Exchange*), articulant serveur FHIR JPA (HAPI), passerelle d'interopérabilité (OpenHIM), registre des formations sanitaires, registre d'identification des patients (Splink) et service terminologique.

---

## 2. Contexte Sanitaire et Pyramide de Soins du Togo

Le système de santé togolais est structuré selon une pyramide sanitaire à quatre niveaux d'offre de soins, territorialisée en **6 Régions Sanitaires** (Savanes, Kara, Centrale, Plateaux, Maritime, Grand Lomé) subdivisées en **44 Districts Sanitaires officiels** :
- **Niveau Tertiaire / National** : Centres Hospitaliers Universitaires (CHU Sylvanus Olympio, CHU Campus, CHU Kara) ;
- **Niveau Secondaire / Régional** : Centres Hospitaliers Régionaux (CHR) ;
- **Niveau Primaire / Préfectoral** : Hôpitaux Préfectoraux / de District ;
- **Niveau Périphérique de Base** : Centres Médico-Sociaux (CMS) et Unités de Soins Périphériques (USP).

### Problématiques Sanitaires et Pathologies Prioritaires
Le pipeline est étalonné sur les charges de morbidité et les priorités de santé publique du Togo :
- **Pathologies infectieuses et endémiques** : Paludisme (formes simples et formes graves chez l'enfant et la femme enceinte), Infections Respiratoires Aiguës (IRA), Maladies diarrhéiques ;
- **Grandes endémies transmissibles** : VIH/SIDA (dépistage, suivi immunologique, protocoles antirétroviraux) et Tuberculose (schémas thérapeutiques nationaux) ;
- **Maladies chroniques et métaboliques** : Hypertension Artérielle (HTA), Diabète de type 2, Drépanocytose ;
- **Santé Maternelle et Infantile (SMI)** : Consultations Prénatales (CPN), accouchements, complications obstétricales, césariennes (actes cliniques) ;
- **Prévention et Nutrition** : Programme Élargi de Vaccination (PEV Togo : BCG, Penta, Polio, Rougeole-Rubéole, Fièvre Jaune) et malnutrition (aiguë modérée et sévère).

---

## 3. Postulat Éthique : Données 100 % Synthétiques

> **Avertissement Déontologique et Juridique Inviolable :**  
> **100 % des données utilisées et générées par ce projet sont algorithmiquement synthétiques ou extraites de bacs à sable publics de démonstration.**  
> **Aucune donnée réelle à caractère personnel ni aucun dossier de patient togolais n'est utilisé, manipulé ou stocké dans ce dépôt.**

Le projet respecte scrupuleusement la **Loi togolaise n° 2019-014 relative à la protection des données à caractère personnel** ainsi que la **Convention de Malabo de l'Union Africaine sur la cybersécurité et la protection des données à caractère personnel**.

Toutes les cohortes cliniques de patients virtuels reproduisent les distributions démographiques et épidémiologiques du Togo tout en garantissant :
- Le respect strict de la vie privée dès la conception (*Privacy by Design*) ;
- Des mécanismes de pseudonymisation déterministe par hachage cryptographique salé (SHA-256) ;
- L'interdiction absolue d'introduire des fichiers de données de santé réelles dans l'arborescence (arrêt d'urgence immédiat en cas de détection).

---

## 4. Architecture Technique (Medallion Lakehouse)

Le pipeline implémente le modèle **Medallion Lakehouse** assurant étanchéité, traçabilité unitaire bit-à-bit et reproductibilité déterministe (UUID v5) :

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         SOURCES D'INGESTION                              │
│   DHIS2 API (Agrégats) | Excel Multi-onglets | CSV Cliniques | FHIR JSON │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ SHA-256 / Copie bit-à-bit immuable
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  COUCHE RAW (data/raw/) : Données brutes immuables en lecture seule       │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ Métadonnées : source, row, timestamp, hash
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  COUCHE BRONZE (data/bronze/) : Stockage Parquet typé avec traçabilité    │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ Profilage qualité & nettoyage normalisé
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  COUCHE SILVER (data/silver/) : Données nettoyées, standardisées          │
│  • Rapprochement d'identité probabiliste Splink (Master Patient Index)    │
│  • Normalisation terminologique (CIM-10, LOINC, ATC, SNOMED CT)           │
│  • Validation sur Modèle Canonique Pydantic                               │
└──────────────────┬─────────────────┴───────────────────┬─────────────────┘
                   │                                     │
                   ▼                                     ▼
┌──────────────────────────────────────┐  ┌────────────────────────────────┐
│  COUCHE GOLD FHIR (data/gold/fhir/)  │  │  COUCHE GOLD OMOP (Postgres)   │
│  • Profils IG Togo (FSH / SUSHI)     │  │  • OMOP CDM 5.4 relationnel    │
│  • Validateur officiel HL7 Java      │  │  • Vocabulaires Athena         │
│  • Ingestion HAPI FHIR via OpenHIM   │  │  • Qualité Achilles & DQD (R)  │
└──────────────────┬───────────────────┘  └────────────────┬───────────────┘
                   │                                       │
                   └───────────────────┬───────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  COUCHE GOLD IA (data/gold/ai/)                                          │
│  • Tables Parquet typées (priorité ML) & exports miroirs CSV             │
│  • Validation par contrats Pandera & Fiche de Données (Datasheet)        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Guide de Démarrage Rapide (Quickstart)

### Prérequis Système
- **Système d'exploitation** : Linux (Debian, Ubuntu, RHEL) ou macOS
- **Gestionnaire Python** : [`uv`](https://github.com/astral-sh/uv) (v0.4+)
- **Conteneurisation** : Docker Engine 24+ et Docker Compose v2+
- **Version Python cible** : Python 3.11 strict

### 1. Cloner le Dépôt
```bash
git clone https://github.com/bi2l/fhir-pipeline.git
cd fhir-pipeline
```

### 2. Installer `uv` et approvisionner Python 3.11
```bash
# Installation de uv (si non installé)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Approvisionner l'interpréteur CPython 3.11 isolé
uv python install 3.11

# Créer l'environnement virtuel et synchroniser les dépendances
uv sync
```

### 3. Démarrer les Services d'Infrastructure Conteneurisés
```bash
# Lancement de PostgreSQL (bases hapi_fhir et omop_cdm), HAPI FHIR JPA et OpenHIM
docker compose up -d

# Vérifier la disponibilité du serveur FHIR
curl -s http://localhost:8080/fhir/metadata | grep "fhirVersion"
```

### 4. Utilisation de la CLI du Pipeline
Le point d'entrée unique de traitement est piloté par la CLI Typer :
```bash
# Afficher l'aide générale et les commandes disponibles
uv run fhir-pipeline --help

# 1. Ingérer les sources brutes vers les couches raw et bronze
uv run fhir-pipeline ingest --source data/raw/

# 2. Exécuter le profilage et le nettoyage silver
uv run fhir-pipeline clean

# 3. Exécuter le rapprochement d'identité Master Patient Index (Splink)
uv run fhir-pipeline match-patients

# 4. Générer les ressources FHIR profilées Togo et valider
uv run fhir-pipeline fhir-transform

# 5. Charger dans HAPI FHIR via la passerelle OpenHIM
uv run fhir-pipeline load --use-openhim

# 6. Exécuter l'ETL vers OMOP CDM 5.4 et valider la qualité (DQD)
uv run fhir-pipeline omop-etl
uv run fhir-pipeline omop-dqd

# 7. Exporter les jeux de données tabulaires pour l'entraînement d'IA
uv run fhir-pipeline export-ai --format parquet --mirror-csv
```

---

## 6. Arborescence du Projet

```
.
├── config/                 # Règles YAML de nettoyage, mappings et seuils
├── data/
│   ├── raw/                # Fichiers sources immuables (lecture seule)
│   ├── bronze/             # Données structurées Parquet avec 4 métadonnées
│   ├── silver/             # Données nettoyées et normalisées
│   ├── gold/
│   │   ├── fhir/           # Bundles et transactions FHIR validés
│   │   ├── omop/           # Exports tabulaires OMOP CDM
│   │   └── ai/             # Tables Parquet optimisées IA et miroirs CSV
│   ├── quarantine/         # Rejets avec motifs codifiés
│   ├── reference/          # Référentiels géographiques togolais (44 districts)
│   └── truth/              # Vérité terrain étalon générée
├── docs/
│   ├── journal/            # Registres de gouvernance pérennes (JOURNAL, DECISIONS, A_VALIDER)
│   ├── fr/                 # Documentation technique et fonctionnelle en français
│   └── en/                 # Documentation miroir en anglais
├── ig/                     # Sources FHIR Shorthand (FSH) du Guide d'Implémentation Togo
├── src/                    # Code source modulaire (packages en nomenclature anglaise)
│   ├── canonical_model/    # Entités pivots typées Pydantic
│   ├── cleaning/           # Règles modulaires de normalisation silver
│   ├── degradation/        # Moteur d'injection d'erreurs contrôlées
│   ├── export_ai/          # Génération des tables Parquet/CSV et contrats Pandera
│   ├── fhir_transform/     # Mapping canonique vers profils FHIR R4
│   ├── generation/         # Générateur contextuel Python (Voie B)
│   ├── ig/                 # Orchestration de la compilation SUSHI conteneurisée
│   ├── ingestion/          # Lecteurs multi-formats et ingestion raw/bronze
│   ├── loading/            # Connecteurs HTTP HAPI FHIR et OpenHIM
│   ├── matching/           # Modèle Splink et Master Patient Index
│   ├── omop_etl/           # ETL relationnel vers PostgreSQL OMOP CDM 5.4
│   ├── profiling/          # Moteur de profilage et 6 dimensions de qualité
│   ├── terminology/        # ConceptMaps, ValueSets et connecteur Athena
│   └── validation/         # Validation officielle HL7 et routage quarantaine
├── tests/                  # Miroir de tests unitaires et de propriétés (pytest)
├── docker-compose.yml      # Orchestration PostgreSQL, HAPI FHIR JPA, OpenHIM
├── pyproject.toml          # Métadonnées, dépendances strictes et outillage (ruff, pytest)
├── uv.lock                 # Fichier de verrouillage déterministe
└── README.md               # Présentation générale du projet
```

---

## 7. Feuille de Route Technique (Étapes 0 à 21)

| Étape | Intitulé | Livrable Clé |
|---|---|---|
| **Étape 0** | Cadrage du socle et initialisation du dépôt | Réconciliation documentaire, outillage uv / Python 3.11, Git |
| **Étape 1** | Environnement et outillage | Docker Compose (Postgres, HAPI, OpenHIM), CLI Typer, CI |
| **Étape 2** | Référentiels du contexte togolais | Découpage 6 régions / 44 districts, annuaire USP/CMS/CHU, URI |
| **Étape 3** | Génération des données « vérité terrain » | Générateur contextuel Python (Voie B) épidémiologique Togo |
| **Étape 4** | Dégradation contrôlée | Catalogue d'altérations réalistes et journal de corruption |
| **Étape 5** | Ingestion (raw et bronze) | Lecteurs multi-formats, hachage SHA-256, traçabilité bronze |
| **Étape 6** | Profilage et diagnostic initial | Mesure des 6 dimensions de qualité et rapport initial |
| **Étape 7** | Nettoyage et normalisation (silver) | Normalisation dates, âges, UCUM, libellés français, journal |
| **Étape 8** | Rapprochement des patients (MPI) | Modèle Splink, identifiant maître déterministe, déduplication |
| **Étape 9** | Modèle canonique | Schémas Pydantic typés des entités cliniques et indicateurs |
| **Étape 10** | Terminologies et ConceptMaps | Tables de correspondance, ConceptMaps FHIR, mock Athena < 1 Mo |
| **Étape 11** | Guide d'implémentation FHIR Togo | 9 profils togolais (dont TogoProcedure), build SUSHI conteneurisé |
| **Étape 12** | Mapping vers FHIR R4 | Bundles transactionnels, UUID v5 déterministes, MeasureReport |
| **Étape 13** | Validation officielle et quarantaine | Validateur officiel HL7 Java, registre des rejets et motifs |
| **Étape 14** | Chargement et architecture OpenHIE | Passerelle OpenHIM (mode double proxy/direct), HAPI FHIR JPA |
| **Étape 15** | FHIR vers OMOP CDM 5.4 | ETL PostgreSQL OMOP, étanchéité agrégats, concept 0 tracé |
| **Étape 16** | Qualité OMOP | Exécution officielle d'OHDSI Achilles et Data Quality Dashboard |
| **Étape 17** | Exports pour l'IA | Fichiers Parquet typés, CSV miroirs, contrats Pandera, Datasheet |
| **Étape 18** | Rapport avant/après | Métriques comparatives de redressement de qualité reproductibles |
| **Étape 19** | Sécurité et protection des données | Audit des secrets, conformité Loi 2019-014 et Malabo |
| **Étape 20** | Tests et intégration continue | Tests de déterminisme, tests de bout en bout sur 100 patients |
| **Étape 21** | Documentation et publication | Publication bilingue, documentation des mappings et release |

---

## 8. Gouvernance et Contribution

Le développement du projet respecte les règles inviolables définies dans `AGENT.md` et les décisions d'architecture consignées dans `docs/journal/DECISIONS.md`.

Toute intervention sur une **zone à validation humaine obligatoire** (correspondances cliniques sensibles, hiérarchie territoriale togolaise, seuils de fusion Splink, profils FHIR) exige l'approbation formelle d'un référent humain et l'enregistrement d'une fiche d'arbitrage dans `docs/journal/A_VALIDER.md`.

---

## 9. Licence

Le code source du pipeline est distribué sous licence libre **MIT**.  
La documentation et les spécifications de profils sont publiées sous licence **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
