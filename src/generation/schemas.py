"""Définitions des schémas stricts PyArrow et des modèles Pydantic pour l'Étape 3.

Ce module formalise la structure des tables Parquet de Vérité Terrain (Ground Truth)
et des agrégats statistiques DHIS2 dataValueSets conformément à l'ADR D-04 et VAL-003.
"""

from __future__ import annotations

from typing import Any

import pyarrow as pa
from pydantic import BaseModel, ConfigDict, Field

# ==============================================================================
# Modèles Pydantic v2
# ==============================================================================


class PatientRecord(BaseModel):
    """Modèle d'un dossier patient synthétique togolais."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    patient_id: str = Field(..., description="UUID v5 immuable du patient")
    identifier_system: str = Field(..., description="URI du système d'identifiant patient")
    identifier_value: str = Field(..., description="Matricule lisible TG-PAT-XXXXXXX")
    nni: str = Field(..., description="Numéro National d'Identification togolais TG-NNI-XXXXXXX")
    family_name: str = Field(..., description="Patronyme togolais")
    given_name: str = Field(..., description="Prénom usuel togolais")
    gender: str = Field(..., description="'female' ou 'male'")
    birth_date: str = Field(..., description="Date de naissance YYYY-MM-DD")
    is_estimated_birth_date: bool = Field(..., description="Indicateur d'âge approximatif")
    estimated_age_flag: bool = Field(..., description="Alias conforme VAL-003")
    age_precision: str = Field(..., description="'exact' ou 'approximate-year'")
    phone_number: str = Field(..., description="Numéro togolais +228 XX XX XX XX")
    address_region_code: str = Field(..., description="Code région sanitaire TG-XXX")
    address_district_code: str = Field(..., description="Code district sanitaire TG-XXX-XXX")
    address_city: str = Field(..., description="Ville de résidence")
    residence_district_code: str = Field(..., description="Alias district de résidence")
    residence_region_code: str = Field(..., description="Alias région de résidence")
    marital_status: str = Field(..., description="'U', 'M', 'D', 'W'")
    ethnic_group: str = Field(..., description="Groupe ethno-linguistique")
    created_at: str = Field(..., description="Horodatage ISO de création")


class EncounterRecord(BaseModel):
    """Modèle d'un épisode de soins / consultation sanitaire."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    encounter_id: str = Field(..., description="UUID v5 du séjour/visite")
    patient_id: str = Field(..., description="UUID v5 du patient")
    facility_id: str = Field(..., description="UUID v5 de la structure sanitaire")
    facility_code: str = Field(..., description="Code de la structure TG-FAC-XXX")
    facility_name: str = Field(..., description="Nom de l'établissement")
    facility_category: str = Field(..., description="CHU, CHR, Hospital, CMS, USP")
    pyramid_level: int = Field(..., ge=1, le=4, description="Niveau de pyramide 1 à 4")
    district_code: str = Field(..., description="Code district sanitaire")
    region_code: str = Field(..., description="Code région sanitaire")
    encounter_class: str = Field(..., description="'ambulatory', 'inpatient', 'emergency'")
    encounter_type: str = Field(..., description="Alias modalité de consultation")
    start_date: str = Field(..., description="Horodatage début ISO 8601")
    start_datetime: str = Field(..., description="Alias début ISO")
    end_date: str = Field(..., description="Horodatage fin ISO 8601")
    end_datetime: str = Field(..., description="Alias fin ISO")
    reason_code: str = Field(..., description="Code motif principal CIM-10 / PEV")
    reason_display: str = Field(..., description="Libellé du motif en français")
    status: str = Field(..., description="'finished'")
    referral_from_facility_id: str | None = Field(
        None, description="UUID établissement d'origine si référence"
    )


