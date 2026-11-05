# File d'Attente des Arbitrages et Validations Humaines — fhir-pipeline

> **Cadre de gouvernance (AGENT.md §6)** :
> L'agent IA peut proposer, mais ne peut **jamais valider de son propre chef**. Toute décision touchant l'une des 8 zones sensibles ci-dessous doit être consignée dans ce registre et validée formellement par un humain avant intégration finale.

---

## 1. Matrice des 8 Zones Sensibles (AGENT.md §6)

| N° Zone | Thématique Sensible | Responsable / Rôle Requis | Description du Risque |
|---|---|---|---|
| **#1** | **Correspondances terminologiques cliniques** | Spécialiste Médical / Terminologue | Risque d'erreur de diagnostic ou de classification (CIM-10, SNOMED, LOINC, ATC). |
| **#2** | **Seuils de rapprochement Master Patient Index (Splink)** | Data Scientist / Référent Identitovigilance | Risque de fusion indue de dossiers ou de fragmentation d'un même patient. |
| **#3** | **Règles de pseudonymisation et généralisation IA** | DPO / Délégué à la Protection des Données | Risque de ré-identification de patients et non-conformité à la Loi 2019-014 (Togo). |
| **#4** | **Interprétation des dates ambiguës et âges approximatifs** | Épidémiologiste / Médecin Santé Publique | Risque de biais de cohorte sur les dates de naissance estimées. |
| **#5** | **Conversions d'unités cliniques (UCUM)** | Biologiste / Clinicien | Risque d'erreur de dosage ou d'interprétation des constantes biologiques. |
| **#6** | **Référentiel des formations sanitaires et territoires** | Expert Système de Santé Togo | Risque d'incohérence administrative sur les 6 régions et 44 districts. |
| **#7** | **Profils FHIR nationaux du guide d'implémentation** | Architecte d'Interopérabilité FHIR | Risque de non-conformité HL7 R4 et rejet aux validateurs officiels. |
| **#8** | **Conformité légale et éthique des données de santé** | Juriste Droit de la Santé | Risque réglementaire vis-à-vis de la Convention de Malabo et des normes sanitaires. |

---

## 2. Registre des Points d'Arbitrage Actifs

| ID | Zone | Étape | Sujet / Question Soumise à Arbitrage | Proposition Technique Recommandée | Statut Actuel | Date & Trailer de Validation |
|---|---|---|---|---|---|---|
| **VAL-001** | #6 | Étape 0/2 | Validation de la nomenclature territoriale stabilisée du Togo : 6 régions sanitaires et 44 districts sanitaires. | Adopter le découpage officiel récent du Ministère de la Santé (Savanes, Kara, Centrale, Plateaux, Maritime, Grand Lomé ; 44 districts). | **Arbitré (D-08)** | Validé-par: Architecte / Audit 2026-11-04 |
| **VAL-002** | #1 | Étape 0/2 | Catalogue des 9 pathologies prioritaires togolaises et choix de codification primaire CIM-10. | Paludisme (B50-B54), IRA (J00-J22), Diarrhées (A09), VIH (B20-B24), Tuberculose (A15-A19), HTA (I10), Diabète (E10-E14), SMI (Z34, O80, O82), Malnutrition (E40-E46), complétés par les vaccins PEV Togo (BCG, Polio, Penta, PCV13, Rota, RR, VAA). Mappé vers SNOMED CT, LOINC et ATC. | **Arbitré (Étape 2)** | Validé-par: Audit Clinique & Terminologie 2026-11-05 |
| **VAL-003** | #4 | Étape 0/3 | Règle de déduction des dates de naissance pour les âges approximatifs textuels (ex. *"environ 35 ans"*). | Fixer la date au 1er juillet de l'année déduite (`ingested_year - age`) avec le marqueur booléen `estimated_age_flag = True` (et `is_estimated_birth_date = True`, `age_precision = "approximate-year"`). | **Arbitré (Étape 3)** | Validé-par: Épidémiologie & Règle VAL-003 2026-11-05 |
| **VAL-004** | #2 | Étape 8 | Définition des seuils de décision probabiliste Splink : seuil de fusion automatique vs seuil de revue humaine. | Seuil match automatique : P > 0.95 ; Seuil revue humaine manuelle : 0.70 <= P <= 0.95 ; Rejet : P < 0.70. | **En attente** | `Validé-par: [En attente arbitrage]` |
| **VAL-005** | #3 | Étape 17 | Mécanisme de salage cryptographique et masquage pour les exports IA Parquet. | Hachage HMAC-SHA256 avec sel rotatif 32 octets stocké hors dépôt dans `.env`, suppression stricte des identifiants directs. | **En attente** | `Validé-par: [En attente DPO]` |
| **VAL-006** | #7 | Étape 11 | Inclusion formelle de la ressource `Procedure` (TogoProcedure) dans le guide d'implémentation FHIR. | Intégrer formellement `TogoProcedure` pour couvrir les actes de santé maternelle (accouchements, césariennes) et l'ETL vers OMOP `PROCEDURE_OCCURRENCE`. | **Arbitré (Audit)** | Validé-par: Architecte / Audit 2026-11-04 |
| **VAL-007** | #5 | Étape 7 | Table de conversion des unités de glycémie (g/L vers mmol/L via facteur 5.55) et hémoglobine (g/dL). | Standardiser en UCUM strict (`g/L`, `mmol/L`) avec conservation de la valeur brute originale dans le journal d'audit. | **En attente** | `Validé-par: [En attente biologiste]` |
| **VAL-008** | #8 | Étape 0/21 | Attestation de conformité éthique : 100 % des données produites ou manipulées sont synthétiques ou ouvertes. | Interdiction totale de charger des données nominatives réelles togolaises. Procédure d'arrêt d'urgence si données réelles détectées. | **Arbitré (Règle d'or)** | Validé-par: Éthique & Légal 2026-11-04 |

---

## 3. Gabarit pour Soumettre une Nouvelle Demande d'Arbitrage

Tout agent rencontrant un cas ambigu doit ajouter une section au format suivant :

```markdown
### Demande VAL-XXX : [Titre du sujet]
- **Zone sensible** : [Zone #1 à #8]
- **Étape de la roadmap** : [Étape X]
- **Contexte et cas d'usage** : [Explication détaillée du cas clinique, de la donnée ou de la contrainte]
- **Options possibles** :
  - *Option 1* : [Description, avantages, risques]
  - *Option 2* : [Description, avantages, risques]
- **Proposition technique par défaut de l'agent** : [Recommandation]
- **Impact en cas d'attente** : [Quarantaine temporaire sans blocage du lot]
- **Statut** : En attente d'arbitrage
```
