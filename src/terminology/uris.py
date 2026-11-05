"""Module canonique des URIs d'interopérabilité sanitaire pour le Togo.

Ce module définit l'autorité racine, les espaces de noms d'identifiants (NamingSystems / SIDs),
les CodeSystems locaux, les ValueSets, les profils nationaux StructureDefinition
et les terminologies internationales de référence pour le pipeline FHIR Togo.

Fournit des constantes typées, des énumérations normalisées et des fonctions
utilitaires pour l'accès programmatique et la validation d'intégrité.
"""

from __future__ import annotations

from enum import StrEnum

# ==============================================================================
# 0. Autorité Racine Nationale
# ==============================================================================
BASE_URI: str = "http://interop-sante.gouv.tg/fhir"


# ==============================================================================
# 1. Identifier Systems (NamingSystems / SIDs)
# ==============================================================================
# Identifiant Maître Patient (IUP déterministe / Splink)
URI_PATIENT_MPI: str = f"{BASE_URI}/sid/patient-mpi"

# Numéro National d'Identification civil togolais (carte d'identité / biométrie)
URI_PATIENT_NNI: str = f"{BASE_URI}/sid/nni"

# Identifiant local patient dans le dossier médical source (IPP établissement)
URI_PATIENT_LOCAL: str = f"{BASE_URI}/sid/patient-local"

# Identifiant national unique de la formation sanitaire (FOSA)
URI_FACILITY: str = f"{BASE_URI}/sid/facility"

# Code du district sanitaire (44 districts officiels, ADR D-08)
URI_DISTRICT: str = f"{BASE_URI}/sid/district"

# Code de la région sanitaire (6 régions officielles, ADR D-08)
URI_REGION: str = f"{BASE_URI}/sid/region"

# Identifiant unique de séjour, consultation ou visite (Encounter)
URI_ENCOUNTER: str = f"{BASE_URI}/sid/encounter"

# Identifiant national des professionnels de santé (Ordre / Matricule)
URI_PRACTITIONER: str = f"{BASE_URI}/sid/practitioner"


# ==============================================================================
# 2. Local CodeSystems (Vocabulaires Contrôlés Nationaux)
# ==============================================================================
# Catégories de la pyramide sanitaire (CHU, CHR, Hospital, CMS, USP)
URI_CS_FACILITY_CATEGORY: str = f"{BASE_URI}/cs/facility-category"

# Nomenclature officielle des 6 régions sanitaires
URI_CS_HEALTH_REGION: str = f"{BASE_URI}/cs/health-region"

# Nomenclature officielle des 44 districts sanitaires
URI_CS_HEALTH_DISTRICT: str = f"{BASE_URI}/cs/health-district"

# Catalogue officiel des 9 pathologies prioritaires togolaises
URI_CS_PRIORITY_PATHOLOGY: str = f"{BASE_URI}/cs/priority-pathology"

# Nomenclature des vaccins du Programme Élargi de Vaccination (PEV)
URI_CS_PEV_VACCINES: str = f"{BASE_URI}/cs/pev-vaccines"

# Libellés cliniques usuels en français libre
URI_CS_LOCAL_TERMS: str = f"{BASE_URI}/cs/local-clinical-terms"

# Précision sur les dates de naissance estimées
URI_CS_AGE_PRECISION: str = f"{BASE_URI}/cs/age-precision"


# ==============================================================================
# 3. Local ValueSets (Jeux de Valeurs Autorisées)
# ==============================================================================
URI_VS_FACILITY_CATEGORY: str = f"{BASE_URI}/vs/facility-category"
URI_VS_HEALTH_REGION: str = f"{BASE_URI}/vs/health-region"
URI_VS_HEALTH_DISTRICT: str = f"{BASE_URI}/vs/health-district"
URI_VS_PRIORITY_PATHOLOGY: str = f"{BASE_URI}/vs/priority-pathology"
URI_VS_PEV_VACCINES: str = f"{BASE_URI}/vs/pev-vaccines"


