"""Moteur de règles cliniques et épidémiologiques contextuelles pour le Togo (Étape 3).

Ce module simule les parcours de soins, épisodes cliniques, observations LOINC,
prescriptions ATC et vaccinations PEV conformément à la pyramide sanitaire togolaise,
aux 9 pathologies prioritaires et aux contraintes d'intégrité clinique (VAL-002, D-04, D-08).
"""

from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

from src.terminology.geography import load_health_geography
from src.terminology.pathologies import load_sample_vocabularies

# Espaces de noms UUID v5 immuables pour la traçabilité des entités cliniques
NAMESPACE_TOGO_BASE = uuid.uuid5(uuid.NAMESPACE_DNS, "interop-sante.gouv.tg")
NAMESPACE_TOGO_ENCOUNTER = uuid.uuid5(NAMESPACE_TOGO_BASE, "encounter")
NAMESPACE_TOGO_CONDITION = uuid.uuid5(NAMESPACE_TOGO_BASE, "condition")
NAMESPACE_TOGO_OBSERVATION = uuid.uuid5(NAMESPACE_TOGO_BASE, "observation")
NAMESPACE_TOGO_PRESCRIPTION = uuid.uuid5(NAMESPACE_TOGO_BASE, "prescription")
NAMESPACE_TOGO_IMMUNIZATION = uuid.uuid5(NAMESPACE_TOGO_BASE, "immunization")