class ConditionRecord(BaseModel):
    """Modèle d'un diagnostic médical lié à une rencontre."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    condition_id: str = Field(..., description="UUID v5 du diagnostic")
    patient_id: str = Field(..., description="UUID v5 du patient")
    encounter_id: str = Field(..., description="UUID v5 de la rencontre")
    pathology_group: str = Field(..., description="L'un des 9 groupes de pathologies prioritaires")
    icd10_code: str = Field(..., description="Code CIM-10 officiel")
    icd10_display: str = Field(..., description="Libellé CIM-10 français")
    snomed_code: str = Field(..., description="Code concept standard SNOMED CT")
    snomed_display: str = Field(..., description="Libellé SNOMED CT français")
    clinical_status: str = Field(..., description="'active', 'resolved', 'recurrence'")
    verification_status: str = Field(..., description="'confirmed'")
    severity: str = Field(..., description="'mild', 'moderate', 'severe'")
    onset_date: str = Field(..., description="Date début symptômes YYYY-MM-DD")
    onset_datetime: str = Field(..., description="Alias début ISO")
    recorded_date: str = Field(..., description="Date de consignation YYYY-MM-DD")


class ObservationRecord(BaseModel):
    """Modèle d'une constante vitale ou d'un examen biologique (LOINC)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str = Field(..., description="UUID v5 de l'observation")
    patient_id: str = Field(..., description="UUID v5 du patient")
    encounter_id: str = Field(..., description="UUID v5 de la rencontre")
    category: str = Field(..., description="'vital-signs', 'laboratory', 'exam'")
    loinc_code: str = Field(..., description="Code standard LOINC")
    loinc_display: str = Field(..., description="Libellé LOINC français")
    value_quantity: float | None = Field(None, description="Valeur quantitative")
    value_numeric: float | None = Field(None, description="Alias valeur quantitative")
    value_unit: str | None = Field(None, description="Unité UCUM standard")
    unit: str | None = Field(None, description="Alias unité UCUM")
    value_string: str | None = Field(None, description="Valeur textuelle / résultat qualitatif")
    interpretation: str | None = Field(None, description="'N', 'H', 'L', 'A'")
    observation_datetime: str = Field(..., description="Horodatage ISO de mesure")
    effective_date: str = Field(..., description="Alias horodatage ISO")


class PrescriptionRecord(BaseModel):
    """Modèle d'une prescription médicamenteuse (ATC)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prescription_id: str = Field(..., description="UUID v5 de la prescription")
    medication_request_id: str = Field(..., description="Alias UUID v5 compatible FHIR")
    patient_id: str = Field(..., description="UUID v5 du patient")
    encounter_id: str = Field(..., description="UUID v5 de la rencontre")
    atc_code: str = Field(..., description="Code officiel ATC OMS")
    atc_display: str = Field(..., description="Dénomination commune internationale")
    medication_name: str = Field(..., description="Nom usuel du médicament")
    dosage_instruction: str = Field(..., description="Posologie textuelle en français")
    quantity: float = Field(..., gt=0, description="Quantité totale prescrite")
    duration_days: int = Field(..., gt=0, description="Durée de traitement en jours")
    prescribed_date: str = Field(..., description="Date de prescription YYYY-MM-DD")
    authored_on: str = Field(..., description="Alias date de prescription ISO")
    status: str = Field(..., description="'active' ou 'completed'")


class ImmunizationRecord(BaseModel):
    """Modèle d'un acte vaccinal du calendrier PEV Togo."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    immunization_id: str = Field(..., description="UUID v5 de l'acte vaccinal")
    patient_id: str = Field(..., description="UUID v5 du patient")
    encounter_id: str = Field(..., description="UUID v5 de la rencontre")
    facility_id: str = Field(..., description="UUID v5 de l'établissement")
    vaccine_code: str = Field(..., description="Code antigène PEV (BCG, VPO, PENTA, etc.)")
    vaccine_display: str = Field(..., description="Libellé court français du vaccin")
    vaccine_name: str = Field(..., description="Dénomination complète du vaccin")
    atc_code: str = Field(..., description="Code ATC correspondant")
    dose_number: int = Field(..., ge=1, le=5, description="Numéro de dose")
    lot_number: str = Field(..., description="Numéro de lot pharmaceutique")
    occurrence_date: str = Field(..., description="Date d'administration YYYY-MM-DD")
    administered_date: str = Field(..., description="Alias date d'administration")
    status: str = Field(..., description="'completed'")