# ==============================================================================
# 4. StructureDefinitions & Extensions (Profils IG FHIR Togo)
# ==============================================================================
URI_PROFILE_PATIENT: str = f"{BASE_URI}/StructureDefinition/togo-patient"
URI_PROFILE_ENCOUNTER: str = f"{BASE_URI}/StructureDefinition/togo-encounter"
URI_PROFILE_CONDITION: str = f"{BASE_URI}/StructureDefinition/togo-condition"
URI_PROFILE_OBSERVATION: str = f"{BASE_URI}/StructureDefinition/togo-observation"
URI_PROFILE_PROCEDURE: str = f"{BASE_URI}/StructureDefinition/togo-procedure"
URI_PROFILE_MEDICATION_REQUEST: str = f"{BASE_URI}/StructureDefinition/togo-medication-request"
URI_PROFILE_IMMUNIZATION: str = f"{BASE_URI}/StructureDefinition/togo-immunization"
URI_PROFILE_ORGANIZATION: str = f"{BASE_URI}/StructureDefinition/togo-organization"
URI_PROFILE_LOCATION: str = f"{BASE_URI}/StructureDefinition/togo-location"

URI_EXT_ESTIMATED_AGE: str = f"{BASE_URI}/StructureDefinition/estimated-age-precision"
URI_EXT_DISTRICT_REF: str = f"{BASE_URI}/StructureDefinition/health-district-reference"


# ==============================================================================
# 5. Standard International Systems (Terminologies Médicales Mondiales)
# ==============================================================================
# Classification Internationale des Maladies (CIM-10 / ICD-10)
URI_ICD10: str = "http://hl7.org/fhir/sid/icd-10"

# Système Normalisé de Nomenclature Médicale (SNOMED CT)
URI_SNOMED_CT: str = "http://snomed.info/sct"

# Logical Observation Identifiers Names and Codes (LOINC)
URI_LOINC: str = "http://loinc.org"

# Anatomical Therapeutic Chemical classification system (ATC)
URI_ATC: str = "http://www.whocc.no/atc"

# Unified Code for Units of Measure (UCUM)
URI_UCUM: str = "http://unitsofmeasure.org"


# ==============================================================================
# 6. Énumérations Normalisées (Enums Typés)
# ==============================================================================
class IdentifierSystem(StrEnum):
    """Espaces de noms des identifiants (NamingSystems / SIDs)."""

    PATIENT_MPI = URI_PATIENT_MPI
    PATIENT_NNI = URI_PATIENT_NNI
    PATIENT_LOCAL = URI_PATIENT_LOCAL
    FACILITY = URI_FACILITY
    DISTRICT = URI_DISTRICT
    REGION = URI_REGION
    ENCOUNTER = URI_ENCOUNTER
    PRACTITIONER = URI_PRACTITIONER


class LocalCodeSystem(StrEnum):
    """Nomenclatures contrôlées nationales (CodeSystems locaux Togo)."""

    FACILITY_CATEGORY = URI_CS_FACILITY_CATEGORY
    HEALTH_REGION = URI_CS_HEALTH_REGION
    HEALTH_DISTRICT = URI_CS_HEALTH_DISTRICT
    PRIORITY_PATHOLOGY = URI_CS_PRIORITY_PATHOLOGY
    PEV_VACCINES = URI_CS_PEV_VACCINES
    LOCAL_TERMS = URI_CS_LOCAL_TERMS
    AGE_PRECISION = URI_CS_AGE_PRECISION


class LocalValueSet(StrEnum):
    """Jeux de valeurs autorisées (ValueSets locaux Togo)."""

    FACILITY_CATEGORY = URI_VS_FACILITY_CATEGORY
    HEALTH_REGION = URI_VS_HEALTH_REGION
    HEALTH_DISTRICT = URI_VS_HEALTH_DISTRICT
    PRIORITY_PATHOLOGY = URI_VS_PRIORITY_PATHOLOGY
    PEV_VACCINES = URI_VS_PEV_VACCINES