class ClinicalRulesEngine:
    """Moteur d'application des règles cliniques contextuelles togolaises."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._load_references()

    def _load_references(self) -> None:
        """Charge et indexe les référentiels géographiques et terminologiques."""
        self.geo_df: pd.DataFrame = load_health_geography()
        self.vocab_df: pd.DataFrame = load_sample_vocabularies()

        # Indexation des formations sanitaires par niveau de pyramide
        self.facilities_by_level: dict[int, list[dict[str, Any]]] = {
            1: self.geo_df[self.geo_df["pyramid_level"] == 1].to_dict(orient="records"),
            2: self.geo_df[self.geo_df["pyramid_level"] == 2].to_dict(orient="records"),
            3: self.geo_df[self.geo_df["pyramid_level"] == 3].to_dict(orient="records"),
            4: self.geo_df[self.geo_df["pyramid_level"] == 4].to_dict(orient="records"),
        }

        # Indexation des formations par district pour proximité
        self.facilities_by_district: dict[str, list[dict[str, Any]]] = {}
        for row in self.geo_df.to_dict(orient="records"):
            d_code = row["district_code"]
            self.facilities_by_district.setdefault(d_code, []).append(row)

    def select_facility(
        self,
        district_code: str,
        pyramid_level: int,
    ) -> dict[str, Any]:
        """Sélectionne une structure sanitaire respectant le niveau et la proximité géographique."""
        # Candidats du niveau demandé
        level_candidates = self.facilities_by_level.get(pyramid_level, [])
        if not level_candidates:
            level_candidates = self.facilities_by_level[1]

        # Priorité aux structures dans le district du patient (notamment niveau 1 et 2)
        district_level_candidates = [
            f for f in level_candidates if f["district_code"] == district_code
        ]
        if district_level_candidates:
            return self.rng.choice(district_level_candidates)

        # Sinon structure du niveau dans la région ou au niveau national
        return self.rng.choice(level_candidates)

    def determine_pathologies_for_patient(
        self,
        patient: dict[str, Any],
    ) -> list[str]:
        """Détermine les pathologies prioritaires candidates selon l'âge et le sexe du patient."""
        age: int = patient["_age"]
        gender: str = patient["gender"]

        candidates: list[tuple[str, float]] = []

        # 1. Paludisme (endémique, forte sur-incidence pédiatrique)
        p_malaria = 0.50 if age < 5 else 0.35
        candidates.append(("Malaria", p_malaria))

        # 2. IRA (Infections Respiratoires Aiguës)
        p_ari = 0.35 if age < 5 else 0.18
        candidates.append(("ARI", p_ari))

        # 3. Diarrhées
        p_diarrhea = 0.30 if age < 5 else 0.10
        candidates.append(("Diarrhea", p_diarrhea))

        # 4. Malnutrition (nourrissons et jeunes enfants < 5 ans)
        if age < 5:
            candidates.append(("Malnutrition", 0.15))

        # 5. Santé Maternelle et Infantile (SMI)
        # RÈGLE D'INTÉGRITÉ STRICTE : UNIQUEMENT FEMMES DE 15 À 49 ANS
        if gender == "female" and 15 <= age <= 49:
            candidates.append(("SMI", 0.25))

        # 6. HTA (Hypertension) : adultes >= 30 ans, surtout 45+
        if age >= 45:
            candidates.append(("HTA", 0.30))
        elif age >= 30:
            candidates.append(("HTA", 0.12))

        # 7. Diabète : adultes >= 35 ans
        if age >= 45:
            candidates.append(("Diabetes", 0.18))
        elif age >= 35:
            candidates.append(("Diabetes", 0.08))

        # 8. VIH : adultes 15-55 ans
        if 15 <= age <= 55:
            candidates.append(("HIV", 0.05))

        # 9. Tuberculose : adultes et jeunes adultes
        if age >= 15:
            candidates.append(("TB", 0.03))

        # Sélection probabiliste d'au moins 1 pathologie
        selected: list[str] = []
        for path_group, prob in candidates:
            if self.rng.random() < prob:
                selected.append(path_group)

        # Si aucune pathologie tirée, attribuer la pathologie la plus commune selon l'âge
        if not selected:
            if age < 5:
                selected.append("Malaria")
            elif gender == "female" and 20 <= age <= 35 and self.rng.random() < 0.5:
                selected.append("SMI")
            elif age >= 50:
                selected.append("HTA")
            else:
                selected.append(self.rng.choice(["Malaria", "ARI"]))

        return selected

    def generate_clinical_events_for_patient(
        self,
        patient: dict[str, Any],
        patient_idx: int,
        year: int = 2025,
    ) -> dict[str, list[dict[str, Any]]]:
        """Génère l'ensemble des rencontres, diagnostics, observations, prescriptions et vaccins."""
        pathologies = self.determine_pathologies_for_patient(patient)
        age: int = patient["_age"]
        district_code: str = patient["address_district_code"]

        encounters: list[dict[str, Any]] = []
        conditions: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        prescriptions: list[dict[str, Any]] = []
        immunizations: list[dict[str, Any]] = []

        for enc_counter, path_group in enumerate(pathologies, start=1):
            # 1. Détermination du niveau de la pyramide pour cette consultation
            # Distribution : 72% Niv 1 (USP/CMS), 16% Niv 2 (Hospital), 8% Niv 3 (CHR), 4% Niv 4 (CHU)
            pyramid_roll = self.rng.random()
            if path_group == "SMI" and self.rng.random() < 0.20:
                # Césariennes ou accouchements compliqués orientés vers niveau 2, 3 ou 4
                pyramid_level = self.rng.choices([2, 3, 4], weights=[0.60, 0.30, 0.10], k=1)[0]
            elif pyramid_roll < 0.72:
                pyramid_level = 1
            elif pyramid_roll < 0.88:
                pyramid_level = 2
            elif pyramid_roll < 0.96:
                pyramid_level = 3
            else:
                pyramid_level = 4

            facility = self.select_facility(district_code, pyramid_level)

            # Rapprochement / référence si niveau > 1
            referral_facility_id: str | None = None
            if pyramid_level > 1 and self.rng.random() < 0.40:
                usp_cands = [
                    f for f in self.facilities_by_level[1] if f["district_code"] == district_code
                ]
                if usp_cands:
                    referral_facility_id = self.rng.choice(usp_cands)["facility_id"]

            encounter_id = str(
                uuid.uuid5(
                    NAMESPACE_TOGO_ENCOUNTER,
                    f"seed={self.seed}:pat={patient_idx}:enc={enc_counter}",
                )
            )

            # Dates
            month = self.rng.randint(1, 12)
            day = self.rng.randint(1, 28)
            hour = self.rng.randint(8, 16)
            minute = self.rng.randint(0, 59)
            start_date_str = f"{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00Z"
            end_date_str = f"{year}-{month:02d}-{day:02d}T{hour + 1:02d}:{minute:02d}:00Z"

            enc_class = (
                "inpatient"
                if pyramid_level >= 3 or (pyramid_level == 2 and self.rng.random() < 0.25)
                else "ambulatory"
            )

            # Raccordement aux codes de la pathologie
            cond_records, obs_records, rx_records, reason_code, reason_display = (
                self._generate_pathology_data(
                    path_group=path_group,
                    patient=patient,
                    encounter_id=encounter_id,
                    encounter_date=start_date_str,
                    pyramid_level=pyramid_level,
                )
            )

            encounters.append(
                {
                    "encounter_id": encounter_id,
                    "patient_id": patient["patient_id"],
                    "facility_id": facility["facility_id"],
                    "facility_code": facility["facility_code"],
                    "facility_name": facility["name"],
                    "facility_category": facility["category"],
                    "pyramid_level": pyramid_level,
                    "district_code": facility["district_code"],
                    "region_code": facility["region_code"],
                    "encounter_class": enc_class,
                    "encounter_type": enc_class,
                    "start_date": start_date_str,
                    "start_datetime": start_date_str,
                    "end_date": end_date_str,
                    "end_datetime": end_date_str,
                    "reason_code": reason_code,
                    "reason_display": reason_display,
                    "status": "finished",
                    "referral_from_facility_id": referral_facility_id,
                }
            )

            conditions.extend(cond_records)
            observations.extend(obs_records)
            prescriptions.extend(rx_records)

        # 2. Calendrier vaccinal PEV Togo pour les enfants de moins de 2 ans (< 2 ans)
        # RÈGLE D'INTÉGRITÉ STRICTE : AUCUN VACCIN PEV PÉDIATRIQUE CHEZ L'ADULTE
        if age < 2:
            pev_records = self._generate_pev_immunizations(
                patient=patient,
                encounters=encounters,
                district_code=district_code,
                year=year,
            )
            immunizations.extend(pev_records)

        return {
            "encounters": encounters,
            "conditions": conditions,
            "observations": observations,
            "prescriptions": prescriptions,
            "immunizations": immunizations,
        }

    def _generate_pathology_data(
        self,
        path_group: str,
        patient: dict[str, Any],
        encounter_id: str,
        encounter_date: str,
        pyramid_level: int,
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        str,
        str,
    ]:
        """Génère les triplets condition-observation-prescription conformes au vocabulaire."""
        patient_id = patient["patient_id"]
        date_iso = encounter_date[:10]

        conditions: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        prescriptions: list[dict[str, Any]] = []

        if path_group == "Malaria":
            is_severe = pyramid_level >= 3 or self.rng.random() < 0.10
            icd_code = "B50.0" if is_severe else "B50.9"
            icd_display = (
                "Paludisme à Plasmodium falciparum avec complications cérébrales"
                if is_severe
                else "Paludisme à Plasmodium falciparum, sans précision"
            )
            snomed_code = "240742007" if is_severe else "61462000"
            snomed_display = (
                "Infection à Plasmodium falciparum" if is_severe else "Paludisme (Concept standard)"
            )

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:malaria"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "Malaria",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "severe" if is_severe else "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            # Constantes LOINC : Fièvre >= 38.0°C obligatoire + TDR Positif
            temp_val = round(self.rng.uniform(38.5, 40.2), 1)
            obs_temp_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:temp"))
            observations.append(
                {
                    "observation_id": obs_temp_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "vital-signs",
                    "loinc_code": "8310-5",
                    "loinc_display": "Température corporelle",
                    "value_quantity": temp_val,
                    "value_numeric": temp_val,
                    "value_unit": "Cel",
                    "unit": "Cel",
                    "value_string": None,
                    "interpretation": "H",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            obs_tdr_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:tdr"))
            observations.append(
                {
                    "observation_id": obs_tdr_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "laboratory",
                    "loinc_code": "58900-2",
                    "loinc_display": "Test de Diagnostic Rapide (TDR) Paludisme",
                    "value_quantity": None,
                    "value_numeric": None,
                    "value_unit": None,
                    "unit": None,
                    "value_string": "Positif",
                    "interpretation": "A",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            # Traitement ATC : ACT ou Artésunate
            atc_code = "P01BE03" if is_severe else "P01BF01"
            med_name = (
                "Artésunate injectable 60mg"
                if is_severe
                else "Artéméther / Luméfantrine 20/120mg (ACT)"
            )
            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:malaria"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": atc_code,
                    "atc_display": med_name,
                    "medication_name": med_name,
                    "dosage_instruction": "1 prise matin et soir pendant 3 jours",
                    "quantity": 1.0,
                    "duration_days": 3,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "completed",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "ARI":
            icd_code = "J18.9"
            icd_display = "Pneumopathie, sans précision"
            snomed_code = "233604007"
            snomed_display = "Pneumonie"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:ari"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "ARI",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            resp_rate = float(self.rng.randint(28, 48))
            obs_resp_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:rr"))
            observations.append(
                {
                    "observation_id": obs_resp_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "vital-signs",
                    "loinc_code": "9279-1",
                    "loinc_display": "Fréquence respiratoire",
                    "value_quantity": resp_rate,
                    "value_numeric": resp_rate,
                    "value_unit": "{breaths}/min",
                    "unit": "{breaths}/min",
                    "value_string": None,
                    "interpretation": "H",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:amox"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "J01CA04",
                    "atc_display": "Amoxicilline 500mg gélule",
                    "medication_name": "Amoxicilline",
                    "dosage_instruction": "500mg 3 fois par jour pendant 7 jours",
                    "quantity": 21.0,
                    "duration_days": 7,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "completed",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "Diarrhea":
            icd_code = "A09.0"
            icd_display = "Autre gastro-entérite et colite infectieuse"
            snomed_code = "62315008"
            snomed_display = "Diarrhée"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:diarrhea"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "Diarrhea",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "mild",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:sro"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "A07CA",
                    "atc_display": "Sels de réhydratation orale (SRO)",
                    "medication_name": "SRO + Zinc",
                    "dosage_instruction": "1 sachet dilué dans 1 litre d'eau potable",
                    "quantity": 3.0,
                    "duration_days": 5,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "completed",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "HTA":
            icd_code = "I10"
            icd_display = "Hypertension essentielle (primitive)"
            snomed_code = "59621000"
            snomed_display = "Hypertension artérielle"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:hta"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "HTA",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            pas_val = float(self.rng.randint(145, 185))
            pad_val = float(self.rng.randint(92, 115))

            obs_pas_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:pas"))
            observations.append(
                {
                    "observation_id": obs_pas_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "vital-signs",
                    "loinc_code": "8480-6",
                    "loinc_display": "Pression artérielle systolique (PAS)",
                    "value_quantity": pas_val,
                    "value_numeric": pas_val,
                    "value_unit": "mm[Hg]",
                    "unit": "mm[Hg]",
                    "value_string": None,
                    "interpretation": "H",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            obs_pad_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:pad"))
            observations.append(
                {
                    "observation_id": obs_pad_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "vital-signs",
                    "loinc_code": "8462-4",
                    "loinc_display": "Pression artérielle diastolique (PAD)",
                    "value_quantity": pad_val,
                    "value_numeric": pad_val,
                    "value_unit": "mm[Hg]",
                    "unit": "mm[Hg]",
                    "value_string": None,
                    "interpretation": "H",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:amlo"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "C08CA01",
                    "atc_display": "Amlodipine 5mg",
                    "medication_name": "Amlodipine",
                    "dosage_instruction": "1 comprimé par jour le matin",
                    "quantity": 30.0,
                    "duration_days": 30,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "active",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "Diabetes":
            icd_code = "E11.9"
            icd_display = "Diabète de type 2 sans complication"
            snomed_code = "44054006"
            snomed_display = "Diabète de type 2"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:diab"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "Diabetes",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            glyc_val = round(self.rng.uniform(1.40, 2.60), 2)
            obs_glyc_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:glyc"))
            observations.append(
                {
                    "observation_id": obs_glyc_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "laboratory",
                    "loinc_code": "1558-6",
                    "loinc_display": "Glycémie à jeun sérum/plasma",
                    "value_quantity": glyc_val,
                    "value_numeric": glyc_val,
                    "value_unit": "g/L",
                    "unit": "g/L",
                    "value_string": None,
                    "interpretation": "H",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:metf"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "A10BA02",
                    "atc_display": "Metformine 850mg",
                    "medication_name": "Metformine",
                    "dosage_instruction": "1 comprimé midi et soir au milieu du repas",
                    "quantity": 60.0,
                    "duration_days": 30,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "active",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "SMI":
            # RÈGLE D'INTÉGRITÉ CLINIQUE ABSOLUE : ZÉRO GROSSESSE MASCULINE
            if patient["gender"] != "female" or not (15 <= patient["_age"] <= 49):
                # Remplacement de sécurité si violation de précondition
                return self._generate_pathology_data(
                    "Malaria", patient, encounter_id, encounter_date, pyramid_level
                )

            # CPN ou Accouchement
            is_delivery = pyramid_level >= 2 and self.rng.random() < 0.40
            if is_delivery:
                is_cesarean = pyramid_level >= 2 and self.rng.random() < 0.25
                icd_code = "O82" if is_cesarean else "O80"
                icd_display = (
                    "Accouchement par césarienne"
                    if is_cesarean
                    else "Accouchement spontané par voie basse"
                )
                snomed_code = "236973005"
                snomed_display = "Accouchement normal"
            else:
                icd_code = "Z34.0"
                icd_display = "Surveillance d'une première grossesse normale (CPN)"
                snomed_code = "169446002"
                snomed_display = "Soins prénatals (CPN)"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:smi"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "SMI",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "mild",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            obs_gest_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:gest"))
            gest_age = float(self.rng.randint(12, 39)) if not is_delivery else 39.0
            observations.append(
                {
                    "observation_id": obs_gest_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "exam",
                    "loinc_code": "11884-4",
                    "loinc_display": "Âge gestationnel",
                    "value_quantity": gest_age,
                    "value_numeric": gest_age,
                    "value_unit": "wk",
                    "unit": "wk",
                    "value_string": None,
                    "interpretation": "N",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            # Prescription : Fer + Acide folique
            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:folate"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "B03AA07",
                    "atc_display": "Fer ferreux et acide folique",
                    "medication_name": "Fer + Acide folique",
                    "dosage_instruction": "1 comprimé par jour tout au long de la grossesse",
                    "quantity": 30.0,
                    "duration_days": 30,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "active",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "Malnutrition":
            icd_code = "E44.0"
            icd_display = "Malnutrition protéino-énergétique modérée"
            snomed_code = "238107002"
            snomed_display = "Malnutrition aiguë modérée"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:maln"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "Malnutrition",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            muac_val = round(self.rng.uniform(115.0, 124.0), 1)
            obs_muac_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:muac"))
            observations.append(
                {
                    "observation_id": obs_muac_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "vital-signs",
                    "loinc_code": "56072-2",
                    "loinc_display": "Périmètre brachial (PB)",
                    "value_quantity": muac_val,
                    "value_numeric": muac_val,
                    "value_unit": "mm",
                    "unit": "mm",
                    "value_string": None,
                    "interpretation": "L",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:atpe"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "V06DX",
                    "atc_display": "Autres nutriments (ATPE / Plumpy'Nut)",
                    "medication_name": "Plumpy'Nut",
                    "dosage_instruction": "2 sachets par jour pendant 14 jours",
                    "quantity": 28.0,
                    "duration_days": 14,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "completed",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        elif path_group == "HIV":
            icd_code = "B24"
            icd_display = "Maladie par le VIH, sans précision"
            snomed_code = "86406008"
            snomed_display = "Infection à VIH"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:hiv"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "HIV",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            obs_hiv_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:hiv"))
            observations.append(
                {
                    "observation_id": obs_hiv_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "laboratory",
                    "loinc_code": "75622-1",
                    "loinc_display": "Test rapide dépistage VIH 1 et 2",
                    "value_quantity": None,
                    "value_numeric": None,
                    "value_unit": None,
                    "unit": None,
                    "value_string": "Positif",
                    "interpretation": "A",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:tld"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "J05AR13",
                    "atc_display": "Ténofovir disoproxil, lamivudine et dolutégravir (TLD)",
                    "medication_name": "TLD 300/300/50mg",
                    "dosage_instruction": "1 comprimé par jour au coucher",
                    "quantity": 30.0,
                    "duration_days": 30,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "active",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

        else:  # TB (Tuberculose)
            icd_code = "A15.0"
            icd_display = (
                "Tuberculose du poumon, confirmée par examen microscopique de l'expectoration"
            )
            snomed_code = "154283005"
            snomed_display = "Tuberculose pulmonaire"

            cond_id = str(uuid.uuid5(NAMESPACE_TOGO_CONDITION, f"{encounter_id}:cond:tb"))
            conditions.append(
                {
                    "condition_id": cond_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "pathology_group": "TB",
                    "icd10_code": icd_code,
                    "icd10_display": icd_display,
                    "snomed_code": snomed_code,
                    "snomed_display": snomed_display,
                    "clinical_status": "active",
                    "verification_status": "confirmed",
                    "severity": "moderate",
                    "onset_date": date_iso,
                    "onset_datetime": encounter_date,
                    "recorded_date": date_iso,
                }
            )

            obs_tb_id = str(uuid.uuid5(NAMESPACE_TOGO_OBSERVATION, f"{encounter_id}:obs:xpert"))
            observations.append(
                {
                    "observation_id": obs_tb_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "category": "laboratory",
                    "loinc_code": "89371-9",
                    "loinc_display": "GeneXpert MTB/RIF crachats",
                    "value_quantity": None,
                    "value_numeric": None,
                    "value_unit": None,
                    "unit": None,
                    "value_string": "MTB détecté",
                    "interpretation": "A",
                    "observation_datetime": encounter_date,
                    "effective_date": encounter_date,
                }
            )

            rx_id = str(uuid.uuid5(NAMESPACE_TOGO_PRESCRIPTION, f"{encounter_id}:rx:rhze"))
            prescriptions.append(
                {
                    "prescription_id": rx_id,
                    "medication_request_id": rx_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "atc_code": "J04AK02",
                    "atc_display": "Rifampicine, isoniazide, pyrazinamide et éthambutol (4FDC RHZE)",
                    "medication_name": "RHZE 150/75/400/275mg",
                    "dosage_instruction": "4 comprimés par jour le matin à jeun",
                    "quantity": 120.0,
                    "duration_days": 30,
                    "prescribed_date": date_iso,
                    "authored_on": encounter_date,
                    "status": "active",
                }
            )

            return conditions, observations, prescriptions, icd_code, icd_display

    def _generate_pev_immunizations(
        self,
        patient: dict[str, Any],
        encounters: list[dict[str, Any]],
        district_code: str,
        year: int,
    ) -> list[dict[str, Any]]:
        """Génère les actes vaccinaux du PEV Togo pour un enfant de moins de 2 ans."""
        patient_id = patient["patient_id"]
        # Sélection d'une structure de niveau 1 (CMS / USP) pour la vaccination
        usp_cands = [f for f in self.facilities_by_level[1] if f["district_code"] == district_code]
        facility = (
            self.rng.choice(usp_cands)
            if usp_cands
            else self.rng.choice(self.facilities_by_level[1])
        )

        facility_id = facility["facility_id"]
        # Référence à la première rencontre de l'enfant ou rencontre synthétique
        encounter_id = encounters[0]["encounter_id"] if encounters else str(uuid.uuid4())

        # Antigènes du calendrier PEV Togo avec codes ATC et doses
        pev_vaccines: list[tuple[str, str, str, str, int]] = [
            (
                "BCG",
                "Vaccin BCG",
                "Vaccin antituberculeux (BCG)",
                "J07AN01",
                1,
            ),
            (
                "VPO",
                "Vaccin Polio Oral",
                "Vaccin poliomyélitique oral bivalent (VPO)",
                "J07BF02",
                1,
            ),
            (
                "PENTA",
                "Vaccin Pentavalent",
                "Vaccin pentavalent DTC-HepB-Hib",
                "J07CA09",
                1,
            ),
            (
                "RR",
                "Vaccin Rougeole-Rubéole",
                "Vaccin combiné rougeole et rubéole (RR)",
                "J07BD53",
                1,
            ),
            (
                "VAA",
                "Vaccin Fièvre Jaune",
                "Vaccin contre la fièvre jaune (VAA)",
                "J07BL01",
                1,
            ),
        ]

        immunizations: list[dict[str, Any]] = []
        for idx, (v_code, v_disp, v_name, atc_code, dose_num) in enumerate(pev_vaccines):
            imm_id = str(
                uuid.uuid5(NAMESPACE_TOGO_IMMUNIZATION, f"{patient_id}:imm:{v_code}:{idx}")
            )
            # Date déterministe au cours de l'année
            occ_month = min(12, 1 + idx * 2)
            occ_day = 10 + (idx * 3) % 18
            occ_date = f"{year}-{occ_month:02d}-{occ_day:02d}"

            lot_num = f"TG-PEV-{year}-{v_code}-{(self.rng.randint(1, 99)):02d}"

            immunizations.append(
                {
                    "immunization_id": imm_id,
                    "patient_id": patient_id,
                    "encounter_id": encounter_id,
                    "facility_id": facility_id,
                    "vaccine_code": v_code,
                    "vaccine_display": v_disp,
                    "vaccine_name": v_name,
                    "atc_code": atc_code,
                    "dose_number": dose_num,
                    "lot_number": lot_num,
                    "occurrence_date": occ_date,
                    "administered_date": occ_date,
                    "status": "completed",
                }
            )

        return immunizations
