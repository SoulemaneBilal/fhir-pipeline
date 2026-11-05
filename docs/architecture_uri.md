# Architecture des URI Canoniques et Systèmes d'Identifiants — Togo Health Data Pipeline

**Version** : 1.0.0
**Statut** : Validé / Opposable
**Date d'émission** : 2026-11-05
**Autorité nationale** : Ministère de la Santé, de l'Hygiène Publique et de l'Accès Universel aux Soins de la République Togolaise
**Cadre normatif** : HL7 FHIR R4, OpenHIE, OHDSI OMOP CDM 5.4, Décisions d'Architecture ADR D-08 & D-09

---

## 1. Contexte & Principes Directeurs

Le pipeline national de standardisation et d'interopérabilité des données de santé du Togo (`fhir-pipeline`) a pour mission de convertir des sources de données fragmentées et hétérogènes (fichiers tabulaires, registres papier numérisés, bases DHIS2, dossiers de consultation de dispensaires périphériques et de centres hospitaliers universitaires) vers un socle standardisé conforme aux spécifications HL7 FHIR R4 et OMOP CDM 5.4.

Au cœur de cette architecture se trouve la définition stricte et univoque des **URI canoniques** (*Uniform Resource Identifiers*) et des **espaces de noms d'identifiants** (*NamingSystems*). Conformément aux principes d'intégrité opérationnelle stipulés dans `AGENT.md` :

1. **Unicité et non-ambiguïté** : Chaque entité du système de santé togolais (patient, établissement, consultation, professionnel, district, région) est rattachée à un espace de noms d'identifiant formellement identifié par un URI immuable.
2. **Déterminisme et idempotence** : Les identifiants techniques sont générés de manière déterministe via UUID version 5 (`uuid.uuid5(UUID_NAMESPACE, ...)`), garantissant qu'une même entité source produit systématiquement le même identifiant FHIR sans dépendance à une horloge système ou un générateur pseudo-aléatoire non reproductible.
3. **Séparation des domaines** : Distinction rigoureuse entre les identifiants décentralisés (*NamingSystems* sous `/sid/`), les nomenclatures contrôlées locales (*CodeSystems* sous `/cs/`), les ensembles de valeurs admissibles (*ValueSets* sous `/vs/`), et les profils nationaux de contraintes (*StructureDefinitions* sous `/StructureDefinition/`).
4. **Alignement international sans perte clinique** : Préservation des identifiants et terminologies sources togolaises tout en assurant leur projection sans ambiguïté vers les ontologies médicales internationales de référence (CIM-10, SNOMED CT, LOINC, ATC, UCUM).

---

## 2. Autorité Racine et Hiérarchie Canonique

L'autorité d'interopérabilité sanitaire de la République Togolaise est matérialisée par l'URI canonique racine :

```text
http://interop-sante.gouv.tg/fhir
```

Tous les artefacts d'interopérabilité produits par le pipeline dérivent directement de cette racine selon une arborescence standardisée :

```text
http://interop-sante.gouv.tg/fhir/
├── sid/                         # Identifier Systems (NamingSystems)
│   ├── patient-mpi              # Identifiant Maître Patient (IUP / Splink)
│   ├── nni                      # Numéro National d'Identification civil
│   ├── patient-local            # Identifiant patient local (IPP établissement)
│   ├── facility                 # Identifiant national formation sanitaire (FOSA)
│   ├── district                 # Code district sanitaire (44 districts)
│   ├── region                   # Code région sanitaire (6 régions)
│   ├── encounter                # Numéro de visite / consultation / séjour
│   └── practitioner             # Identifiant du professionnel de santé
│
├── cs/                          # Local CodeSystems (Vocabulaires contrôlés)
│   ├── facility-category        # Niveaux pyramidaux (CHU, CHR, Hospital, CMS, USP)
│   ├── health-region            # Nomenclature des 6 régions sanitaires
│   ├── health-district          # Nomenclature des 44 districts sanitaires
│   ├── priority-pathology       # 9 pathologies prioritaires nationales
│   ├── pev-vaccines             # Vaccins du Programme Élargi de Vaccination
│   ├── local-clinical-terms     # Termes cliniques locaux en français libre
│   └── age-precision            # Précision sur date de naissance estimée
│
├── vs/                          # Local ValueSets (Jeux de valeurs autorisées)
│   ├── facility-category        # Ensemble des catégories de structures
│   ├── health-region            # Ensemble des 6 régions
│   ├── health-district          # Ensemble des 44 districts
│   ├── priority-pathology       # Ensemble des pathologies prioritaires
│   └── pev-vaccines             # Ensemble des vaccins PEV
│
└── StructureDefinition/         # Profils et Extensions FHIR Togo
    ├── togo-patient             # Profil Patient national
    ├── togo-encounter           # Profil Consultation / Séjour
    ├── togo-condition           # Profil Diagnostic / Problème de santé
    ├── togo-observation         # Profil Constante / Signe vital / Examen
    ├── togo-procedure           # Profil Acte médical / Chirurgie
    ├── togo-medication-request  # Profil Prescription médicamenteuse
    ├── togo-immunization        # Profil Vaccination
    ├── togo-organization        # Profil Structure de soins / Organisation
    ├── togo-location            # Profil Lieu géographique / Pavillon
    ├── estimated-age-precision  # Extension : précision d'âge estimé
    └── health-district-reference # Extension : rattachement au district
```