class TogoProfile(StrEnum):
    """Profils nationaux StructureDefinition (IG FHIR Togo)."""

    PATIENT = URI_PROFILE_PATIENT
    ENCOUNTER = URI_PROFILE_ENCOUNTER
    CONDITION = URI_PROFILE_CONDITION
    OBSERVATION = URI_PROFILE_OBSERVATION
    PROCEDURE = URI_PROFILE_PROCEDURE
    MEDICATION_REQUEST = URI_PROFILE_MEDICATION_REQUEST
    IMMUNIZATION = URI_PROFILE_IMMUNIZATION
    ORGANIZATION = URI_PROFILE_ORGANIZATION
    LOCATION = URI_PROFILE_LOCATION


class StandardSystem(StrEnum):
    """Systèmes terminologiques internationaux de référence."""

    ICD10 = URI_ICD10
    SNOMED_CT = URI_SNOMED_CT
    LOINC = URI_LOINC
    ATC = URI_ATC
    UCUM = URI_UCUM


# ==============================================================================
# 7. Registres et Ensembles de Contrôle
# ==============================================================================
ALL_CANONICAL_URIS: frozenset[str] = frozenset(
    [
        BASE_URI,
        # SIDs
        URI_PATIENT_MPI,
        URI_PATIENT_NNI,
        URI_PATIENT_LOCAL,
        URI_FACILITY,
        URI_DISTRICT,
        URI_REGION,
        URI_ENCOUNTER,
        URI_PRACTITIONER,
        # CodeSystems
        URI_CS_FACILITY_CATEGORY,
        URI_CS_HEALTH_REGION,
        URI_CS_HEALTH_DISTRICT,
        URI_CS_PRIORITY_PATHOLOGY,
        URI_CS_PEV_VACCINES,
        URI_CS_LOCAL_TERMS,
        URI_CS_AGE_PRECISION,
        # ValueSets
        URI_VS_FACILITY_CATEGORY,
        URI_VS_HEALTH_REGION,
        URI_VS_HEALTH_DISTRICT,
        URI_VS_PRIORITY_PATHOLOGY,
        URI_VS_PEV_VACCINES,
        # Profils & Extensions
        URI_PROFILE_PATIENT,
        URI_PROFILE_ENCOUNTER,
        URI_PROFILE_CONDITION,
        URI_PROFILE_OBSERVATION,
        URI_PROFILE_PROCEDURE,
        URI_PROFILE_MEDICATION_REQUEST,
        URI_PROFILE_IMMUNIZATION,
        URI_PROFILE_ORGANIZATION,
        URI_PROFILE_LOCATION,
        URI_EXT_ESTIMATED_AGE,
        URI_EXT_DISTRICT_REF,
        # Standard Systems
        URI_ICD10,
        URI_SNOMED_CT,
        URI_LOINC,
        URI_ATC,
        URI_UCUM,
    ]
)

NAMING_SYSTEM_REGISTRY: dict[str, dict[str, str]] = {
    "patient-mpi": {
        "uri": URI_PATIENT_MPI,
        "name": "Identifiant Unique Patient (MPI / Splink)",
        "type": "IUP",
        "description": "Identifiant déterministe issu de la réconciliation Splink.",
    },
    "nni": {
        "uri": URI_PATIENT_NNI,
        "name": "Numéro National d'Identification",
        "type": "Civil",
        "description": "Identifiant de la carte d'identité ou du registre biométrique togolais.",
    },
    "patient-local": {
        "uri": URI_PATIENT_LOCAL,
        "name": "Identifiant Patient Local (IPP)",
        "type": "Local",
        "description": "Identifiant patient propre à la formation sanitaire source.",
    },
    "facility": {
        "uri": URI_FACILITY,
        "name": "Identifiant Formation Sanitaire (FOSA)",
        "type": "Structure",
        "description": "Code national unique d'identification des établissements de santé.",
    },
    "district": {
        "uri": URI_DISTRICT,
        "name": "Identifiant District Sanitaire",
        "type": "Territoire",
        "description": "Code officiel des 44 districts sanitaires du Togo (ADR D-08).",
    },
    "region": {
        "uri": URI_REGION,
        "name": "Identifiant Région Sanitaire",
        "type": "Territoire",
        "description": "Code officiel des 6 régions sanitaires du Togo (ADR D-08).",
    },
    "encounter": {
        "uri": URI_ENCOUNTER,
        "name": "Identifiant Consultation / Séjour",
        "type": "Activité",
        "description": "Numéro unique de visite ou d'hospitalisation.",
    },
    "practitioner": {
        "uri": URI_PRACTITIONER,
        "name": "Identifiant Professionnel de Santé",
        "type": "Praticien",
        "description": "Numéro d'inscription à l'Ordre ou matricule ministériel.",
    },
}