class Dhis2DataValueRecord(BaseModel):
    """Modèle d'un agrégat statistique mensuel DHIS2 dataValueSets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    data_element_id: str = Field(..., description="Identifiant indicateur DHIS2")
    data_element_name: str = Field(..., description="Nom lisible de l'indicateur")
    period: str = Field(..., description="Période mensuelle format YYYYMM")
    org_unit_id: str = Field(..., description="Code ou identifiant entité géographique")
    district_code: str = Field(..., description="Code district sanitaire TG-XXX-XXX")
    org_unit_name: str = Field(..., description="Nom du district sanitaire")
    district_name: str = Field(..., description="Nom du district")
    region_code: str = Field(..., description="Code de la région sanitaire")
    category_option_combo: str = Field(..., description="Désagrégation COC_DEFAULT / <5ans")
    attribute_option_combo: str = Field(..., description="AOC_DEFAULT")
    value: int = Field(..., ge=0, description="Valeur statistique agrégée")
    stored_by: str = Field(..., description="Système rapporteur")
    created: str = Field(..., description="Horodatage ISO de création")
    last_updated: str = Field(..., description="Horodatage ISO de mise à jour")


# ==============================================================================
# Schémas Stricts PyArrow
# ==============================================================================

PATIENT_SCHEMA = pa.schema(
    [
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("identifier_system", pa.string(), nullable=False),
        pa.field("identifier_value", pa.string(), nullable=False),
        pa.field("nni", pa.string(), nullable=False),
        pa.field("family_name", pa.string(), nullable=False),
        pa.field("given_name", pa.string(), nullable=False),
        pa.field("gender", pa.string(), nullable=False),
        pa.field("birth_date", pa.string(), nullable=False),
        pa.field("is_estimated_birth_date", pa.bool_(), nullable=False),
        pa.field("estimated_age_flag", pa.bool_(), nullable=False),
        pa.field("age_precision", pa.string(), nullable=False),
        pa.field("phone_number", pa.string(), nullable=False),
        pa.field("address_region_code", pa.string(), nullable=False),
        pa.field("address_district_code", pa.string(), nullable=False),
        pa.field("address_city", pa.string(), nullable=False),
        pa.field("residence_district_code", pa.string(), nullable=False),
        pa.field("residence_region_code", pa.string(), nullable=False),
        pa.field("marital_status", pa.string(), nullable=False),
        pa.field("ethnic_group", pa.string(), nullable=False),
        pa.field("created_at", pa.string(), nullable=False),
    ]
)

ENCOUNTER_SCHEMA = pa.schema(
    [
        pa.field("encounter_id", pa.string(), nullable=False),
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("facility_id", pa.string(), nullable=False),
        pa.field("facility_code", pa.string(), nullable=False),
        pa.field("facility_name", pa.string(), nullable=False),
        pa.field("facility_category", pa.string(), nullable=False),
        pa.field("pyramid_level", pa.int64(), nullable=False),
        pa.field("district_code", pa.string(), nullable=False),
        pa.field("region_code", pa.string(), nullable=False),
        pa.field("encounter_class", pa.string(), nullable=False),
        pa.field("encounter_type", pa.string(), nullable=False),
        pa.field("start_date", pa.string(), nullable=False),
        pa.field("start_datetime", pa.string(), nullable=False),
        pa.field("end_date", pa.string(), nullable=False),
        pa.field("end_datetime", pa.string(), nullable=False),
        pa.field("reason_code", pa.string(), nullable=False),
        pa.field("reason_display", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("referral_from_facility_id", pa.string(), nullable=True),
    ]
)

CONDITION_SCHEMA = pa.schema(
    [
        pa.field("condition_id", pa.string(), nullable=False),
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("encounter_id", pa.string(), nullable=False),
        pa.field("pathology_group", pa.string(), nullable=False),
        pa.field("icd10_code", pa.string(), nullable=False),
        pa.field("icd10_display", pa.string(), nullable=False),
        pa.field("snomed_code", pa.string(), nullable=False),
        pa.field("snomed_display", pa.string(), nullable=False),
        pa.field("clinical_status", pa.string(), nullable=False),
        pa.field("verification_status", pa.string(), nullable=False),
        pa.field("severity", pa.string(), nullable=False),
        pa.field("onset_date", pa.string(), nullable=False),
        pa.field("onset_datetime", pa.string(), nullable=False),
        pa.field("recorded_date", pa.string(), nullable=False),
    ]
)

OBSERVATION_SCHEMA = pa.schema(
    [
        pa.field("observation_id", pa.string(), nullable=False),
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("encounter_id", pa.string(), nullable=False),
        pa.field("category", pa.string(), nullable=False),
        pa.field("loinc_code", pa.string(), nullable=False),
        pa.field("loinc_display", pa.string(), nullable=False),
        pa.field("value_quantity", pa.float64(), nullable=True),
        pa.field("value_numeric", pa.float64(), nullable=True),
        pa.field("value_unit", pa.string(), nullable=True),
        pa.field("unit", pa.string(), nullable=True),
        pa.field("value_string", pa.string(), nullable=True),
        pa.field("interpretation", pa.string(), nullable=True),
        pa.field("observation_datetime", pa.string(), nullable=False),
        pa.field("effective_date", pa.string(), nullable=False),
    ]
)

PRESCRIPTION_SCHEMA = pa.schema(
    [
        pa.field("prescription_id", pa.string(), nullable=False),
        pa.field("medication_request_id", pa.string(), nullable=False),
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("encounter_id", pa.string(), nullable=False),
        pa.field("atc_code", pa.string(), nullable=False),
        pa.field("atc_display", pa.string(), nullable=False),
        pa.field("medication_name", pa.string(), nullable=False),
        pa.field("dosage_instruction", pa.string(), nullable=False),
        pa.field("quantity", pa.float64(), nullable=False),
        pa.field("duration_days", pa.int64(), nullable=False),
        pa.field("prescribed_date", pa.string(), nullable=False),
        pa.field("authored_on", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
    ]
)

IMMUNIZATION_SCHEMA = pa.schema(
    [
        pa.field("immunization_id", pa.string(), nullable=False),
        pa.field("patient_id", pa.string(), nullable=False),
        pa.field("encounter_id", pa.string(), nullable=False),
        pa.field("facility_id", pa.string(), nullable=False),
        pa.field("vaccine_code", pa.string(), nullable=False),
        pa.field("vaccine_display", pa.string(), nullable=False),
        pa.field("vaccine_name", pa.string(), nullable=False),
        pa.field("atc_code", pa.string(), nullable=False),
        pa.field("dose_number", pa.int64(), nullable=False),
        pa.field("lot_number", pa.string(), nullable=False),
        pa.field("occurrence_date", pa.string(), nullable=False),
        pa.field("administered_date", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
    ]
)

DHIS2_DATA_VALUE_SCHEMA = pa.schema(
    [
        pa.field("data_element_id", pa.string(), nullable=False),
        pa.field("data_element_name", pa.string(), nullable=False),
        pa.field("period", pa.string(), nullable=False),
        pa.field("org_unit_id", pa.string(), nullable=False),
        pa.field("district_code", pa.string(), nullable=False),
        pa.field("org_unit_name", pa.string(), nullable=False),
        pa.field("district_name", pa.string(), nullable=False),
        pa.field("region_code", pa.string(), nullable=False),
        pa.field("category_option_combo", pa.string(), nullable=False),
        pa.field("attribute_option_combo", pa.string(), nullable=False),
        pa.field("value", pa.int64(), nullable=False),
        pa.field("stored_by", pa.string(), nullable=False),
        pa.field("created", pa.string(), nullable=False),
        pa.field("last_updated", pa.string(), nullable=False),
    ]
)

TABLE_SCHEMAS: dict[str, pa.Schema] = {
    "patients": PATIENT_SCHEMA,
    "encounters": ENCOUNTER_SCHEMA,
    "conditions": CONDITION_SCHEMA,
    "observations": OBSERVATION_SCHEMA,
    "prescriptions": PRESCRIPTION_SCHEMA,
    "immunizations": IMMUNIZATION_SCHEMA,
    "dhis2_data_values": DHIS2_DATA_VALUE_SCHEMA,
}

MODEL_CLASSES: dict[str, type[BaseModel]] = {
    "patients": PatientRecord,
    "encounters": EncounterRecord,
    "conditions": ConditionRecord,
    "observations": ObservationRecord,
    "prescriptions": PrescriptionRecord,
    "immunizations": ImmunizationRecord,
    "dhis2_data_values": Dhis2DataValueRecord,
}


def create_pyarrow_table(records: list[dict[str, Any]], schema: pa.Schema) -> pa.Table:
    """Crée une table PyArrow typée strictement à partir d'une liste de dictionnaires."""
    if not records:
        # Table vide respectant strictement le schéma
        arrays = [pa.array([], type=field.type) for field in schema]
        return pa.Table.from_arrays(arrays, schema=schema)

    # Extraction ordonnée selon les champs du schéma
    columns: dict[str, list[Any]] = {field.name: [] for field in schema}
    for record in records:
        for field in schema:
            columns[field.name].append(record.get(field.name))

    arrays = [pa.array(columns[field.name], type=field.type) for field in schema]
    return pa.Table.from_arrays(arrays, schema=schema)