---

## 3. Spécification Détaillée des NamingSystems (Systèmes d'Identifiants)

Dans les ressources FHIR R4, l'élément `Identifier` associe un couple `(system, value)`. Les systèmes d'identifiants togolais sont définis comme suit :

### 3.1 Identifiants Patients

| Nom Technique | URI Canonique (`system`) | Description Clinique & Rôle | Format Attendu (`value`) | Exemple |
|---|---|---|---|---|
| **Patient MPI** | `http://interop-sante.gouv.tg/fhir/sid/patient-mpi` | Identifiant Unique Patient (IUP) déterministe issu de la réconciliation Splink / Record Linkage | UUID v5 canonique format RFC 4122 | `urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8` |
| **Numéro National d'Identification (NNI)** | `http://interop-sante.gouv.tg/fhir/sid/nni` | Numéro civil officiel de la carte d'identité togolaise ou du registre biométrique national | Numéro alphanumérique officiel | `TG-NNI-19880415-0042` |
| **Identifiant Local Patient** | `http://interop-sante.gouv.tg/fhir/sid/patient-local` | Identifiant Permanent du Patient (IPP) extrait du dossier médical ou du registre papier de la structure source | Chaîne locale propre à l'établissement | `IPP-2024-8841` |

### 3.2 Identifiants des Structures & Territoires

| Nom Technique | URI Canonique (`system`) | Description Clinique & Rôle | Format Attendu (`value`) | Exemple |
|---|---|---|---|---|
| **Formation Sanitaire (Facility)** | `http://interop-sante.gouv.tg/fhir/sid/facility` | Identifiant national unique de l'établissement de soins (FOSA) | Préfixe `TG-FAC-` suivi du code régional et numéro | `TG-FAC-LOM-001` (CHU Sylvanus Olympio) |
| **District Sanitaire** | `http://interop-sante.gouv.tg/fhir/sid/district` | Code officiel du district sanitaire parmi les 44 districts nationaux (ADR D-08) | Préfixe `TG-` suivi du code région et district | `TG-LOM-AGO` (Agoè-Nyivé), `TG-PLA-KLO` (Kloto) |
| **Région Sanitaire** | `http://interop-sante.gouv.tg/fhir/sid/region` | Code officiel de la région sanitaire parmi les 6 régions du Togo (ADR D-08) | Code court ISO/National à 6 valeurs | `TG-SAV`, `TG-KAR`, `TG-CEN`, `TG-PLA`, `TG-MAR`, `TG-LOM` |

### 3.3 Identifiants d'Activité et des Professionnels

| Nom Technique | URI Canonique (`system`) | Description Clinique & Rôle | Format Attendu (`value`) | Exemple |
|---|---|---|---|---|
| **Encounter (Visite / Séjour)** | `http://interop-sante.gouv.tg/fhir/sid/encounter` | Identifiant unique de consultation externe, hospitalisation ou passage aux urgences | Préfixe d'établissement et numéro de consultation | `TG-ENC-2026-LOM001-09412` |
| **Practitioner (Praticien)** | `http://interop-sante.gouv.tg/fhir/sid/practitioner` | Numéro d'enregistrement du médecin, infirmier ou sage-femme au tableau de l'Ordre ou du Ministère | Numéro d'Ordre ou matricule fonction publique | `TG-MED-4412-ONMT` |