LOCAL_CODESYSTEM_REGISTRY: dict[str, dict[str, str]] = {
    "facility-category": {
        "uri": URI_CS_FACILITY_CATEGORY,
        "name": "Catégories d'Établissements de Santé",
        "description": "Nomenclature des 4 niveaux de la pyramide (CHU, CHR, Hospital, CMS, USP).",
    },
    "health-region": {
        "uri": URI_CS_HEALTH_REGION,
        "name": "Régions Sanitaires du Togo",
        "description": "Nomenclature officielle des 6 régions sanitaires (ADR D-08).",
    },
    "health-district": {
        "uri": URI_CS_HEALTH_DISTRICT,
        "name": "Districts Sanitaires du Togo",
        "description": "Nomenclature officielle des 44 districts sanitaires (ADR D-08).",
    },
    "priority-pathology": {
        "uri": URI_CS_PRIORITY_PATHOLOGY,
        "name": "Pathologies Prioritaires Togolaises",
        "description": "Catalogue des 9 pathologies prioritaires nationales.",
    },
    "pev-vaccines": {
        "uri": URI_CS_PEV_VACCINES,
        "name": "Vaccins du PEV",
        "description": "Antigènes du Programme Élargi de Vaccination du Togo.",
    },
    "local-clinical-terms": {
        "uri": URI_CS_LOCAL_TERMS,
        "name": "Termes Cliniques Locaux",
        "description": "Libellés médicaux francophones usuels non standardisés.",
    },
    "age-precision": {
        "uri": URI_CS_AGE_PRECISION,
        "name": "Précision d'Âge Estimé",
        "description": "Qualification du niveau de précision des dates de naissance.",
    },
}

STANDARD_SYSTEM_REGISTRY: dict[str, dict[str, str]] = {
    "icd-10": {
        "uri": URI_ICD10,
        "name": "CIM-10 / ICD-10",
        "authority": "WHO / HL7",
        "domain": "Condition",
    },
    "snomed-ct": {
        "uri": URI_SNOMED_CT,
        "name": "SNOMED Clinical Terms",
        "authority": "SNOMED International",
        "domain": "Clinical Finding / Procedure",
    },
    "loinc": {
        "uri": URI_LOINC,
        "name": "LOINC",
        "authority": "Regenstrief Institute",
        "domain": "Observation / Measurement",
    },
    "atc": {
        "uri": URI_ATC,
        "name": "ATC",
        "authority": "WHO CC",
        "domain": "Medication",
    },
    "ucum": {
        "uri": URI_UCUM,
        "name": "UCUM",
        "authority": "Regenstrief Institute",
        "domain": "Units of Measure",
    },
}


# ==============================================================================
# 8. Fonctions Utilitaires d'Accès Programmatique et de Validation
# ==============================================================================
def is_canonical_uri(uri: str) -> bool:
    """Vérifie si une URI donnée fait partie des URI canoniques reconnues."""
    if not isinstance(uri, str):
        return False
    return uri in ALL_CANONICAL_URIS


def is_togo_authority_uri(uri: str) -> bool:
    """Vérifie si une URI est issue de l'autorité nationale d'interopérabilité togolaise."""
    if not isinstance(uri, str):
        return False
    return uri == BASE_URI or uri.startswith(f"{BASE_URI}/")


