## **Roadmap technique stricte**

Chaque étape dépend uniquement des précédentes. Une étape n’est terminée que si son critère de validation est atteint.

### **Décisions techniques tranchées**

* Python 3.11 strict (installé et managé via uv python install 3.11), gestionnaire universel de paquets et environnement virtuel par uv, configuration standardisée PEP 517/621 dans pyproject.toml et verrouillage déterministe via uv.lock.  
* FHIR R4 (4.0.1), modèles `fhir.resources` en version R4 épinglée.  
* Manipulation : pandas pour l’ingestion, DuckDB pour les couches analytiques intermédiaires et les jointures, Apache Parquet (cible prioritaire) et CSV dénormalisé (cible secondaire) pour le stockage et l'export.  
* Qualité : Pandera. Rapprochement de patients : **Splink** (liaison probabiliste, compatible DuckDB).  
* Validation : validateur officiel HL7 (Java) et SUSHI/FSH conteneurisés sous Docker pour la compilation des profils et du Guide d'Implémentation.  
* Serveur FHIR : **HAPI FHIR JPA** (Docker). Couche d’interopérabilité : **OpenHIM** (Docker, mode proxy de médiation par défaut et bypass direct configurable).  
* OMOP : CDM **5.4** hébergé sur PostgreSQL conteneurisé dédié (omop_cdm) pour la compatibilité OHDSI (DatabaseConnector, Achilles, Data Quality Dashboard), vocabulaires via **Athena** (mock < 1 Mo dans Git, script de téléchargement externe), et exports finaux en Parquet.  
* CLI : Typer. Qualité du code : ruff, pytest, pre-commit, GitHub Actions. Pas d’orchestrateur externe au départ.

### **Étape 0 : Cadrage du socle et initialisation du dépôt**

* **Tâches** :  
  * Réconciliation documentaire complète : résoudre les 18 discordances documentaires de SYNTHESE_PROJET.md (§5.1) dans `definition_projet.md`, `technique.md` et `AGENT.md`. Renommer `'Definition  Projet.md'` en `'definition_projet.md'`. Rédiger le `README.md` exhaustif de présentation du projet et du contexte togolais.  
  * Installer l'outillage Python : installer `uv` sur l'hôte, approvisionner CPython 3.11 via `uv python install 3.11`, créer le `pyproject.toml` (PEP 517/621, Python `>=3.11,<3.12`, dépendances du projet, config ruff/pytest), supprimer `requirements.txt` et générer le lockfile déterministe `uv.lock` via `uv sync`.  
  * Arborescence normalisée en anglais : créer tous les sous-paquets sous `src/` (`ingestion`, `profiling`, `cleaning`, `matching`, `canonical_model`, `terminology`, `ig`, `fhir_transform`, `validation`, `loading`, `omop_etl`, `export_ai`, `degradation`, `generation`) et les répertoires `data/raw`, `data/bronze`, `data/silver`, `data/gold/fhir`, `data/gold/omop`, `data/gold/ai`, `data/quarantine`, `data/truth`, `data/reference`, `config`, `tests`, `docs/journal`.  
  * Gouvernance pérenne et configuration : initialiser `docs/journal/JOURNAL.md`, `docs/journal/DECISIONS.md` (fiches D-01 à D-09), `docs/journal/A_VALIDER.md`, le gabarit `.env.example`, et enrichir `.gitignore` (caches, `.venv`, `.env`, bases de données locales).  
  * Versionnement Git : premier commit fondateur sur la branche principale figeant le socle reproductible.  
* **Validation** : `uv run python --version` retourne une version 3.11.x ; `uv sync` se termine avec succès (code 0) ; aucune contradiction documentaire résiduelle ; arborescence complète en place ; git commit initial créé.

### **Étape 1 : Environnement et outillage**

* **Tâches** : vérifier les prérequis d'exécution Docker et Python 3.11. Écrire le fichier docker-compose.yml orchestrant PostgreSQL 15 (avec deux bases : hapi_fhir et omop_cdm), HAPI FHIR JPA (v6.8+) et OpenHIM (Core et Console). Créer le conteneur Docker dédié pour SUSHI (Node.js). Créer le squelette de la CLI Typer (src/cli.py). Configurer linting (ruff), tests unitaires (pytest) et intégration continue GitHub Actions.  
* **Validation** : `docker compose up` démarre HAPI, `GET /metadata` répond en R4, la CI passe au vert sur un test trivial.

### **Étape 2 : Référentiels du contexte togolais**