---

## 4. Spécification des CodeSystems Locaux

Les nomenclatures contrôlées nationales sont publiées sous forme de `CodeSystem` FHIR R4 autonomes.

### 4.1 Pyramide Sanitaire (`.../cs/facility-category`)
- **URI** : `http://interop-sante.gouv.tg/fhir/cs/facility-category`
- **Titre** : Catégories et Niveaux Opérationnels de la Pyramide Sanitaire Togolaise
- **Codes autorisés** :
  - `CHU` : Centre Hospitalier Universitaire (Niveau 4 - Tertiaire national)
  - `CHR` : Centre Hospitalier Régional (Niveau 3 - Secondaire régional)
  - `Hospital` : Hôpital de District / Centre Hospitalier Préfectoral - CHP (Niveau 2 - Primaire de référence)
  - `CMS` : Centre Médico-Social (Niveau 1 - Périphérique primaire)
  - `USP` : Unité de Soins Périphérique Type I ou II (Niveau 1 - Périphérique de premier contact)

### 4.2 Régions Sanitaires (`.../cs/health-region`)
- **URI** : `http://interop-sante.gouv.tg/fhir/cs/health-region`
- **Titre** : Nomenclature Officielle des 6 Régions Sanitaires du Togo (ADR D-08)
- **Codes autorisés** :
  - `TG-SAV` : Région des Savanes (Chef-lieu : Dapaong, 7 districts)
  - `TG-KAR` : Région de la Kara (Chef-lieu : Kara, 7 districts)
  - `TG-CEN` : Région Centrale (Chef-lieu : Sokodé, 5 districts)
  - `TG-PLA` : Région des Plateaux (Chef-lieu : Atakpamé, 12 districts)
  - `TG-MAR` : Région Maritime (Chef-lieu : Tsévié, 6 districts)
  - `TG-LOM` : Région du Grand Lomé (Chef-lieu : Lomé, 7 districts)

### 4.3 Districts Sanitaires (`.../cs/health-district`)
- **URI** : `http://interop-sante.gouv.tg/fhir/cs/health-district`
- **Titre** : Répertoire Officiel des 44 Districts Sanitaires du Togo (ADR D-08)
- **Codes autorisés** : 44 codes uniques normés (ex. `TG-SAV-CIN`, `TG-KAR-KOZ`, `TG-CEN-TCJ`, `TG-PLA-KLO`, `TG-MAR-ZIO`, `TG-LOM-AGO`...).

### 4.4 Pathologies Prioritaires Nationales (`.../cs/priority-pathology`)
- **URI** : `http://interop-sante.gouv.tg/fhir/cs/priority-pathology`
- **Titre** : Catalogue des 9 Pathologies Prioritaires de la République Togolaise
- **Codes autorisés** :
  - `MALARIA` : Paludisme (accès simple, grave, congénital)
  - `ARI` : Infections Respiratoires Aiguës (IRA, pneumonies, bronchites)
  - `DIARRHEA` : Maladies Diarrhéiques et Gastro-entérites aiguës (choléra, dysenterie)
  - `HIV` : Infection par le VIH / SIDA et coinfections associées
  - `TB` : Tuberculose (pulmonaire, extra-pulmonaire, multirésistante)
  - `HTA` : Hypertension Artérielle et complications cardiovasculaires
  - `DIABETES` : Diabète de type 1 et 2, complications métaboliques
  - `SMI` : Santé Maternelle et Infantile (grossesse, accouchement, césarienne, post-partum)
  - `MALNUTRITION` : Malnutrition aiguë sévère (MAS) et modérée (MAM), carences micronutritionnelles

### 4.5 Vaccins du Programme Élargi de Vaccination (`.../cs/pev-vaccines`)
- **URI** : `http://interop-sante.gouv.tg/fhir/cs/pev-vaccines`
- **Titre** : Nomenclature des Antigènes du Programme Élargi de Vaccination du Togo
- **Codes autorisés** : `BCG`, `VPO`, `VPI`, `PENTA`, `PCV13`, `ROTA`, `RR`, `VAA`, `MEN-A`, `VPH`, `COVID19`.

