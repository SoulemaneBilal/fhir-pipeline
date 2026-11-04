## **Définition du projet**

### **1\. Intitulé**

**Pipeline de standardisation et d’interopérabilité de données de santé : de sources fragmentées (DHIS2, Excel, systèmes propriétaires) vers FHIR R4, OpenHIE et OMOP CDM, avec un jeu de données propre et exportable pour l’IA.**

### **2\. Contexte et problème**

Dans la plupart des systèmes de santé d’Afrique de l’Ouest, dont le Togo, l’information de santé existe mais elle est **fragmentée, non standardisée et difficilement réutilisable** :

* **Sources hétérogènes** : agrégats mensuels DHIS2, fichiers Excel tenus par les formations sanitaires, logiciels propriétaires sans référentiel ni export documenté, registres papier saisis a posteriori.  
* **Absence d’identifiant patient unique** : un même patient apparaît dans plusieurs structures, avec des orthographes différentes, un âge approximatif plutôt qu’une date de naissance, et des noms issus de plusieurs langues locales (éwé, mina, kabiyè, etc.) ou translittérés.  
* **Libellés libres en français** : « palu simple », « Paludisme non compliqué », « PALUDISME », sans code CIM-10, SNOMED CT ou LOINC.  
* **Hiérarchie administrative et sanitaire instable** : noms de régions, de districts et de formations sanitaires écrits de plusieurs façons, sans identifiant partagé.  
* **Collecte intermittente** : saisie hors ligne, synchronisation tardive, doublons et conflits de versions.  
* **Données agrégées et données individuelles mélangées** : une donnée agrégée DHIS2 (nombre de cas) ne peut pas devenir un « Patient » FHIR. Elle devient un indicateur (`MeasureReport`) ou une observation de population, alors que les données de type tracker (individuelles) deviennent des ressources cliniques.  
* **Cadre légal et éthique** : la protection des données personnelles (loi togolaise sur les données à caractère personnel, convention de Malabo) impose pseudonymisation, minimisation et traçabilité.

### **3\. Enjeux**

1. **Interopérabilité nationale** : permettre à des systèmes qui ne se parlent pas d’échanger via un serveur FHIR et une couche d’interopérabilité de type OpenHIE.  
2. **Qualité et confiance** : mesurer objectivement la qualité des données avant et après, avec des indicateurs reproductibles.  
3. **Réutilisation scientifique** : produire une base **OMOP CDM** exploitable par les outils d’analyse OHDSI et par l’IA.  
4. **Contextualisation** : montrer qu’un standard conçu ailleurs (US Core, vocabulaires anglophones) peut être adapté au contexte togolais : français, géographie sanitaire locale, pathologies prioritaires.  
5. **Reproductibilité et honnêteté** : toutes les données du projet sont synthétiques ou publiques. Aucune donnée réelle de patient togolais n’est utilisée.

### **4\. Objectifs**

* **Principal** : transformer des données sources dégradées et hétérogènes, de contexte togolais, en ressources FHIR R4 valides, puis en base OMOP CDM, avec traçabilité complète.  
* **Secondaires** :  
  * Démontrer l’intégration dans une architecture OpenHIE (serveur FHIR, registre des formations, rapprochement de patients, service terminologique).  
  * Publier un **guide d’implémentation FHIR « Togo »** (profils et jeux de valeurs en français).  
  * Produire des exports tabulaires prêts pour l’apprentissage automatique au format Apache Parquet (cible prioritaire) et en export miroir dénormalisé CSV (cible secondaire), accompagnés d’une fiche de description du jeu de données (Datasheet).

### **5\. Périmètre**

**Inclus**

* Approche **généraliste**, avec un fil conducteur sur les pathologies fréquentes : paludisme, infections respiratoires, diarrhées, VIH, tuberculose, hypertension, diabète, santé maternelle et infantile, vaccination, malnutrition.  
* Sources : DHIS2 (agrégats issus de l'instance de démonstration publique et structures d'export), classeurs Excel complexes, CSV de dossiers hospitaliers propriétaires simulés, Bundles FHIR dégradés.  
* Cibles : serveur FHIR HAPI JPA (R4 4.0.1) sous passerelle OpenHIM, base OMOP CDM 5.4 (sur PostgreSQL conteneurisé), exports analytiques prioritaires au format Apache Parquet et exports miroirs dénormalisés au format CSV, et fichiers d'échange d'indicateurs conformes DHIS2 (ADX / dataValueSets JSON).  
* Langue : français en priorité, README et documentation bilingues (français d’abord).

**Exclus**

* Interface utilisateur graphique (UI), application clinique de saisie directe, entraînement effectif de modèles d’IA (le projet livre exclusivement les données préparées et typées), ingestion en streaming ou temps réel (fonctionnement strict par lots / batch en CLI Typer), et données réelles de patients togolais (100 % de données synthétiques ou publiques).

### **6\. Hypothèses d’interprétation (à corriger si faux)**

* « Libellés en français mais bien standardisés » : les **sources** contiennent des libellés français variables, et la **sortie** les relie à des codes standard tout en conservant un libellé français normalisé.  
* Données et vérité terrain : priorité absolue accordée au générateur contextuel Python (Voie B) reproduisant fidèlement la pyramide sanitaire togolaise (6 régions, 44 districts), la démographie, les pathologies cibles et les altérations réalistes. La voie Synthea adaptée (Voie A) est conservée en jalon d'extension ultérieur.

### **7\. Principes directeurs**

1. Les données brutes ne sont jamais modifiées.  
2. Chaque ressource produite est traçable jusqu’à la ligne source.  
3. Idempotence : identifiants déterministes (UUID v5), relancer ne crée pas de doublons.  
4. Chaque étape lit une couche et en écrit une autre, et se relance seule.  
5. Aucune décision clinique silencieuse : tout mapping incertain va en revue humaine, jamais deviné.  
6. Tout est mesuré : chaque règle de nettoyage a un test et une métrique.

### **8\. Critères de succès globaux**

* Taux de récupération mesuré contre la vérité terrain (ressources recréées correctement ou rejetées avec raison).  
* Zéro référence FHIR brisée dans la couche finale.  
* Validation FHIR sans erreur bloquante contre les profils Togo.  
* Base OMOP chargée avec un rapport de qualité (DQD) et un taux de mapping vers concepts standard publié.  
* Pipeline reproductible en une commande via Docker.  
* Documentation bilingue publiée sur GitHub.

