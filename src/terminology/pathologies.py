"""Catalogue des pathologies prioritaires du Togo et mock terminologique OHDSI OMOP CDM 5.4.

Conforme aux spécifications R3 d'ORIGINAL_REQUEST.md, PROJECT.md, ADR D-09 et VAL-002.
Fournit :
- L'inventaire des 9 pathologies prioritaires togolaises :
  Paludisme (Malaria), Infections Respiratoires Aiguës (IRA/ARI),
  Maladies diarrhéiques (Diarrhea), VIH/SIDA (HIV), Tuberculose (TB),
  Hypertension artérielle (HTA), Diabète (Diabetes), Santé maternelle et infantile (SMI),
  et Malnutrition (complétée par les vaccins essentiels PEV).
- Les cartographies vers CIM-10 (ICD-10), SNOMED CT, LOINC et ATC.
- La génération et validation du jeu de données mock Parquet Athena / OMOP CDM 5.4 (< 1 Mo).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Chemin par défaut du fichier Parquet mock terminologique (< 1 Mo, ADR D-09)
DEFAULT_VOCAB_PARQUET_PATH = Path("terminology/sample_vocabularies.parquet")

# 9 Pathologies prioritaires officielles du Togo (VAL-002, PROJECT.md)
PRIORITY_PATHOLOGY_GROUPS: list[str] = [
    "Malaria",
    "ARI",
    "Diarrhea",
    "HIV",
    "TB",
    "HTA",
    "Diabetes",
    "SMI",
    "Malnutrition",
]

# Vocabulaires standards pivots obligatoires
STANDARD_VOCABULARIES: set[str] = {"ICD10", "SNOMED", "LOINC", "ATC"}

# Domaines OMOP valides
VALID_OMOP_DOMAINS: set[str] = {
    "Condition",
    "Measurement",
    "Observation",
    "Drug",
    "Procedure",
}

# Catalogue structuré des pathologies prioritaires et leurs alignements
PRIORITY_PATHOLOGIES_CATALOG: dict[str, dict[str, Any]] = {
    "Malaria": {
        "code": "Malaria",
        "name_fr": "Paludisme",
        "name_en": "Malaria",
        "category": "Maladie infectieuse parasitaire endémique",
        "description": (
            "Première cause de morbidité et de mortalité infanto-juvénile au Togo. "
            "Diagnostics CIM-10 B50-B54, TDR antigène HRP2 (LOINC 58900-2) et ACT (ATC P01BF01)."
        ),
        "icd10": [
            {
                "code": "B50.9",
                "name": "Plasmodium falciparum malaria, unspecified",
                "french_name": "Paludisme à Plasmodium falciparum sans complication",
            },
            {
                "code": "B50.0",
                "name": "Plasmodium falciparum malaria with cerebral complications",
                "french_name": "Paludisme grave avec complications cérébrales",
            },
            {
                "code": "B54",
                "name": "Unspecified malaria",
                "french_name": "Paludisme sans précision",
            },
        ],
        "snomed": [
            {
                "code": "61462000",
                "name": "Malaria",
                "french_name": "Paludisme (Concept standard)",
            },
            {
                "code": "240742007",
                "name": "Plasmodium falciparum infection",
                "french_name": "Infection à Plasmodium falciparum",
            },
        ],
        "loinc": [
            {
                "code": "8310-5",
                "name": "Body temperature",
                "french_name": "Température corporelle",
            },
            {
                "code": "58900-2",
                "name": "Plasmodium falciparum antigen [Presence] in Blood by Rapid immunoassay",
                "french_name": "Test de Diagnostic Rapide (TDR) Paludisme",
            },
            {
                "code": "718-7",
                "name": "Hemoglobin [Mass/volume] in Blood",
                "french_name": "Taux d'hémoglobine",
            },
        ],
        "atc": [
            {
                "code": "P01BF01",
                "name": "artemether and lumefantrine",
                "french_name": "Artéméther et luméfantrine (ACT)",
            },
            {
                "code": "P01BE03",
                "name": "artesunate",
                "french_name": "Artésunate injectable (paludisme grave)",
            },
            {
                "code": "P01BD51",
                "name": "sulfadoxine and pyrimethamine",
                "french_name": "Sulfadoxine-pyriméthamine (TPI grossesse)",
            },
        ],
    },
    "ARI": {
        "code": "ARI",
        "name_fr": "Infections Respiratoires Aiguës (IRA)",
        "name_en": "Acute Respiratory Infections",
        "category": "Infection respiratoire aiguë haute et basse",
        "description": (
            "Cause majeure de consultation pédiatrique au Togo. Pneumonies et bronchites aiguës "
            "(CIM-10 J18.9, J20.9), surveillance SpO2 (LOINC 59408-5), antibiothérapie Amoxicilline (ATC J01CA04)."
        ),
        "icd10": [
            {
                "code": "J18.9",
                "name": "Pneumonia, unspecified",
                "french_name": "Pneumopathie aiguë sans précision",
            },
            {
                "code": "J20.9",
                "name": "Acute bronchitis, unspecified",
                "french_name": "Bronchite aiguë sans précision",
            },
            {
                "code": "J06.9",
                "name": "Acute upper respiratory infection, unspecified",
                "french_name": "Infection aiguë des voies respiratoires supérieures",
            },
        ],
        "snomed": [
            {
                "code": "233604007",
                "name": "Pneumonia",
                "french_name": "Pneumonie",
            },
            {
                "code": "195708003",
                "name": "Acute respiratory infection",
                "french_name": "Infection respiratoire aiguë (IRA)",
            },
        ],
        "loinc": [
            {
                "code": "9279-1",
                "name": "Respiratory rate",
                "french_name": "Fréquence respiratoire",
            },
            {
                "code": "59408-5",
                "name": "Oxygen saturation in Arterial blood by Pulse oximetry",
                "french_name": "Saturation pulsée en oxygène (SpO2)",
            },
        ],
        "atc": [
            {
                "code": "J01CA04",
                "name": "amoxicillin",
                "french_name": "Amoxicilline",
            },
            {
                "code": "R03AC02",
                "name": "salbutamol",
                "french_name": "Salbutamol aérosol",
            },
        ],
    },
    "Diarrhea": {
        "code": "Diarrhea",
        "name_fr": "Maladies diarrhéiques",
        "name_en": "Diarrheal diseases",
        "category": "Pathologie gastro-intestinale et déshydratation",
        "description": (
            "Gastro-entérites infectieuses et déshydratation aiguë chez l'enfant de moins de 5 ans. "
            "CIM-10 A09.0 et E86, suivi pondéral (LOINC 29463-7), protocole SRO + Zinc (ATC A07CA & A12CB01)."
        ),
        "icd10": [
            {
                "code": "A09.0",
                "name": "Other and unspecified gastroenteritis and colitis of infectious origin",
                "french_name": "Gastro-entérite d'origine infectieuse",
            },
            {
                "code": "E86",
                "name": "Volume depletion",
                "french_name": "Déshydratation aiguë",
            },
        ],
        "snomed": [
            {
                "code": "62315008",
                "name": "Diarrhea",
                "french_name": "Diarrhée",
            },
            {
                "code": "236070008",
                "name": "Dehydration",
                "french_name": "Déshydratation",
            },
        ],
        "loinc": [
            {
                "code": "29463-7",
                "name": "Body weight",
                "french_name": "Poids corporel",
            },
        ],
        "atc": [
            {
                "code": "A07CA",
                "name": "oral rehydration salt formulations",
                "french_name": "Sels de réhydratation orale (SRO)",
            },
            {
                "code": "A12CB01",
                "name": "zinc sulfate",
                "french_name": "Sulfate de zinc pédiatrique",
            },
        ],
    },
    "HIV": {
        "code": "HIV",
        "name_fr": "Infection par le VIH / SIDA",
        "name_en": "Human Immunodeficiency Virus Infection",
        "category": "Infection virale chronique",
        "description": (
            "Prise en charge active et stratégie 95-95-95 au Togo. Diagnostic CIM-10 B20/B24, "
            "dépistage rapide (LOINC 75622-1), suivi CD4 et charge virale, trithérapie de première ligne TLD (ATC J05AR13)."
        ),
        "icd10": [
            {
                "code": "B24",
                "name": "Unspecified human immunodeficiency virus [HIV] disease",
                "french_name": "Infection par le virus de l'immunodéficience humaine (VIH)",
            },
            {
                "code": "B20",
                "name": "Human immunodeficiency virus [HIV] disease resulting in infectious and parasitic diseases",
                "french_name": "Maladie par le VIH avec maladies infectieuses et parasitaires",
            },
        ],
        "snomed": [
            {
                "code": "86406008",
                "name": "Human immunodeficiency virus infection",
                "french_name": "Infection à VIH",
            },
        ],
        "loinc": [
            {
                "code": "75622-1",
                "name": "HIV 1 and 2 antibodies and HIV1 p24 Ag [Presence] in Serum by Rapid immunoassay",
                "french_name": "Test rapide dépistage VIH 1 et 2",
            },
            {
                "code": "24467-3",
                "name": "CD4 cells [#/volume] in Blood",
                "french_name": "Numération des lymphocytes CD4",
            },
            {
                "code": "25836-8",
                "name": "HIV 1 RNA [#/volume] (viral load) in Plasma by NAA",
                "french_name": "Charge virale plasmatique VIH-1",
            },
        ],
        "atc": [
            {
                "code": "J05AR13",
                "name": "lamivudine, tenofovir disoproxil and dolutegravir",
                "french_name": "TLD (Ténofovir + Lamivudine + Dolutégravir)",
            },
            {
                "code": "J05AJ03",
                "name": "dolutegravir",
                "french_name": "Dolutégravir (DTG)",
            },
        ],
    },
    "TB": {
        "code": "TB",
        "name_fr": "Tuberculose",
        "name_en": "Tuberculosis",
        "category": "Infection bactérienne mycobactérienne",
        "description": (
            "Priorité nationale du Programme National de Lutte contre la Tuberculose (PNLT). "
            "CIM-10 A15.0, diagnostic moléculaire GeneXpert (LOINC 89371-9), association fixe 4FDC RHZE (ATC J04AK02)."
        ),
        "icd10": [
            {
                "code": "A15.0",
                "name": "Tuberculosis of lung, confirmed by sputum microscopy with or without culture",
                "french_name": "Tuberculose pulmonaire confirmée par microscopie",
            },
            {
                "code": "A16.2",
                "name": "Tuberculosis of lung, without mention of bacteriological or histological confirmation",
                "french_name": "Tuberculose pulmonaire sans confirmation bactériologique",
            },
        ],
        "snomed": [
            {
                "code": "154283005",
                "name": "Pulmonary tuberculosis",
                "french_name": "Tuberculose pulmonaire",
            },
        ],
        "loinc": [
            {
                "code": "89371-9",
                "name": "Mycobacterium tuberculosis complex DNA [Presence] in Sputum by NAA",
                "french_name": "GeneXpert MTB/RIF crachats",
            },
        ],
        "atc": [
            {
                "code": "J04AK02",
                "name": "rifampicin, pyrazinamide, ethambutol and isoniazid",
                "french_name": "4FDC (RHZE) Antituberculeux combiné",
            },
            {
                "code": "J04AM06",
                "name": "rifampicin and isoniazid",
                "french_name": "RH (Rifampicine + Isoniazide)",
            },
        ],
    },
    "HTA": {
        "code": "HTA",
        "name_fr": "Hypertension Artérielle (HTA)",
        "name_en": "Hypertension",
        "category": "Maladie cardiovasculaire non transmissible (MNT)",
        "description": (
            "Pathologie cardiovasculaire prévalente chez l'adulte togolais. Diagnostic CIM-10 I10, "
            "mesures PAS/PAD (LOINC 8480-6 / 8462-4), antihypertenseurs Amlodipine (ATC C08CA01) et Énalapril (ATC C09AA02)."
        ),
        "icd10": [
            {
                "code": "I10",
                "name": "Essential (primary) hypertension",
                "french_name": "Hypertension artérielle essentielle",
            },
        ],
        "snomed": [
            {
                "code": "59621000",
                "name": "Essential hypertension",
                "french_name": "Hypertension artérielle",
            },
        ],
        "loinc": [
            {
                "code": "8480-6",
                "name": "Systolic blood pressure",
                "french_name": "Pression artérielle systolique (PAS)",
            },
            {
                "code": "8462-4",
                "name": "Diastolic blood pressure",
                "french_name": "Pression artérielle diastolique (PAD)",
            },
            {
                "code": "8867-4",
                "name": "Heart rate",
                "french_name": "Fréquence cardiaque",
            },
        ],
        "atc": [
            {
                "code": "C08CA01",
                "name": "amlodipine",
                "french_name": "Amlodipine",
            },
            {
                "code": "C09AA02",
                "name": "enalapril",
                "french_name": "Énalapril",
            },
            {
                "code": "C09CA01",
                "name": "losartan",
                "french_name": "Losartan",
            },
        ],
    },
    "Diabetes": {
        "code": "Diabetes",
        "name_fr": "Diabète",
        "name_en": "Diabetes Mellitus",
        "category": "Maladie métabolique non transmissible (MNT)",
        "description": (
            "Pathologie métabolique chronique en progression au Togo. CIM-10 E11.9 (type 2) et E10.9 (type 1), "
            "glycémie capillaire et veineuse (LOINC 2345-7 et 1558-6), HbA1c, antidiabétiques oraux Metformine (ATC A10BA02)."
        ),
        "icd10": [
            {
                "code": "E11.9",
                "name": "Type 2 diabetes mellitus without complications",
                "french_name": "Diabète de type 2 sans complication",
            },
            {
                "code": "E10.9",
                "name": "Type 1 diabetes mellitus without complications",
                "french_name": "Diabète de type 1 sans complication",
            },
        ],
        "snomed": [
            {
                "code": "44054006",
                "name": "Type 2 diabetes mellitus",
                "french_name": "Diabète de type 2",
            },
            {
                "code": "46635009",
                "name": "Type 1 diabetes mellitus",
                "french_name": "Diabète de type 1",
            },
        ],
        "loinc": [
            {
                "code": "2345-7",
                "name": "Glucose [Mass/volume] in Blood",
                "french_name": "Glycémie à jeun",
            },
            {
                "code": "1558-6",
                "name": "Fasting glucose [Mass/volume] in Serum or Plasma",
                "french_name": "Glycémie à jeun sérum/plasma",
            },
            {
                "code": "4548-4",
                "name": "Hemoglobin A1c/Hemoglobin.total in Blood",
                "french_name": "Hémoglobine glyquée (HbA1c)",
            },
        ],
        "atc": [
            {
                "code": "A10BA02",
                "name": "metformin",
                "french_name": "Metformine",
            },
            {
                "code": "A10BB01",
                "name": "glibenclamide",
                "french_name": "Glibenclamide",
            },
        ],
    },
    "SMI": {
        "code": "SMI",
        "name_fr": "Santé Maternelle et Infantile (SMI)",
        "name_en": "Maternal and Child Health",
        "category": "Obstétrique, périnatalité et suivi néonatal",
        "description": (
            "Surveillance prénatale (CPN), accouchements eutociques et césariennes (CIM-10 Z34.0, O80, O82), "
            "âge gestationnel (LOINC 11884-4), prévention hémorragies de la délivrance par Ocytocine (ATC H01BB02)."
        ),
        "icd10": [
            {
                "code": "Z34.0",
                "name": "Supervision of normal first pregnancy",
                "french_name": "Surveillance de première grossesse normale (CPN)",
            },
            {
                "code": "O80",
                "name": "Single spontaneous delivery",
                "french_name": "Accouchement unique spontané",
            },
            {
                "code": "O82",
                "name": "Single delivery by caesarean section",
                "french_name": "Accouchement unique par césarienne",
            },
        ],
        "snomed": [
            {
                "code": "169446002",
                "name": "Antenatal care",
                "french_name": "Soins prénatals (CPN)",
            },
            {
                "code": "236973005",
                "name": "Normal delivery",
                "french_name": "Accouchement normal eutocique",
            },
        ],
        "loinc": [
            {
                "code": "11884-4",
                "name": "Gestational age",
                "french_name": "Âge gestationnel",
            },
            {
                "code": "82810-3",
                "name": "Pregnancy status",
                "french_name": "Statut de grossesse",
            },
        ],
        "atc": [
            {
                "code": "H01BB02",
                "name": "oxytocin",
                "french_name": "Ocytocine (prévention hémorragie délivrance)",
            },
            {
                "code": "B03AA07",
                "name": "ferrous sulfate",
                "french_name": "Sulfate ferreux + acide folique (supplémentation)",
            },
        ],
    },
    "Malnutrition": {
        "code": "Malnutrition",
        "name_fr": "Malnutrition",
        "name_en": "Malnutrition",
        "category": "Trouble nutritionnel pédiatrique",
        "description": (
            "Dépistage et traitement de la malnutrition aiguë sévère (MAS) et modérée (MAM) chez l'enfant. "
            "CIM-10 E43 et E44.0, périmètre brachial MUAC (LOINC 56072-2 / 89270-3), ATPE / Plumpy'Nut et Vitamine A."
        ),
        "icd10": [
            {
                "code": "E43",
                "name": "Unspecified severe protein-energy malnutrition",
                "french_name": "Malnutrition protéino-énergétique sévère (MAS)",
            },
            {
                "code": "E44.0",
                "name": "Moderate protein-energy malnutrition",
                "french_name": "Malnutrition protéino-énergétique modérée (MAM)",
            },
        ],
        "snomed": [
            {
                "code": "238108007",
                "name": "Severe protein-calorie malnutrition",
                "french_name": "Malnutrition aiguë sévère",
            },
            {
                "code": "238107002",
                "name": "Moderate protein-calorie malnutrition",
                "french_name": "Malnutrition aiguë modérée",
            },
        ],
        "loinc": [
            {
                "code": "8302-2",
                "name": "Body height",
                "french_name": "Taille corporelle",
            },
            {
                "code": "56072-2",
                "name": "Mid-upper arm circumference",
                "french_name": "Périmètre brachial (PB / MUAC)",
            },
            {
                "code": "89270-3",
                "name": "Mid upper arm circumference Percentile",
                "french_name": "Percentile du périmètre brachial (MUAC)",
            },
        ],
        "atc": [
            {
                "code": "A11CA01",
                "name": "retinol (vit A)",
                "french_name": "Vitamine A (rétinol)",
            },
            {
                "code": "V06DX",
                "name": "other nutrients",
                "french_name": "Aliment Thérapeutique Prêt à l'Emploi (ATPE / Plumpy'Nut)",
            },
        ],
    },
    "PEV": {
        "code": "PEV",
        "name_fr": "Programme Élargi de Vaccination (PEV)",
        "name_en": "Expanded Programme on Immunization",
        "category": "Vaccination essentielle pédiatrique",
        "description": (
            "Calendrier vaccinal national du Togo : BCG, Polio oral (VPO), Pentavalent (DTC-HepB-Hib), "
            "Rougeole-Rubéole (RR) et Fièvre Jaune (VAA)."
        ),
        "icd10": [],
        "snomed": [],
        "loinc": [],
        "atc": [
            {
                "code": "J07AN01",
                "name": "tuberculosis, live attenuated (BCG)",
                "french_name": "Vaccin BCG (Tuberculose)",
            },
            {
                "code": "J07BF02",
                "name": "poliomyelitis, oral, bivalent, live attenuated",
                "french_name": "Vaccin Poliomyélite Oral (VPO)",
            },
            {
                "code": "J07CA09",
                "name": "diphtheria-hemophilus influenzae B-pertussis-tetanus-hepatitis B",
                "french_name": "Vaccin Pentavalent (DTC-HepB-Hib)",
            },
            {
                "code": "J07BD53",
                "name": "measles, combinations with rubella, live attenuated",
                "french_name": "Vaccin Rougeole-Rubéole (RR)",
            },
            {
                "code": "J07BL01",
                "name": "yellow fever, live attenuated",
                "french_name": "Vaccin Fièvre Jaune (VAA)",
            },
        ],
    },
}

# Définition exhaustive des concepts OHDSI OMOP CDM 5.4 pour le mock Parquet
MOCK_CONCEPTS_CATALOG: list[dict[str, Any]] = [
    # ==========================================================================
    # 1. PALUDISME (Malaria)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 4158563,
        "concept_name": "Plasmodium falciparum malaria",
        "french_name": "Paludisme à Plasmodium falciparum",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "B50.9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 435308,
    },
    {
        "concept_id": 4158560,
        "concept_name": "Plasmodium falciparum malaria with cerebral complications",
        "french_name": "Paludisme grave avec complications cérébrales",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "B50.0",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 435308,
    },
    {
        "concept_id": 4158572,
        "concept_name": "Unspecified malaria",
        "french_name": "Paludisme sans précision",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "B54",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 435308,
    },
    # SNOMED CT
    {
        "concept_id": 435308,
        "concept_name": "Malaria",
        "french_name": "Paludisme (Concept standard)",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "61462000",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 435308,
    },
    {
        "concept_id": 4148906,
        "concept_name": "Plasmodium falciparum infection",
        "french_name": "Infection à Plasmodium falciparum",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "240742007",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 4148906,
    },
    # LOINC
    {
        "concept_id": 3020891,
        "concept_name": "Body temperature",
        "french_name": "Température corporelle",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "8310-5",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 3020891,
    },
    {
        "concept_id": 40757603,
        "concept_name": "Plasmodium falciparum antigen [Presence] in Blood by Rapid immunoassay",
        "french_name": "Test de Diagnostic Rapide (TDR) Paludisme",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "58900-2",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 40757603,
    },
    {
        "concept_id": 3000963,
        "concept_name": "Hemoglobin [Mass/volume] in Blood",
        "french_name": "Taux d'hémoglobine",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "718-7",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 3000963,
    },
    # ATC
    {
        "concept_id": 21604686,
        "concept_name": "artemether and lumefantrine",
        "french_name": "Artéméther et luméfantrine (ACT)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "P01BF01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 21604686,
    },
    {
        "concept_id": 21604683,
        "concept_name": "artesunate",
        "french_name": "Artésunate injectable (paludisme grave)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "P01BE03",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 21604683,
    },
    {
        "concept_id": 21604675,
        "concept_name": "sulfadoxine and pyrimethamine",
        "french_name": "Sulfadoxine-pyriméthamine (TPI grossesse)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "P01BD51",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malaria",
        "standard_concept_id": 21604675,
    },
    # ==========================================================================
    # 2. INFECTIONS RESPIRATOIRES AIGUËS (IRA / ARI)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 4124847,
        "concept_name": "Pneumonia, unspecified",
        "french_name": "Pneumopathie aiguë sans précision",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "J18.9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 255848,
    },
    {
        "concept_id": 4127088,
        "concept_name": "Acute bronchitis, unspecified",
        "french_name": "Bronchite aiguë sans précision",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "J20.9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 260139,
    },
    {
        "concept_id": 4127087,
        "concept_name": "Acute upper respiratory infection, unspecified",
        "french_name": "Infection aiguë des voies respiratoires supérieures",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "J06.9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 4168213,
    },
    # SNOMED CT
    {
        "concept_id": 255848,
        "concept_name": "Pneumonia",
        "french_name": "Pneumonie",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "233604007",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 255848,
    },
    {
        "concept_id": 4168213,
        "concept_name": "Acute respiratory infection",
        "french_name": "Infection respiratoire aiguë (IRA)",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "195708003",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 4168213,
    },
    # LOINC
    {
        "concept_id": 3024171,
        "concept_name": "Respiratory rate",
        "french_name": "Fréquence respiratoire",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "9279-1",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 3024171,
    },
    {
        "concept_id": 40762499,
        "concept_name": "Oxygen saturation in Arterial blood by Pulse oximetry",
        "french_name": "Saturation pulsée en oxygène (SpO2)",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "59408-5",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 40762499,
    },
    # ATC
    {
        "concept_id": 21600021,
        "concept_name": "amoxicillin",
        "french_name": "Amoxicilline",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J01CA04",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 21600021,
    },
    {
        "concept_id": 21601744,
        "concept_name": "salbutamol",
        "french_name": "Salbutamol aérosol",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "R03AC02",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "ARI",
        "standard_concept_id": 21601744,
    },
    # ==========================================================================
    # 3. MALADIES DIARRHÉIQUES (Diarrhea)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 45548694,
        "concept_name": "Other and unspecified gastroenteritis and colitis of infectious origin",
        "french_name": "Gastro-entérite d'origine infectieuse",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "A09.0",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 196523,
    },
    {
        "concept_id": 433753,
        "concept_name": "Volume depletion",
        "french_name": "Déshydratation aiguë",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "E86",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 433753,
    },
    # SNOMED CT
    {
        "concept_id": 196523,
        "concept_name": "Diarrhea",
        "french_name": "Diarrhée",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "62315008",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 196523,
    },
    {
        "concept_id": 434153,
        "concept_name": "Dehydration",
        "french_name": "Déshydratation",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "236070008",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 434153,
    },
    # LOINC
    {
        "concept_id": 3025315,
        "concept_name": "Body weight",
        "french_name": "Poids corporel",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "29463-7",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 3025315,
    },
    # ATC
    {
        "concept_id": 21601386,
        "concept_name": "oral rehydration salt formulations",
        "french_name": "Sels de réhydratation orale (SRO)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 4th",
        "standard_concept": "C",
        "concept_code": "A07CA",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 21601386,
    },
    {
        "concept_id": 21601445,
        "concept_name": "zinc sulfate",
        "french_name": "Sulfate de zinc pédiatrique",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "A12CB01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diarrhea",
        "standard_concept_id": 21601445,
    },
    # ==========================================================================
    # 4. VIH / SIDA (HIV)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 43530727,
        "concept_name": "Unspecified human immunodeficiency virus [HIV] disease",
        "french_name": "Infection par le virus de l'immunodéficience humaine (VIH)",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "B24",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 439727,
    },
    {
        "concept_id": 43530725,
        "concept_name": "Human immunodeficiency virus [HIV] disease resulting in infectious and parasitic diseases",
        "french_name": "Maladie par le VIH avec maladies infectieuses et parasitaires",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "B20",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 439727,
    },
    # SNOMED CT
    {
        "concept_id": 439727,
        "concept_name": "Human immunodeficiency virus infection",
        "french_name": "Infection à VIH",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "86406008",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 439727,
    },
    # LOINC
    {
        "concept_id": 3034509,
        "concept_name": "HIV 1 and 2 antibodies and HIV1 p24 Ag [Presence] in Serum by Rapid immunoassay",
        "french_name": "Test rapide dépistage VIH 1 et 2",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "75622-1",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 3034509,
    },
    {
        "concept_id": 3023103,
        "concept_name": "CD4 cells [#/volume] in Blood",
        "french_name": "Numération des lymphocytes CD4",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "24467-3",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 3023103,
    },
    {
        "concept_id": 3016723,
        "concept_name": "HIV 1 RNA [#/volume] (viral load) in Plasma by NAA",
        "french_name": "Charge virale plasmatique VIH-1",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "25836-8",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 3016723,
    },
    # ATC
    {
        "concept_id": 21600461,
        "concept_name": "lamivudine, tenofovir disoproxil and dolutegravir",
        "french_name": "TLD (Ténofovir + Lamivudine + Dolutégravir)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J05AR13",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 21600461,
    },
    {
        "concept_id": 21600451,
        "concept_name": "dolutegravir",
        "french_name": "Dolutégravir (DTG)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J05AJ03",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HIV",
        "standard_concept_id": 21600451,
    },
    # ==========================================================================
    # 5. TUBERCULOSE (TB)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 4134114,
        "concept_name": "Tuberculosis of lung, confirmed by sputum microscopy with or without culture",
        "french_name": "Tuberculose pulmonaire confirmée par microscopie",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "A15.0",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "TB",
        "standard_concept_id": 253954,
    },
    {
        "concept_id": 4134115,
        "concept_name": "Tuberculosis of lung, without mention of bacteriological confirmation",
        "french_name": "Tuberculose pulmonaire sans confirmation bactériologique",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "A16.2",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "TB",
        "standard_concept_id": 253954,
    },
    # SNOMED CT
    {
        "concept_id": 253954,
        "concept_name": "Pulmonary tuberculosis",
        "french_name": "Tuberculose pulmonaire",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "154283005",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "TB",
        "standard_concept_id": 253954,
    },
    # LOINC
    {
        "concept_id": 3020287,
        "concept_name": "Mycobacterium tuberculosis complex DNA [Presence] in Sputum by NAA",
        "french_name": "GeneXpert MTB/RIF crachats",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "89371-9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "TB",
        "standard_concept_id": 3020287,
    },
    # ATC
    {
        "concept_id": 21600375,
        "concept_name": "rifampicin, pyrazinamide, ethambutol and isoniazid",
        "french_name": "4FDC (RHZE) Antituberculeux combiné",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J04AK02",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "TB",
        "standard_concept_id": 21600375,
    },
    {
        "concept_id": 21600379,
        "concept_name": "rifampicin and isoniazid",
        "french_name": "RH (Rifampicine + Isoniazide)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J04AM06",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "TB",
        "standard_concept_id": 21600379,
    },
    # ==========================================================================
    # 6. HYPERTENSION ARTÉRIELLE (HTA)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 45576870,
        "concept_name": "Essential (primary) hypertension",
        "french_name": "Hypertension artérielle essentielle",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "I10",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 320128,
    },
    # SNOMED CT
    {
        "concept_id": 320128,
        "concept_name": "Essential hypertension",
        "french_name": "Hypertension artérielle",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "59621000",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 320128,
    },
    # LOINC
    {
        "concept_id": 3004249,
        "concept_name": "Systolic blood pressure",
        "french_name": "Pression artérielle systolique (PAS)",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "8480-6",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 3004249,
    },
    {
        "concept_id": 3012888,
        "concept_name": "Diastolic blood pressure",
        "french_name": "Pression artérielle diastolique (PAD)",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "8462-4",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 3012888,
    },
    {
        "concept_id": 3027598,
        "concept_name": "Heart rate",
        "french_name": "Fréquence cardiaque",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "8867-4",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 3027598,
    },
    # ATC
    {
        "concept_id": 21601782,
        "concept_name": "amlodipine",
        "french_name": "Amlodipine",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "C08CA01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 21601782,
    },
    {
        "concept_id": 21601804,
        "concept_name": "enalapril",
        "french_name": "Énalapril",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "C09AA02",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 21601804,
    },
    {
        "concept_id": 21601822,
        "concept_name": "losartan",
        "french_name": "Losartan",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "C09CA01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "HTA",
        "standard_concept_id": 21601822,
    },
    # ==========================================================================
    # 7. DIABÈTE (Diabetes)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 45543169,
        "concept_name": "Type 2 diabetes mellitus without complications",
        "french_name": "Diabète de type 2 sans complication",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "E11.9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 201826,
    },
    {
        "concept_id": 45543168,
        "concept_name": "Type 1 diabetes mellitus without complications",
        "french_name": "Diabète de type 1 sans complication",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "E10.9",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 201254,
    },
    # SNOMED CT
    {
        "concept_id": 201826,
        "concept_name": "Type 2 diabetes mellitus",
        "french_name": "Diabète de type 2",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "44054006",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 201826,
    },
    {
        "concept_id": 201254,
        "concept_name": "Type 1 diabetes mellitus",
        "french_name": "Diabète de type 1",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "46635009",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 201254,
    },
    # LOINC
    {
        "concept_id": 3004501,
        "concept_name": "Glucose [Mass/volume] in Blood",
        "french_name": "Glycémie à jeun",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "2345-7",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 3004501,
    },
    {
        "concept_id": 3004502,
        "concept_name": "Fasting glucose [Mass/volume] in Serum or Plasma",
        "french_name": "Glycémie à jeun sérum/plasma",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "1558-6",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 3004502,
    },
    {
        "concept_id": 3004410,
        "concept_name": "Hemoglobin A1c/Hemoglobin.total in Blood",
        "french_name": "Hémoglobine glyquée (HbA1c)",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Lab Test",
        "standard_concept": "S",
        "concept_code": "4548-4",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 3004410,
    },
    # ATC
    {
        "concept_id": 21600712,
        "concept_name": "metformin",
        "french_name": "Metformine",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "A10BA02",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 21600712,
    },
    {
        "concept_id": 21600744,
        "concept_name": "glibenclamide",
        "french_name": "Glibenclamide",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "A10BB01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Diabetes",
        "standard_concept_id": 21600744,
    },
    # ==========================================================================
    # 8. SANTÉ MATERNELLE ET INFANTILE (SMI)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 4181467,
        "concept_name": "Supervision of normal first pregnancy",
        "french_name": "Surveillance de première grossesse normale (CPN)",
        "domain_id": "Observation",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "Z34.0",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 4216356,
    },
    {
        "concept_id": 45572212,
        "concept_name": "Single spontaneous delivery",
        "french_name": "Accouchement unique spontané",
        "domain_id": "Procedure",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "O80",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 4066440,
    },
    {
        "concept_id": 45572214,
        "concept_name": "Single delivery by caesarean section",
        "french_name": "Accouchement unique par césarienne",
        "domain_id": "Procedure",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "O82",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 4066440,
    },
    # SNOMED CT
    {
        "concept_id": 4216356,
        "concept_name": "Antenatal care",
        "french_name": "Soins prénatals (CPN)",
        "domain_id": "Procedure",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Procedure",
        "standard_concept": "S",
        "concept_code": "169446002",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 4216356,
    },
    {
        "concept_id": 4066440,
        "concept_name": "Normal delivery",
        "french_name": "Accouchement normal",
        "domain_id": "Procedure",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Procedure",
        "standard_concept": "S",
        "concept_code": "236973005",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 4066440,
    },
    # LOINC
    {
        "concept_id": 3006322,
        "concept_name": "Gestational age",
        "french_name": "Âge gestationnel",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "11884-4",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 3006322,
    },
    {
        "concept_id": 3006323,
        "concept_name": "Pregnancy status",
        "french_name": "Statut de grossesse",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "82810-3",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 3006323,
    },
    # ATC
    {
        "concept_id": 21601664,
        "concept_name": "oxytocin",
        "french_name": "Ocytocine (prévention hémorragie délivrance)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "H01BB02",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 21601664,
    },
    {
        "concept_id": 21601420,
        "concept_name": "ferrous sulfate",
        "french_name": "Sulfate ferreux + acide folique",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "B03AA07",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "SMI",
        "standard_concept_id": 21601420,
    },
    # ==========================================================================
    # 9. MALNUTRITION (Malnutrition)
    # ==========================================================================
    # CIM-10
    {
        "concept_id": 45543187,
        "concept_name": "Unspecified severe protein-energy malnutrition",
        "french_name": "Malnutrition protéino-énergétique sévère (MAS)",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "E43",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 4323447,
    },
    {
        "concept_id": 45543188,
        "concept_name": "Moderate protein-energy malnutrition",
        "french_name": "Malnutrition protéino-énergétique modérée (MAM)",
        "domain_id": "Condition",
        "vocabulary_id": "ICD10",
        "concept_class_id": "ICD10 code",
        "standard_concept": None,
        "concept_code": "E44.0",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 4323448,
    },
    # SNOMED CT
    {
        "concept_id": 4323447,
        "concept_name": "Severe protein-calorie malnutrition",
        "french_name": "Malnutrition aiguë sévère",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "238108007",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 4323447,
    },
    {
        "concept_id": 4323448,
        "concept_name": "Moderate protein-calorie malnutrition",
        "french_name": "Malnutrition aiguë modérée",
        "domain_id": "Condition",
        "vocabulary_id": "SNOMED",
        "concept_class_id": "Clinical Finding",
        "standard_concept": "S",
        "concept_code": "238107002",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 4323448,
    },
    # LOINC
    {
        "concept_id": 3036277,
        "concept_name": "Body height",
        "french_name": "Taille corporelle",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "8302-2",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 3036277,
    },
    {
        "concept_id": 40760447,
        "concept_name": "Mid-upper arm circumference",
        "french_name": "Périmètre brachial (PB)",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "56072-2",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 40760447,
    },
    {
        "concept_id": 40760448,
        "concept_name": "Mid upper arm circumference Percentile",
        "french_name": "Percentile du périmètre brachial (MUAC)",
        "domain_id": "Measurement",
        "vocabulary_id": "LOINC",
        "concept_class_id": "Clinical Observation",
        "standard_concept": "S",
        "concept_code": "89270-3",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 40760448,
    },
    # ATC
    {
        "concept_id": 21601618,
        "concept_name": "retinol (vit A)",
        "french_name": "Vitamine A (rétinol)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "A11CA01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 21601618,
    },
    {
        "concept_id": 21604555,
        "concept_name": "other nutrients",
        "french_name": "Aliment Thérapeutique Prêt à l'Emploi (ATPE / Plumpy'Nut)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "V06DX",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "Malnutrition",
        "standard_concept_id": 21604555,
    },
    # ==========================================================================
    # 10. PEV TOGO (Vaccination essentielle)
    # ==========================================================================
    {
        "concept_id": 21600862,
        "concept_name": "tuberculosis, live attenuated (BCG)",
        "french_name": "Vaccin BCG (Tuberculose)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J07AN01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "PEV",
        "standard_concept_id": 21600862,
    },
    {
        "concept_id": 21600885,
        "concept_name": "poliomyelitis, oral, bivalent, live attenuated",
        "french_name": "Vaccin Poliomyélite Oral (VPO)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J07BF02",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "PEV",
        "standard_concept_id": 21600885,
    },
    {
        "concept_id": 21600898,
        "concept_name": "diphtheria-hemophilus influenzae B-pertussis-tetanus-hepatitis B",
        "french_name": "Vaccin Pentavalent (DTC-HepB-Hib)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J07CA09",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "PEV",
        "standard_concept_id": 21600898,
    },
    {
        "concept_id": 21600874,
        "concept_name": "measles, combinations with rubella, live attenuated",
        "french_name": "Vaccin Rougeole-Rubéole (RR)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J07BD53",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "PEV",
        "standard_concept_id": 21600874,
    },
    {
        "concept_id": 21600890,
        "concept_name": "yellow fever, live attenuated",
        "french_name": "Vaccin Fièvre Jaune (VAA)",
        "domain_id": "Drug",
        "vocabulary_id": "ATC",
        "concept_class_id": "ATC 5th",
        "standard_concept": "C",
        "concept_code": "J07BL01",
        "valid_start_date": "1970-01-01",
        "valid_end_date": "2099-12-31",
        "invalid_reason": None,
        "pathology_group": "PEV",
        "standard_concept_id": 21600890,
    },
]


def get_priority_pathologies() -> dict[str, dict[str, Any]]:
    """Renvoie le catalogue exhaustif des 9 pathologies prioritaires togolaises et leurs correspondances."""
    return PRIORITY_PATHOLOGIES_CATALOG


def load_sample_vocabularies(
    parquet_path: Path | str | None = None,
) -> pd.DataFrame:
    """Charge le catalogue mock terminologique Parquet dans un DataFrame pandas."""
    path = Path(parquet_path) if parquet_path else DEFAULT_VOCAB_PARQUET_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier Parquet terminologique introuvable : {path}. "
            "Exécutez generate_sample_vocabularies() au préalable."
        )
    return pd.read_parquet(path)


def validate_sample_vocabularies(
    df_or_table: pd.DataFrame | pa.Table | Path | str,
) -> list[str]:
    """Valide la conformité du catalogue terminologique selon les règles OMOP CDM 5.4 et ADR D-09.

    Args:
        df_or_table: DataFrame pandas, Table PyArrow ou chemin vers un fichier Parquet.

    Returns:
        Liste des messages d'erreurs détectés (vide si le catalogue est conforme).
    """
    errors: list[str] = []

    # 1. Résolution du DataFrame
    if isinstance(df_or_table, (str, Path)):
        p = Path(df_or_table)
        if not p.exists():
            return [f"Fichier Parquet inexistant : {p}"]
        df = pd.read_parquet(p)
    elif isinstance(df_or_table, pa.Table):
        df = df_or_table.to_pandas()
    elif isinstance(df_or_table, pd.DataFrame):
        df = df_or_table
    else:
        return [f"Type non supporté pour df_or_table : {type(df_or_table)}"]

    if df.empty:
        return ["Le jeu de données de vocabulaires est vide."]

    # 2. Vérification des colonnes obligatoires
    required_columns = {
        "concept_name",
        "domain_id",
        "vocabulary_id",
        "concept_code",
        "pathology_group",
    }
    present_cols = set(df.columns)
    missing_cols = required_columns - present_cols
    if missing_cols:
        errors.append(f"Colonnes obligatoires manquantes : {sorted(missing_cols)}")

    # Vérification présence de colonne ID
    if "concept_id" not in present_cols and "omop_concept_id" not in present_cols:
        errors.append("Colonne d'identifiant (concept_id ou omop_concept_id) manquante")

    if errors:
        return errors

    id_col = "concept_id" if "concept_id" in present_cols else "omop_concept_id"

    # 3. Non-vacuité et unicité de concept_id
    if df[id_col].isnull().any():
        null_count = int(df[id_col].isnull().sum())
        errors.append(f"La colonne '{id_col}' contient {null_count} valeurs nulles")
    if not df[id_col].is_unique:
        duplicates = df[df[id_col].duplicated(keep=False)][id_col].tolist()
        errors.append(f"Identifiants dupliqués dans '{id_col}' : {duplicates[:5]}")

    # 4. Non-vacuité des colonnes concept_code, concept_name, vocabulary_id
    for col in ["concept_code", "concept_name", "vocabulary_id"]:
        if col in df.columns:
            if df[col].isnull().any():
                null_count = int(df[col].isnull().sum())
                errors.append(f"La colonne '{col}' contient {null_count} valeurs nulles")
            empty_count = int((df[col].astype(str).str.strip() == "").sum())
            if empty_count > 0:
                errors.append(f"La colonne '{col}' contient {empty_count} chaînes vides")

    # 5. Domaines OMOP autorisés
    if "domain_id" in df.columns:
        present_domains = set(df["domain_id"].dropna().unique())
        invalid_domains = present_domains - VALID_OMOP_DOMAINS
        if invalid_domains:
            errors.append(f"Domaines OMOP non autorisés détectés : {sorted(invalid_domains)}")

    # 6. Vocabulaires cibles autorisés et présence des 4 pivots
    if "vocabulary_id" in df.columns:
        present_vocabs = set(df["vocabulary_id"].dropna().astype(str).str.strip().unique())
        invalid_vocabs = present_vocabs - STANDARD_VOCABULARIES
        if invalid_vocabs:
            errors.append(f"Vocabulaires non autorisés détectés : {sorted(invalid_vocabs)}")

        # Normalisation pour tolérer variantes de casse et tirets
        norm_vocabs = {v.replace("-", "").replace(" ", "").upper() for v in present_vocabs}
        missing_pivots = [
            v for v in STANDARD_VOCABULARIES if not any(v in nv for nv in norm_vocabs)
        ]
        if missing_pivots:
            errors.append(f"Vocabulaires pivots manquants : {sorted(missing_pivots)}")

    # 7. Présence des 9 pathologies prioritaires togolaises
    if "pathology_group" in df.columns:
        present_groups_upper = {g.strip().upper() for g in df["pathology_group"].dropna().unique()}
        missing_groups = [
            g for g in PRIORITY_PATHOLOGY_GROUPS if g.upper() not in present_groups_upper
        ]
        if missing_groups:
            errors.append(f"Pathologies prioritaires manquantes : {sorted(missing_groups)}")

    return errors


def generate_sample_vocabularies(
    output_path: Path | str = DEFAULT_VOCAB_PARQUET_PATH,
) -> Path:
    """Génère de manière déterministe le catalogue terminologique Parquet (< 1 Mo).

    Args:
        output_path: Chemin cible du fichier Parquet à écrire.

    Returns:
        Path vers le fichier Parquet généré.
    """
    out = Path(output_path)
    df = pd.DataFrame(MOCK_CONCEPTS_CATALOG)

    # Validation interne rigoureuse
    validation_errors = validate_sample_vocabularies(df)
    if validation_errors:
        raise ValueError(f"Échec de validation du catalogue mock : {validation_errors}")

    out.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df)
    pq.write_table(table, out, compression="snappy")

    file_size = os.path.getsize(out)
    if file_size >= 1_000_000:
        raise ValueError(
            f"VIOLATION ADR D-09 : La taille du fichier ({file_size} octets) "
            "dépasse la limite absolue de 1 000 000 octets"
        )

    return out


if __name__ == "__main__":
    generate_sample_vocabularies()