### 4.6 Précision d'Âge Estimé (`.../cs/age-precision`)
- **URI** : `http://interop-sante.gouv.tg/fhir/cs/age-precision`
- **Titre** : Qualification de la précision des dates de naissance déclarées sans état civil exact
- **Codes autorisés** : `EXACT` (jour/mois/année connus), `YEAR_ONLY` (année seule déclarée), `ESTIMATED` (âge estimé par examen clinique ou morphologique).

---

## 5. Spécification des ValueSets Locaux

Les jeux de valeurs (*ValueSets*) regroupent les concepts admissibles pour les éléments codés des profils FHIR :

| Nom Technique | URI Canonique (`url`) | CodeSystem Source Inclus | Usage Principal |
|---|---|---|---|
| **VS Catégorie Établissement** | `http://interop-sante.gouv.tg/fhir/vs/facility-category` | `.../cs/facility-category` | `Location.type`, `Organization.type` |
| **VS Régions Sanitaires** | `http://interop-sante.gouv.tg/fhir/vs/health-region` | `.../cs/health-region` | `Location.address.state` |
| **VS Districts Sanitaires** | `http://interop-sante.gouv.tg/fhir/vs/health-district` | `.../cs/health-district` | `Location.address.district`, extension district |
| **VS Pathologies Prioritaires** | `http://interop-sante.gouv.tg/fhir/vs/priority-pathology` | `.../cs/priority-pathology` | `Condition.code` |
| **VS Vaccins PEV** | `http://interop-sante.gouv.tg/fhir/vs/pev-vaccines` | `.../cs/pev-vaccines` | `Immunization.vaccineCode` |

---

## 6. Profils Nationaux StructureDefinition (IG FHIR Togo)

Le guide d'implémentation national (*Implementation Guide*) définit des profils dérivés des ressources FHIR de base :

| Profil National | URI Canonique (`url`) | Ressource de Base | Rôle dans le Pipeline |
|---|---|---|---|
| **TogoPatient** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-patient` | `Patient` | Identifiants MPI + local, nom usuel, genre, date de naissance avec extension de précision |
| **TogoEncounter** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-encounter` | `Encounter` | Consultation, statut, période, motif de consultation, référence établissement |
| **TogoCondition** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-condition` | `Condition` | Diagnostic clinique, double codage (local + CIM-10 / SNOMED CT) |
| **TogoObservation** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-observation` | `Observation` | Constante vitale, biologie (LOINC + UCUM), statut d'interprétation |
| **TogoProcedure** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-procedure` | `Procedure` | Acte de soins, accouchement, césarienne, geste technique |
| **TogoMedicationRequest** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-medication-request` | `MedicationRequest` | Prescription de médicament essentiel (codification ATC) |
| **TogoImmunization** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-immunization` | `Immunization` | Administration vaccinale PEV, numéro de dose, numéro de lot |
| **TogoOrganization** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-organization` | `Organization` | Entité administrative hospitalière, rattachement hiérarchique |
| **TogoLocation** | `http://interop-sante.gouv.tg/fhir/StructureDefinition/togo-location` | `Location` | Coordonnées GPS, district, région, niveau de pyramide sanitaire |

### Extensions Spécifiques

- **Précision d'âge** : `http://interop-sante.gouv.tg/fhir/StructureDefinition/estimated-age-precision`
  *Contexte d'application* : `Patient.birthDate`
  *Type de valeur* : `CodeableConcept` lié à `.../cs/age-precision`.
- **Rattachement District** : `http://interop-sante.gouv.tg/fhir/StructureDefinition/health-district-reference`
  *Contexte d'application* : `Location`, `Patient.address`
  *Type de valeur* : `Reference(Location)` ou `Coding` lié à `.../cs/health-district`.

---

## 7. Systèmes Terminologiques Internationaux Standards

Le pipeline assure l'alignement sémantique vers les terminologies mondiales standards de l'OMOP CDM et de HL7 FHIR :