* **Tâches** :  
  * Construire le **référentiel géographique et sanitaire togolais validé** : modéliser le découpage officiel stabilisé à 6 régions sanitaires et 44 districts sanitaires, enrichi de la hiérarchie des formations sanitaires en 4 niveaux (CHU, CHR, Hôpitaux Préfectoraux/District, CMS et USP). Source : référentiel cartographique national togolais consolidé, complété par les unités d'organisation DHIS2 et stocké sous forme de table Parquet de référence dans data/reference/togo_health_geography.parquet.  
  * Définir les **systèmes d’URI** du projet (CodeSystem locaux, identifiants de patient, de structure).  
  * Définir le **catalogue de pathologies prioritaires** et le mapping cible (CIM-10, SNOMED CT, LOINC, ATC).  
* **Sorties** : tables de référence en Parquet, document des URI.  
* **Validation** : chaque formation sanitaire a un identifiant unique, une hiérarchie complète, et aucun doublon de libellé normalisé.

### **Étape 3 : Génération des données « vérité terrain »**

* **Tâches** :  
  * **Voie B (Priorité n°1 - Phase 1/2)** : concevoir et implémenter le générateur Python contextuel (`src/generation/contextual_generator.py`) calibré sur le contexte togolais (patients, consultations, diagnostics, examens, médicaments, vaccinations, grossesses) produisant la vérité terrain native dans le modèle canonique, articulée sur le référentiel à 44 districts et les distributions épidémiologiques togolaises.  
  * **Voie A (Jalon d'extension ultérieur)** : formaliser l'adaptation de Synthea (retrait profils US Core, relocalisation patronymique et géographique togolaise, surcouche Java G-CODER) en jalon complémentaire.  
  * Récupérer la structure et des données agrégées de l’**instance de démonstration DHIS2** (API `dataValueSets`, unités d’organisation, éléments de données) pour la voie agrégée.  
  * Stocker la vérité terrain **séparément** des entrées dégradées.  
* **Sorties** : un jeu « or » (FHIR parfait), un jeu tabulaire équivalent, un jeu agrégé DHIS2.  
* **Validation** : toutes les ressources « or » passent le validateur ; deux générations avec la même graine sont identiques bit à bit.

### **Étape 4 : Dégradation contrôlée**

* **Tâches** : écrire un moteur de dégradation piloté par un **catalogue d’erreurs** versionné, chaque erreur étant paramétrée par un taux et une graine :  
  * dates en formats mixtes, dates de naissance remplacées par un âge approximatif ;  
  * noms : variantes d’orthographe, accents perdus, ordre nom/prénom inversé, translittérations ;  
  * libellés de diagnostics libres, abrégés ou mal orthographiés ;  
  * unités incohérentes, séparateurs décimaux mixtes (virgule/point) ;  
  * doublons de patients entre formations, avec identifiants différents ;  
  * valeurs manquantes, codes sentinelles (« NA », « \-1 », « 999 ») ;  
  * encodage cassé, colonnes Excel fusionnées, entêtes décalés, plusieurs feuilles ;  
  * FHIR invalide : champs obligatoires absents, références brisées, mauvais types ;  
  * noms de formations sanitaires écrits de plusieurs façons.  
  * Produire, pour chaque jeu dégradé, un **journal d’altérations** (quelle erreur, sur quelle ligne), qui sert de corrigé.  
* **Sorties** : jeux dégradés par format (Excel, CSV propriétaire simulé, JSON/FHIR cassé, DHIS2) et journal d’altérations.  
* **Validation** : le taux réel de chaque erreur injectée correspond au paramètre à plus ou moins un seuil ; le journal permet de reconstituer l’original.

### **Étape 5 : Ingestion (raw et bronze)**

* **Tâches** : un lecteur par format (Excel multi-feuilles, CSV avec détection d’encodage, JSON/Bundle FHIR, API DHIS2). Copier la source en `raw` sans la modifier. En `bronze`, ajouter `source_file`, `source_row`, `ingested_at`, `content_hash`. Les fichiers illisibles vont en quarantaine avec la raison, sans arrêter le lot.  
* **Validation** : les comptes bronze égalent les comptes sources ; une relance donne le même résultat ; un fichier corrompu n’interrompt pas le lot.

### **Étape 6 : Profilage et diagnostic initial**

* **Tâches** : calculer par table et par colonne la complétude, l’unicité, la validité de format, la cohérence entre champs, les doublons probables, les valeurs aberrantes. Mesurer six dimensions de qualité (complétude, exactitude, cohérence, unicité, validité, actualité). Générer un rapport « avant » automatique.  
* **Validation** : le rapport détecte les erreurs injectées de l’étape 4 avec un rappel mesuré contre le journal d’altérations.

### **Étape 7 : Nettoyage et normalisation (silver)**

* **Tâches** :  
  * dates (formats multiples, âge approximatif vers date estimée avec **indicateur de précision**) ;  
  * noms (normalisation de la casse, des accents, de l’ordre, conservation de la forme originale) ;  
  * unités (conversion vers UCUM) ;  
  * normalisation des libellés français (minuscules, accents, abréviations courantes) ;  
  * rapprochement des noms de formations avec le référentiel de l’étape 2 (similarité approchée, seuil, revue manuelle sous le seuil) ;  
  * valeurs sentinelles transformées en « manquant » explicite.  
  * Chaque règle est un module indépendant, déclaré dans une configuration YAML, qui journalise ce qu’il modifie.  
* **Validation** : un test par règle ; les métriques « après » s’améliorent sur chaque dimension ; aucune donnée n’est modifiée sans entrée de journal.

### **Étape 8 : Rapprochement des patients (registre client)**

* **Tâches** : définir la stratégie de blocage (région, année de naissance approximative, phonétique du nom), entraîner et calibrer un modèle Splink, fixer trois seuils (fusion automatique, revue manuelle, distinct). Produire un **identifiant patient maître** déterministe et une table de correspondance vers les identifiants sources. Ne jamais supprimer les enregistrements sources.  
* **Validation** : précision et rappel calculés contre les doublons connus de l’étape 4 ; matrice de confusion publiée ; zéro fusion de patients de sexe incompatible.

### **Étape 9 : Modèle canonique**

* **Tâches** : définir en Pydantic les entités (Patient, Structure, Consultation, Diagnostic, Examen/Observation, Médicament, Vaccination, Grossesse, Indicateur agrégé) avec champs de traçabilité. Écrire les transformations silver vers modèle canonique.  
* **Validation** : validation Pydantic à 100 % sur les données acceptées ; les rejets ont une raison codifiée.

### **Étape 10 : Terminologies et ConceptMaps**

* **Tâches** :  
  * charger le jeu de test terminologique synthétique minimaliste (< 1 Mo, versionné dans terminology/sample_vocabularies.parquet) couvrant 100 % des pathologies prioritaires togolaises pour les tests sans réseau ; fournir la commande CLI (pipeline terminology fetch-athena) pour télécharger les tables exhaustives Athena dans data/terminology_cache/ (hors git) ;  
  * construire des **tables de correspondance** local vers standard en trois niveaux : correspondance exacte, approchée (rapidfuzz avec seuil), revue manuelle ;  
  * chaque correspondance porte : source, cible, méthode, score, statut (validé, à revoir) ;  
  * exposer les correspondances sous forme de **ConceptMap** FHIR et de **ValueSet** en français.  
  * Ne jamais promouvoir automatiquement une correspondance sous le seuil.  
* **Validation** : taux de mapping par domaine publié ; échantillon vérifié manuellement ; 100 % des correspondances ont une méthode et un score.

### **Étape 11 : Guide d’implémentation FHIR « Togo »**

* **Tâches** : écrire en FSH et compiler via l'image Docker dédiée SUSHI les 9 profils togolais clés : TogoPatient, TogoEncounter, TogoObservation, TogoCondition, TogoProcedure (actes et chirurgies obstétricales), TogoMedicationRequest, TogoImmunization, TogoLocation, TogoOrganization, plus les extensions (précision de l’âge estimé, identifiant local de formation) et les ValueSets en français. Publier l’IG avec l’IG Publisher conteneurisé.  
* **Validation** : l’IG se compile sans erreur et les ressources « or » localisées de l’étape 3 valident contre lui.

### **Étape 12 : Mapping vers FHIR R4**

* **Tâches** : une fonction de mapping par ressource, pilotée par des règles déclaratives. Identifiants UUID v5. Références résolues via l’index des identifiants. Gérer Observation à valeur numérique, codée, composée. Pour l’agrégé, produire des `MeasureReport`. Assembler en Bundles de type transaction, triés par dépendance.  
* **Validation** : validation structurelle avec `fhir.resources` à 100 % des ressources produites ; zéro référence brisée ; relance idempotente.

### **Étape 13 : Validation officielle et quarantaine**

* **Tâches** : appeler le validateur HL7 en sous-processus sur tous les Bundles, avec les profils Togo. Classer les messages (erreur, avertissement, information). Les ressources en erreur vont en quarantaine avec message et chemin. Produire le registre des rejets.  
* **Validation** : aucune ressource en couche finale avec erreur ; chaque rejet est expliqué ; taux de récupération calculé contre la vérité terrain.

### **Étape 14 : Chargement et architecture OpenHIE**

* **Tâches** :  
  * charger d’abord organisations et lieux, puis patients, puis le reste, via transactions sur HAPI ;  
  * configurer **OpenHIM** comme passerelle d’interopérabilité devant HAPI FHIR, avec double mode d'alimentation dans la CLI batch (`--use-openhim` par défaut assurant authentification et audit de médiation, ou `--direct-hapi` pour les benchmarks massifs) ;  
  * concrétiser les composants OpenHIE : **registre des formations** (Location/Organization), **registre client** (Patient maître issu de Splink Étape 8), **service terminologique** (ConceptMaps/ValueSets), et **dossier clinique partagé** (HAPI FHIR) ;  
  * brancher DHIS2 en source d'agrégats (API démo publique) et en destination via la génération et validation de fichiers d'export conformes (ADX et dataValueSets JSON), testés contre un mock conteneurisé d'API DHIS2 sans persistance sur le serveur public.  
  * Documenter un schéma d’architecture et un scénario d’échange complet.  
* **Validation** : tests d’intégration automatisés : requêtes de recherche, lecture, relance sans doublon, accès refusé sans authentification via OpenHIM.

### **Étape 15 : FHIR vers OMOP CDM 5.4**

* **Tâches** : déployer le schéma relationnel OMOP CDM 5.4 sur PostgreSQL conteneurisé (base omop_cdm) et charger les vocabulaires Athena (mock en test, complet via cache). Exécuter l'ETL de transformation : TogoPatient vers PERSON, TogoEncounter vers VISIT_OCCURRENCE, TogoCondition vers CONDITION_OCCURRENCE, TogoObservation vers MEASUREMENT ou OBSERVATION, TogoMedicationRequest vers DRUG_EXPOSURE, TogoProcedure vers PROCEDURE_OCCURRENCE, TogoImmunization vers DRUG_EXPOSURE (avec drug_type_concept_id = 32827 - EHR encounter record, et trace optionnelle dans PROCEDURE_OCCURRENCE), et structures vers CARE_SITE / LOCATION. Règle d'étanchéité stricte : exclusion absolue des agrégats DHIS2 (MeasureReport) des tables cliniques OMOP afin de garantir l'intégrité épidémiologique d'Achilles/DQD ; ces agrégats sont isolés dans gold_dhis2_indicators.parquet. Conserver codes et concepts sources, affecter le concept 0 aux libellés non appariés avec rapport de traçabilité.  
* **Validation** : intégrité référentielle complète ; comptes OMOP égaux aux comptes FHIR attendus ; pourcentage de concept 0 par domaine publié.

### **Étape 16 : Qualité OMOP**

* **Tâches** : exécuter Achilles et le Data Quality Dashboard, analyser les échecs, corriger l’ETL ou documenter l’exception.  
* **Validation** : rapport DQD publié avec taux de réussite et liste des échecs justifiés.

### **Étape 17 : Exports pour l’IA**

* **Tâches** : générer les exports analytiques prioritaires au format Apache Parquet par table OMOP, complétés par une table aplatie dénormalisée par séjour et par patient (démographie, diagnostics, examens agrégés). Produire un export miroir dénormalisé au format CSV pour l'interopérabilité bureautique et statistique. Valider rigoureusement les schémas via des contrats Pandera. Pseudonymiser par hachage salé, généraliser dates et localisations sensibles. Rédiger une Fiche de Données (Datasheet) documentant l'origine synthétique, les distributions épidémiologiques togolaises, les limites, les biais et les usages déconseillés. Séparer variables explicatives et cibles.  
* **Validation** : schéma validé par Pandera ; test qui prouve qu’aucun identifiant direct ne sort ; fiche complète.

### **Étape 18 : Rapport avant/après**

* **Tâches** : générer automatiquement un rapport comparant qualité initiale et finale, taux de récupération, rejets par cause, mapping terminologique, performance du rapprochement de patients.  
* **Validation** : le rapport se régénère par une commande à partir d’un dépôt propre.

### **Étape 19 : Sécurité et protection des données**

* **Tâches** : aucun secret dans le dépôt, variables d’environnement, accès HAPI protégé, journal d’accès. Rédiger une note de conformité qui décrit les mesures face à la loi togolaise sur les données personnelles et au RGPD (à relire avec un juriste si vous visez un usage réel).  
* **Validation** : analyse de secrets dans la CI sans alerte.

### **Étape 20 : Tests et intégration continue**

* **Tâches** : tests unitaires par règle, tests de propriétés (idempotence, déterminisme), tests de bout en bout sur un petit jeu, couverture mesurée, CI complète (lint, tests, build IG, validation).  
* **Validation** : la CI exécute le pipeline de bout en bout sur 100 patients synthétiques.

### **Étape 21 : Documentation et publication**

* **Tâches** : README bilingue (français d’abord) avec schéma d’architecture, résultats chiffrés, guide de démarrage en une commande ; documentation des règles de mapping ; IG publiée via GitHub Pages ; licences distinctes pour le code et les données ; note expliquant que les données sont synthétiques.  
* **Validation** : une personne extérieure reproduit le pipeline en suivant uniquement le README.