def validate_canonical_uri(uri: str) -> bool:
    """Valide qu'une chaîne est une URI canonique valide supportée par le pipeline."""
    return is_canonical_uri(uri)


def get_identifier_system(name_or_alias: str) -> str:
    """Résout un nom ou alias d'identifiant vers son URI NamingSystem officielle.

    Args:
        name_or_alias: Alias (ex: 'mpi', 'patient-mpi', 'nni', 'local', 'facility',
            'district', 'region', 'encounter', 'practitioner').

    Returns:
        L'URI canonique correspondante.

    Raises:
        KeyError: Si l'alias ne correspond à aucun système d'identifiant connu.
    """
    key = name_or_alias.lower().strip().replace("_", "-")
    alias_map: dict[str, str] = {
        "mpi": URI_PATIENT_MPI,
        "patient-mpi": URI_PATIENT_MPI,
        "iup": URI_PATIENT_MPI,
        "nni": URI_PATIENT_NNI,
        "national-id": URI_PATIENT_NNI,
        "cni": URI_PATIENT_NNI,
        "local": URI_PATIENT_LOCAL,
        "patient-local": URI_PATIENT_LOCAL,
        "ipp": URI_PATIENT_LOCAL,
        "facility": URI_FACILITY,
        "facility-id": URI_FACILITY,
        "fosa": URI_FACILITY,
        "district": URI_DISTRICT,
        "district-id": URI_DISTRICT,
        "region": URI_REGION,
        "region-id": URI_REGION,
        "encounter": URI_ENCOUNTER,
        "encounter-id": URI_ENCOUNTER,
        "visite": URI_ENCOUNTER,
        "sejour": URI_ENCOUNTER,
        "practitioner": URI_PRACTITIONER,
        "practitioner-id": URI_PRACTITIONER,
        "medecin": URI_PRACTITIONER,
    }
    if key in alias_map:
        return alias_map[key]
    raise KeyError(
        f"Système d'identifiant inconnu : '{name_or_alias}'. "
        f"Valeurs valides : {sorted(alias_map.keys())}"
    )


def get_code_system(name_or_alias: str) -> str:
    """Résout un nom ou alias de CodeSystem local vers son URI canonique.

    Args:
        name_or_alias: Alias (ex: 'facility-category', 'region', 'district',
            'pathology', 'pev', 'local-terms', 'age-precision').

    Returns:
        L'URI canonique du CodeSystem.

    Raises:
        KeyError: Si l'alias ne correspond à aucun CodeSystem local connu.
    """
    key = name_or_alias.lower().strip().replace("_", "-")
    alias_map: dict[str, str] = {
        "facility-category": URI_CS_FACILITY_CATEGORY,
        "category": URI_CS_FACILITY_CATEGORY,
        "facility-level": URI_CS_FACILITY_CATEGORY,
        "health-region": URI_CS_HEALTH_REGION,
        "region": URI_CS_HEALTH_REGION,
        "health-district": URI_CS_HEALTH_DISTRICT,
        "district": URI_CS_HEALTH_DISTRICT,
        "priority-pathology": URI_CS_PRIORITY_PATHOLOGY,
        "pathology": URI_CS_PRIORITY_PATHOLOGY,
        "pathologies": URI_CS_PRIORITY_PATHOLOGY,
        "pev-vaccines": URI_CS_PEV_VACCINES,
        "pev": URI_CS_PEV_VACCINES,
        "vaccines": URI_CS_PEV_VACCINES,
        "local-clinical-terms": URI_CS_LOCAL_TERMS,
        "local-terms": URI_CS_LOCAL_TERMS,
        "age-precision": URI_CS_AGE_PRECISION,
    }
    if key in alias_map:
        return alias_map[key]
    raise KeyError(
        f"CodeSystem local inconnu : '{name_or_alias}'. "
        f"Valeurs valides : {sorted(alias_map.keys())}"
    )