| Système Standard | URI Canonique Officielle | Domaine Clinique | Format de Code |
|---|---|---|---|
| **CIM-10 (ICD-10)** | `http://hl7.org/fhir/sid/icd-10` | Diagnostics et morbidités (Condition) | Codes alphanumériques avec point (ex. `B50.9`, `J06.9`, `I10`) |
| **SNOMED CT** | `http://snomed.info/sct` | Concepts cliniques, signes, procédures | Identifiants numériques SCTID (ex. `38362002`, `205237003`) |
| **LOINC** | `http://loinc.org` | Examens de laboratoire, mesures, constantes | Codes avec tiret de contrôle (ex. `8480-6`, `1558-6`, `59408-5`) |
| **ATC** | `http://www.whocc.no/atc` | Médicaments et principes actifs (5e niveau) | Codes alphanumériques 7 caractères (ex. `P01BF01`, `J05AR13`) |
| **UCUM** | `http://unitsofmeasure.org` | Unités de mesure standardisées | Expressions syntaxiques UCUM (ex. `mm[Hg]`, `g/dL`, `Cel`, `kg`) |

---

## 8. Accès Programmatique Python (`src/terminology/uris.py`)

L'ensemble de ces constantes, énumérations et fonctions d'utilité est exposé programmatiquement dans le module Python `src/terminology/uris.py`.

### 8.1 Exemple d'Utilisation : Génération d'un Identifiant Patient

```python
from src.terminology.uris import URI_PATIENT_MPI, URI_PATIENT_LOCAL

fhir_patient_identifier_mpi = {
    "use": "official",
    "system": URI_PATIENT_MPI,
    "value": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
}

fhir_patient_identifier_local = {
    "use": "secondary",
    "system": URI_PATIENT_LOCAL,
    "value": "IPP-2026-0042",
}
```

### 8.2 Exemple d'Utilisation : Codification d'un Diagnostic de Paludisme

```python
from src.terminology.uris import URI_CS_PRIORITY_PATHOLOGY, URI_ICD10, URI_SNOMED_CT

coding_condition = [
    {
        "system": URI_CS_PRIORITY_PATHOLOGY,
        "code": "MALARIA",
        "display": "Paludisme",
    },
    {
        "system": URI_ICD10,
        "code": "B50.9",
        "display": "Plasmodium falciparum malaria, unspecified",
    },
    {
        "system": URI_SNOMED_CT,
        "code": "38362002",
        "display": "Malaria",
    },
]
```

### 8.3 Exemple d'Utilisation : Fonctions Utilitaires

```python
from src.terminology.uris import (
    get_identifier_system,
    is_togo_authority_uri,
    validate_canonical_uri,
)

# Résolution flexible par alias
sys_mpi = get_identifier_system("mpi")  # "http://interop-sante.gouv.tg/fhir/sid/patient-mpi"
sys_fac = get_identifier_system("facility")  # "http://interop-sante.gouv.tg/fhir/sid/facility"

# Validation
assert is_togo_authority_uri(sys_mpi) is True
assert validate_canonical_uri("http://loinc.org") is True
assert validate_canonical_uri("http://inconnu.org/code") is False
```

---

## 9. Matrice de Conformité et Traçabilité

| Exigence Spécifiée | Référence Source | Implémentation / Fichier | Statut |
|---|---|---|---|
| Espace canonique national `http://interop-sante.gouv.tg/fhir` | `ORIGINAL_REQUEST.md:104` | `docs/architecture_uri.md:27`, `src/terminology/uris.py:BASE_URI` | Conforme |
| SIDs pour IUP, local, national, FOSA, district, région, visite | `ORIGINAL_REQUEST.md:104`, ADR D-08 | `docs/architecture_uri.md:73`, `src/terminology/uris.py:URI_*` | Conforme |
| CodeSystems locaux (catégories, 6 régions, 44 districts, 9 pathologies) | `ORIGINAL_REQUEST.md:104`, ADR D-08 | `docs/architecture_uri.md:120`, `src/terminology/uris.py:URI_CS_*` | Conforme |
| Terminologies cibles (CIM-10, SNOMED, LOINC, ATC, UCUM) | `ORIGINAL_REQUEST.md:110` | `docs/architecture_uri.md:225`, `src/terminology/uris.py:URI_ICD10...` | Conforme |
| Documentation opposable dédiée | `ORIGINAL_REQUEST.md:105` | `docs/architecture_uri.md` | Conforme |
| Module programmatique avec typage et Enums | `ORIGINAL_REQUEST.md:105` | `src/terminology/uris.py` | Conforme |
| Suite de tests d'intégrité des URIs | `ORIGINAL_REQUEST.md:120` | `tests/test_uris.py` | Conforme |
