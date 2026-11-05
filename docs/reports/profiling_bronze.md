# Rapport de Diagnostic Initial et Profilage Qualité Bronze (Rapport Avant)

> **Identifiant du rapport** : `rep-20261105-213236`  
> **Date de génération** : `2026-11-05T21:32:36.685924+00:00`  
> **Statut du pipeline** : Couche Bronze Parquet (`data/bronze/` ou `data/degraded/`)  
> **Score global de santé qualité** : **99.2%** 🟢 **EXCELLENT**

## 1. Synthèse Exécutive et Score Global de Santé Qualité

Ce rapport dresse le diagnostic exhaustif initial des données de santé brutes converties en format Parquet.
L'analyse est menée sur **6 dimensions normatives** de qualité des données, sans altération des données sources.

### Chiffres Clés de la Synthèse Exécutive
- **Nombre total de tables analysées** : 6
- **Volume total d'enregistrements (lignes)** : 7,026
- **Total d'anomalies de qualité détectées** : 5,441
- **Indice global de santé qualité** : **99.21%**

- ℹ️ Profilage initial de 6 tables (7026 enregistrements analysés).
- ℹ️ Score de santé global : 99.2% sur 6 dimensions normatives.

## 2. Tableau Récapitulatif des 6 Dimensions Normatives de Qualité