def get_standard_system(name_or_alias: str) -> str:
    """Résout un nom ou alias de système standard vers son URI canonique officielle.

    Args:
        name_or_alias: Alias (ex: 'icd10', 'cim10', 'snomed', 'loinc', 'atc', 'ucum').

    Returns:
        L'URI canonique standard.

    Raises:
        KeyError: Si l'alias ne correspond à aucun système standard connu.
    """
    key = name_or_alias.lower().strip().replace("_", "-")
    alias_map: dict[str, str] = {
        "icd10": URI_ICD10,
        "icd-10": URI_ICD10,
        "cim10": URI_ICD10,
        "cim-10": URI_ICD10,
        "snomed": URI_SNOMED_CT,
        "snomed-ct": URI_SNOMED_CT,
        "sct": URI_SNOMED_CT,
        "loinc": URI_LOINC,
        "atc": URI_ATC,
        "ucum": URI_UCUM,
    }
    if key in alias_map:
        return alias_map[key]
    raise KeyError(
        f"Système international inconnu : '{name_or_alias}'. "
        f"Valeurs valides : {sorted(alias_map.keys())}"
    )


def get_profile_uri(resource_name: str) -> str:
    """Résout un nom de ressource FHIR vers l'URI de son profil national IG Togo.

    Args:
        resource_name: Nom de la ressource (ex: 'Patient', 'Encounter', 'Condition', ...).

    Returns:
        L'URI canonique du profil Togo.

    Raises:
        KeyError: Si la ressource ne dispose pas de profil national Togo.
    """
    key = resource_name.lower().strip().replace("_", "-")
    if key.startswith("togo-"):
        key = key[5:]
    profile_map: dict[str, str] = {
        "patient": URI_PROFILE_PATIENT,
        "encounter": URI_PROFILE_ENCOUNTER,
        "condition": URI_PROFILE_CONDITION,
        "observation": URI_PROFILE_OBSERVATION,
        "procedure": URI_PROFILE_PROCEDURE,
        "medicationrequest": URI_PROFILE_MEDICATION_REQUEST,
        "medication-request": URI_PROFILE_MEDICATION_REQUEST,
        "immunization": URI_PROFILE_IMMUNIZATION,
        "organization": URI_PROFILE_ORGANIZATION,
        "location": URI_PROFILE_LOCATION,
    }
    if key in profile_map:
        return profile_map[key]
    raise KeyError(
        f"Profil Togo inconnu pour la ressource : '{resource_name}'. "
        f"Ressources supportées : {sorted(profile_map.keys())}"
    )


def build_sid_uri(sid_name: str) -> str:
    """Construit une URI de NamingSystem sous l'autorité racine du Togo."""
    clean_name = sid_name.strip().strip("/") if isinstance(sid_name, str) else ""
    if not clean_name:
        raise ValueError("Le nom de SID ne peut pas être vide.")
    return f"{BASE_URI}/sid/{clean_name}"


def build_cs_uri(cs_name: str) -> str:
    """Construit une URI de CodeSystem sous l'autorité racine du Togo."""
    clean_name = cs_name.strip().strip("/") if isinstance(cs_name, str) else ""
    if not clean_name:
        raise ValueError("Le nom de CodeSystem ne peut pas être vide.")
    return f"{BASE_URI}/cs/{clean_name}"


def build_vs_uri(vs_name: str) -> str:
    """Construit une URI de ValueSet sous l'autorité racine du Togo."""
    clean_name = vs_name.strip().strip("/") if isinstance(vs_name, str) else ""
    if not clean_name:
        raise ValueError("Le nom de ValueSet ne peut pas être vide.")
    return f"{BASE_URI}/vs/{clean_name}"


def build_profile_uri(profile_name: str) -> str:
    """Construit une URI de StructureDefinition sous l'autorité racine du Togo."""
    clean_name = profile_name.strip().strip("/") if isinstance(profile_name, str) else ""
    if not clean_name:
        raise ValueError("Le nom de profil ne peut pas être vide.")
    return f"{BASE_URI}/StructureDefinition/{clean_name}"