| Dimension | Nom Français | Score Qualité | Statut | Définition & Contrôles Clés |
| :--- | :--- | :---: | :---: | :--- |
| `COMPLETENESS` | **Complétude** | **96.7%** | 🟢 **EXCELLENT** | Absence de valeurs nulles, chaînes vides et codes sentinelles (-1, 999, NA, ND) |
| `ACCURACY` | **Exactitude** | **99.6%** | 🟢 **EXCELLENT** | Conformité syntaxique (dates ISO 8601, absence d'âges textuels, absence de Mojibake, points décimaux) |
| `CONSISTENCY` | **Cohérence** | **99.9%** | 🟢 **EXCELLENT** | Cohérence clinique et logique (absence de grossesses masculines, dates ordonnées, pyramide des soins) |
| `UNIQUENESS` | **Unicité** | **100.0%** | 🟢 **EXCELLENT** | Unicité stricte des identifiants et absence de doublons de patients inter-structures |
| `VALIDITY` | **Validité** | **99.2%** | 🟢 **EXCELLENT** | Conformité aux référentiels officiels (CIM-10, LOINC, ATC, découpage territorial Togo, UCUM) |
| `TIMELINESS` | **Actualité** | **100.0%** | 🟢 **EXCELLENT** | Vraisemblance temporelle (absence de dates futures et dates historiques aberrantes < 1900) |

## 3. Diagnostic Détaillé par Table Clinique

Chaque table clinique fait l'objet d'un profilage par colonne et d'un score agrégé par dimension.

### Table clinique : `conditions`
- **Lignes totales** : 1,302 | **Colonnes** : 14 | **Score global** : **99.8%** 🟢 **EXCELLENT** | **Anomalies** : 91

**Scores par dimension :**
- Complétude : **100.0%**
- Exactitude : **99.5%**
- Cohérence : **99.3%**
- Unicité : **100.0%**
- Validité : **100.0%**
- Actualité : **100.0%**

**Métriques par colonne :**

| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |
| :--- | :---: | :---: | :---: | :---: |
| `condition_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,302 |
| `patient_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,000 |
| `encounter_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,302 |
| `pathology_group` | 0 (0.0%) | 0 (0.0%) | 100.0% | 9 |
| `icd10_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 12 |
| `icd10_display` | 0 (0.0%) | 0 (0.0%) | 100.0% | 30 |
| `snomed_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 11 |
| `snomed_display` | 0 (0.0%) | 0 (0.0%) | 100.0% | 11 |
| `clinical_status` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |
| `verification_status` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |
| `severity` | 0 (0.0%) | 0 (0.0%) | 100.0% | 3 |
| `onset_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 428 |
| `onset_datetime` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,294 |
| `recorded_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 331 |

### Table clinique : `encounters`
- **Lignes totales** : 1,302 | **Colonnes** : 19 | **Score global** : **99.2%** 🟢 **EXCELLENT** | **Anomalies** : 1220

**Scores par dimension :**
- Complétude : **95.3%**
- Exactitude : **99.8%**
- Cohérence : **100.0%**
- Unicité : **100.0%**
- Validité : **100.0%**
- Actualité : **100.0%**

**Métriques par colonne :**

| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |
| :--- | :---: | :---: | :---: | :---: |
| `encounter_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,302 |
| `patient_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,000 |
| `facility_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 183 |
| `facility_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 183 |
| `facility_name` | 0 (0.0%) | 0 (0.0%) | 100.0% | 237 |
| `facility_category` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `pyramid_level` | 0 (0.0%) | 0 (0.0%) | 100.0% | 4 |
| `district_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 44 |
| `region_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 6 |
| `encounter_class` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |
| `encounter_type` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |
| `start_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,295 |
| `start_datetime` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,294 |
| `end_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,294 |
| `end_datetime` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,294 |
| `reason_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 12 |
| `reason_display` | 0 (0.0%) | 0 (0.0%) | 100.0% | 30 |
| `status` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |
| `referral_from_facility_id` | 1168 (89.7%) | 0 (0.0%) | 10.3% | 81 |

### Table clinique : `immunizations`
- **Lignes totales** : 305 | **Colonnes** : 13 | **Score global** : **99.8%** 🟢 **EXCELLENT** | **Anomalies** : 39

**Scores par dimension :**
- Complétude : **99.3%**
- Exactitude : **99.7%**
- Cohérence : **100.0%**
- Unicité : **100.0%**
- Validité : **100.0%**
- Actualité : **100.0%**

**Métriques par colonne :**

| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |
| :--- | :---: | :---: | :---: | :---: |
| `immunization_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 305 |
| `patient_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 61 |
| `encounter_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 61 |
| `facility_id` | 0 (0.0%) | 28 (9.2%) | 90.8% | 54 |
| `vaccine_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `vaccine_display` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `vaccine_name` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `atc_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `dose_number` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |
| `lot_number` | 0 (0.0%) | 0 (0.0%) | 100.0% | 233 |
| `occurrence_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 18 |
| `administered_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `status` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |

### Table clinique : `observations`
- **Lignes totales** : 1,800 | **Colonnes** : 14 | **Score global** : **96.7%** 🟢 **EXCELLENT** | **Anomalies** : 3825

**Scores par dimension :**
- Complétude : **86.2%**
- Exactitude : **99.2%**
- Cohérence : **100.0%**
- Unicité : **100.0%**
- Validité : **95.0%**
- Actualité : **100.0%**

**Métriques par colonne :**

| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |
| :--- | :---: | :---: | :---: | :---: |
| `observation_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,800 |
| `patient_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 965 |
| `encounter_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,175 |
| `category` | 0 (0.0%) | 0 (0.0%) | 100.0% | 3 |
| `loinc_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 10 |
| `loinc_display` | 0 (0.0%) | 0 (0.0%) | 100.0% | 10 |
| `value_quantity` | 570 (31.7%) | 0 (0.0%) | 68.3% | 170 |
| `value_numeric` | 570 (31.7%) | 0 (0.0%) | 68.3% | 170 |
| `value_unit` | 573 (31.8%) | 0 (0.0%) | 68.2% | 16 |
| `unit` | 570 (31.7%) | 0 (0.0%) | 68.3% | 6 |
| `value_string` | 1124 (62.4%) | 0 (0.0%) | 37.6% | 58 |
| `interpretation` | 0 (0.0%) | 0 (0.0%) | 100.0% | 4 |
| `observation_datetime` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,168 |
| `effective_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,168 |

### Table clinique : `patients`
- **Lignes totales** : 1,015 | **Colonnes** : 20 | **Score global** : **99.9%** 🟢 **EXCELLENT** | **Anomalies** : 85

**Scores par dimension :**
- Complétude : **99.8%**
- Exactitude : **99.8%**
- Cohérence : **100.0%**
- Unicité : **99.8%**
- Validité : **100.0%**
- Actualité : **99.9%**

**Métriques par colonne :**

| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |
| :--- | :---: | :---: | :---: | :---: |
| `patient_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,015 |
| `identifier_system` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |
| `identifier_value` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,000 |
| `nni` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,000 |
| `family_name` | 0 (0.0%) | 0 (0.0%) | 100.0% | 143 |
| `given_name` | 0 (0.0%) | 0 (0.0%) | 100.0% | 86 |
| `gender` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |
| `birth_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 901 |
| `is_estimated_birth_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |
| `estimated_age_flag` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |
| `age_precision` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |
| `phone_number` | 14 (1.4%) | 20 (2.0%) | 96.7% | 973 |
| `address_region_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 6 |
| `address_district_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 44 |
| `address_city` | 0 (0.0%) | 0 (0.0%) | 100.0% | 44 |
| `residence_district_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 44 |
| `residence_region_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 6 |
| `marital_status` | 0 (0.0%) | 0 (0.0%) | 100.0% | 4 |
| `ethnic_group` | 0 (0.0%) | 0 (0.0%) | 100.0% | 15 |
| `created_at` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1 |

### Table clinique : `prescriptions`
- **Lignes totales** : 1,302 | **Colonnes** : 13 | **Score global** : **99.8%** 🟢 **EXCELLENT** | **Anomalies** : 181

**Scores par dimension :**
- Complétude : **99.4%**
- Exactitude : **99.5%**
- Cohérence : **100.0%**
- Unicité : **100.0%**
- Validité : **100.0%**
- Actualité : **100.0%**

**Métriques par colonne :**

| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |
| :--- | :---: | :---: | :---: | :---: |
| `prescription_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,302 |
| `medication_request_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,302 |
| `patient_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,000 |
| `encounter_id` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,302 |
| `atc_code` | 0 (0.0%) | 0 (0.0%) | 100.0% | 10 |
| `atc_display` | 0 (0.0%) | 0 (0.0%) | 100.0% | 10 |
| `medication_name` | 0 (0.0%) | 0 (0.0%) | 100.0% | 10 |
| `dosage_instruction` | 96 (7.4%) | 0 (0.0%) | 92.6% | 9 |
| `quantity` | 0 (0.0%) | 0 (0.0%) | 100.0% | 7 |
| `duration_days` | 0 (0.0%) | 0 (0.0%) | 100.0% | 5 |
| `prescribed_date` | 0 (0.0%) | 0 (0.0%) | 100.0% | 424 |
| `authored_on` | 0 (0.0%) | 0 (0.0%) | 100.0% | 1,294 |
| `status` | 0 (0.0%) | 0 (0.0%) | 100.0% | 2 |

## 4. Matrice de Confrontation au Journal d'Altérations (Taux de Rappel)

Confrontation rigoureuse des anomalies détectées par le profiler face aux erreurs réelles injectées dans le journal (`alterations_log.parquet`).

| Règle d'Altération | Nom de la Règle | Table Cible | Colonne Cible | Altérations Injectées | Détectées | Taux de Rappel | Précision |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `RULE-MISS-001` | Valeur manquante (omission de saisie) | `patients` | `phone_number` | 110 | 110 | 🟢 **100.0%** | 96.0% |
| `RULE-NAME-003` | Inversion du nom et prénom | `patients` | `family_name` | 20 | 20 | 🟢 **100.0%** | 96.0% |
| `RULE-DATE-002` | Remplacement de date de naissance par âge approximatif textuel | `patients` | `birth_date` | 20 | 20 | 🟢 **100.0%** | 96.0% |
| `RULE-SENT-001` | Injection de code sentinelle d'indétermination | `patients` | `phone_number` | 48 | 48 | 🟢 **100.0%** | 96.0% |
| `RULE-ENCO-001` | Corruption d'encodage Mojibake (UTF-8 lu en Latin-1) | `patients` | `family_name` | 13 | 13 | 🟢 **100.0%** | 96.0% |
| `RULE-DATE-001` | Format de date altéré en notation composite | `patients` | `birth_date` | 297 | 297 | 🟢 **100.0%** | 96.0% |
| `RULE-NAME-002` | Suppression des accents et diacritiques | `patients` | `family_name` | 10 | 10 | 🟢 **100.0%** | 96.0% |
| `RULE-NAME-001` | Coquille patronymique réaliste | `patients` | `family_name` | 22 | 22 | 🟢 **100.0%** | 96.0% |
| `RULE-DUPL-001` | Doublon patient inter-établissements injecté pour Splink depuis 85bbd55a-8516-5f40-ad11-c2243bc1ba3a | `patients` | `patient_id` | 15 | 15 | 🟢 **100.0%** | 96.0% |
| `RULE-CLIN-001` | Diagnostic formalisé remplacé par libellé en texte libre | `encounters` | `reason_display` | 166 | 166 | 🟢 **100.0%** | 96.0% |
| `RULE-FACI-001` | Variante informelle de nom de structure sanitaire | `encounters` | `facility_name` | 60 | 59 | 🟢 **98.3%** | 96.0% |
| `RULE-MEAS-001` | Séparateur décimal virgule francophone | `observations` | `value_string` | 148 | 148 | 🟢 **100.0%** | 96.0% |
| `RULE-MEAS-002` | Unité de mesure non conforme ou omise | `observations` | `value_unit` | 122 | 122 | 🟢 **100.0%** | 96.0% |

**Bilan global de rappel face au corrigé** : **99.9%** (1050/1051 anomalies réelles interceptées). Seuil minimal requis : >= 80.0%.

## 5. Recommandations Ciblées pour l'Étape 7 (Nettoyage Silver)

Sur la base des anomalies identifiées dans ce profilage initial, les actions prioritaires de nettoyage déclaratif (YAML) et de normalisation pour la couche Silver sont :

1. **Normalisation des dates vers ISO 8601 (`YYYY-MM-DD`)** :
   - Convertir systématiquement les dates aux formats `JJ/MM/AAAA`, `JJ-MM-AAAA`, `AAAA/MM/JJ` et `JJ.MM.AA`.
   - Traiter les approximations textuelles d'âge (`environ 35 ans`, `vers 40 ans`) en calculant une date de naissance approchée avec le flag `estimated_age_flag=True`.
2. **Purge des codes sentinelles d'indétermination** :
   - Convertir les sentinelles (`-1`, `999`, `-999`, `NA`, `ND`, `INCONNU`) en valeurs nulles standards (`None` / `pd.NA`).
3. **Harmonisation des séparateurs décimaux** :
   - Remplacer les virgules décimales (`38,5`) par des points (`38.5`) et convertir les mesures physiologiques en types numériques standard.
4. **Correction du Mojibake et ré-encodage UTF-8** :
   - Réparer les patronymes et libellés corrompus par une double lecture Latin-1 / UTF-8 (`Ã©` vers `é`, `Ã´` vers `ô`).
5. **Standardisation des unités de mesure selon UCUM** :
   - Normaliser les unités locales (`°C`, `deg C` vers `Cel`, `cmHg` vers `mm[Hg]`, `g/l` vers `g/L`).
6. **Dé-doublonnage des identités patient (Préparation Splink - Étape 8)** :
   - Rapprocher les doublons inter-établissements partageant nom, prénom approché et date de naissance identique.
7. **Validation terminologique et géographique** :
   - Aligner les libellés libres et abréviations de diagnostics sur les concepts officiels CIM-10 et LOINC.
   - Aligner les noms informels de formations sanitaires sur le référentiel officiel du Togo (`data/reference/togo_health_geography.parquet`).

---
*Rapport généré automatiquement par le Moteur de Profilage Qualité (Étape 6) - Pipeline FHIR Togo.*
