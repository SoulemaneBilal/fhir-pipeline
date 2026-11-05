"""Tests unitaires pour l'architecture des URIs canoniques et des espaces de noms FHIR Togo.

Vérifie la conformité des constantes, énumérations, registres et fonctions d'utilité
définis dans src/terminology/uris.py avec la spécification normative et les contrats d'interface.
"""

from __future__ import annotations

import pytest

from src.terminology.uris import (
    ALL_CANONICAL_URIS,
    BASE_URI,
    LOCAL_CODESYSTEM_REGISTRY,
    NAMING_SYSTEM_REGISTRY,
    STANDARD_SYSTEM_REGISTRY,
    URI_ATC,
    URI_CS_AGE_PRECISION,
    URI_CS_FACILITY_CATEGORY,
    URI_CS_HEALTH_DISTRICT,
    URI_CS_HEALTH_REGION,
    URI_CS_LOCAL_TERMS,
    URI_CS_PEV_VACCINES,
    URI_CS_PRIORITY_PATHOLOGY,
    URI_DISTRICT,
    URI_ENCOUNTER,
    URI_EXT_DISTRICT_REF,
    URI_EXT_ESTIMATED_AGE,
    URI_FACILITY,
    URI_ICD10,
    URI_LOINC,
    URI_PATIENT_LOCAL,
    URI_PATIENT_MPI,
    URI_PATIENT_NNI,
    URI_PRACTITIONER,
    URI_PROFILE_CONDITION,
    URI_PROFILE_ENCOUNTER,
    URI_PROFILE_IMMUNIZATION,
    URI_PROFILE_LOCATION,
    URI_PROFILE_MEDICATION_REQUEST,
    URI_PROFILE_OBSERVATION,
    URI_PROFILE_ORGANIZATION,
    URI_PROFILE_PATIENT,
    URI_PROFILE_PROCEDURE,
    URI_REGION,
    URI_SNOMED_CT,
    URI_UCUM,
    URI_VS_FACILITY_CATEGORY,
    URI_VS_HEALTH_DISTRICT,
    URI_VS_HEALTH_REGION,
    URI_VS_PEV_VACCINES,
    URI_VS_PRIORITY_PATHOLOGY,
    IdentifierSystem,
    LocalCodeSystem,
    LocalValueSet,
    StandardSystem,
    TogoProfile,
    build_cs_uri,
    build_profile_uri,
    build_sid_uri,
    build_vs_uri,
    get_code_system,
    get_identifier_system,
    get_profile_uri,
    get_standard_system,
    is_canonical_uri,
    is_togo_authority_uri,
    validate_canonical_uri,
)


class TestCanonicalUriConstants:
    """Vérification des constantes d'URIs requises par les contrats d'interface."""

    def test_base_authority_uri(self) -> None:
        """L'autorité racine nationale doit pointer vers le domaine officiel togolais."""
        assert BASE_URI == "http://interop-sante.gouv.tg/fhir"

    def test_identifier_system_constants(self) -> None:
        """Tous les identifiants NamingSystems (SIDs) doivent dériver de BASE_URI/sid/."""
        expected_sids = {
            URI_PATIENT_MPI: "http://interop-sante.gouv.tg/fhir/sid/patient-mpi",
            URI_PATIENT_NNI: "http://interop-sante.gouv.tg/fhir/sid/nni",
            URI_PATIENT_LOCAL: "http://interop-sante.gouv.tg/fhir/sid/patient-local",
            URI_FACILITY: "http://interop-sante.gouv.tg/fhir/sid/facility",
            URI_DISTRICT: "http://interop-sante.gouv.tg/fhir/sid/district",
            URI_REGION: "http://interop-sante.gouv.tg/fhir/sid/region",
            URI_ENCOUNTER: "http://interop-sante.gouv.tg/fhir/sid/encounter",
            URI_PRACTITIONER: "http://interop-sante.gouv.tg/fhir/sid/practitioner",
        }
        for actual, expected in expected_sids.items():
            assert actual == expected
            assert actual.startswith(f"{BASE_URI}/sid/")

    def test_local_codesystem_constants(self) -> None:
        """Tous les CodeSystems locaux doivent dériver de BASE_URI/cs/."""
        expected_cs = {
            URI_CS_FACILITY_CATEGORY: "http://interop-sante.gouv.tg/fhir/cs/facility-category",
            URI_CS_HEALTH_REGION: "http://interop-sante.gouv.tg/fhir/cs/health-region",
            URI_CS_HEALTH_DISTRICT: "http://interop-sante.gouv.tg/fhir/cs/health-district",
            URI_CS_PRIORITY_PATHOLOGY: "http://interop-sante.gouv.tg/fhir/cs/priority-pathology",
            URI_CS_PEV_VACCINES: "http://interop-sante.gouv.tg/fhir/cs/pev-vaccines",
            URI_CS_LOCAL_TERMS: "http://interop-sante.gouv.tg/fhir/cs/local-clinical-terms",
            URI_CS_AGE_PRECISION: "http://interop-sante.gouv.tg/fhir/cs/age-precision",
        }
        for actual, expected in expected_cs.items():
            assert actual == expected
            assert actual.startswith(f"{BASE_URI}/cs/")

    def test_local_valueset_constants(self) -> None:
        """Tous les ValueSets locaux doivent dériver de BASE_URI/vs/."""
        expected_vs = {
            URI_VS_FACILITY_CATEGORY: "http://interop-sante.gouv.tg/fhir/vs/facility-category",
            URI_VS_HEALTH_REGION: "http://interop-sante.gouv.tg/fhir/vs/health-region",
            URI_VS_HEALTH_DISTRICT: "http://interop-sante.gouv.tg/fhir/vs/health-district",
            URI_VS_PRIORITY_PATHOLOGY: "http://interop-sante.gouv.tg/fhir/vs/priority-pathology",
            URI_VS_PEV_VACCINES: "http://interop-sante.gouv.tg/fhir/vs/pev-vaccines",
        }
        for actual, expected in expected_vs.items():
            assert actual == expected
            assert actual.startswith(f"{BASE_URI}/vs/")

    def test_structure_definition_constants(self) -> None:
        """Les profils StructureDefinition et extensions doivent dériver de BASE_URI/StructureDefinition/."""
        profiles = [
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
        ]
        for p in profiles:
            assert p.startswith(f"{BASE_URI}/StructureDefinition/")

    def test_standard_international_system_constants(self) -> None:
        """Les terminologies mondiales standards doivent concorder avec les spécifications HL7/WHO."""
        assert URI_ICD10 == "http://hl7.org/fhir/sid/icd-10"
        assert URI_SNOMED_CT == "http://snomed.info/sct"
        assert URI_LOINC == "http://loinc.org"
        assert URI_ATC == "http://www.whocc.no/atc"
        assert URI_UCUM == "http://unitsofmeasure.org"


class TestTypedEnums:
    """Vérification des énumérations normalisées StrEnum."""

    def test_identifier_system_enum(self) -> None:
        """IdentifierSystem doit exposer tous les SIDs et être utilisable comme chaîne."""
        assert IdentifierSystem.PATIENT_MPI == URI_PATIENT_MPI
        assert IdentifierSystem.PATIENT_NNI == URI_PATIENT_NNI
        assert IdentifierSystem.PATIENT_LOCAL == URI_PATIENT_LOCAL
        assert IdentifierSystem.FACILITY == URI_FACILITY
        assert IdentifierSystem.DISTRICT == URI_DISTRICT
        assert IdentifierSystem.REGION == URI_REGION
        assert IdentifierSystem.ENCOUNTER == URI_ENCOUNTER
        assert IdentifierSystem.PRACTITIONER == URI_PRACTITIONER
        # StrEnum compatibility
        assert isinstance(IdentifierSystem.PATIENT_MPI, str)
        assert IdentifierSystem.PATIENT_MPI.startswith("http")

    def test_local_codesystem_enum(self) -> None:
        """LocalCodeSystem doit exposer les CodeSystems nationaux."""
        assert LocalCodeSystem.FACILITY_CATEGORY == URI_CS_FACILITY_CATEGORY
        assert LocalCodeSystem.HEALTH_REGION == URI_CS_HEALTH_REGION
        assert LocalCodeSystem.HEALTH_DISTRICT == URI_CS_HEALTH_DISTRICT
        assert LocalCodeSystem.PRIORITY_PATHOLOGY == URI_CS_PRIORITY_PATHOLOGY
        assert LocalCodeSystem.PEV_VACCINES == URI_CS_PEV_VACCINES
        assert LocalCodeSystem.LOCAL_TERMS == URI_CS_LOCAL_TERMS
        assert LocalCodeSystem.AGE_PRECISION == URI_CS_AGE_PRECISION

    def test_local_valueset_enum(self) -> None:
        """LocalValueSet doit exposer les ValueSets nationaux."""
        assert LocalValueSet.FACILITY_CATEGORY == URI_VS_FACILITY_CATEGORY
        assert LocalValueSet.HEALTH_REGION == URI_VS_HEALTH_REGION
        assert LocalValueSet.HEALTH_DISTRICT == URI_VS_HEALTH_DISTRICT
        assert LocalValueSet.PRIORITY_PATHOLOGY == URI_VS_PRIORITY_PATHOLOGY
        assert LocalValueSet.PEV_VACCINES == URI_VS_PEV_VACCINES

    def test_togo_profile_enum(self) -> None:
        """TogoProfile doit exposer les profils StructureDefinition majeurs."""
        assert TogoProfile.PATIENT == URI_PROFILE_PATIENT
        assert TogoProfile.ENCOUNTER == URI_PROFILE_ENCOUNTER
        assert TogoProfile.CONDITION == URI_PROFILE_CONDITION
        assert TogoProfile.OBSERVATION == URI_PROFILE_OBSERVATION
        assert TogoProfile.PROCEDURE == URI_PROFILE_PROCEDURE
        assert TogoProfile.MEDICATION_REQUEST == URI_PROFILE_MEDICATION_REQUEST
        assert TogoProfile.IMMUNIZATION == URI_PROFILE_IMMUNIZATION
        assert TogoProfile.ORGANIZATION == URI_PROFILE_ORGANIZATION
        assert TogoProfile.LOCATION == URI_PROFILE_LOCATION

    def test_standard_system_enum(self) -> None:
        """StandardSystem doit exposer les 5 terminologies cibles."""
        assert StandardSystem.ICD10 == URI_ICD10
        assert StandardSystem.SNOMED_CT == URI_SNOMED_CT
        assert StandardSystem.LOINC == URI_LOINC
        assert StandardSystem.ATC == URI_ATC
        assert StandardSystem.UCUM == URI_UCUM


class TestRegistriesAndValidation:
    """Vérification des registres de métadonnées et fonctions de contrôle."""

    def test_all_canonical_uris_completeness(self) -> None:
        """L'ensemble ALL_CANONICAL_URIS doit contenir toutes les URIs définies sans chaîne vide."""
        assert len(ALL_CANONICAL_URIS) >= 30
        for uri in ALL_CANONICAL_URIS:
            assert isinstance(uri, str)
            assert uri.startswith("http://") or uri.startswith("https://")
            assert len(uri) > 10

    def test_registries_structure(self) -> None:
        """Les registres de métadonnées doivent contenir des dictionnaires conformes."""
        assert len(NAMING_SYSTEM_REGISTRY) >= 8
        for entry in NAMING_SYSTEM_REGISTRY.values():
            assert "uri" in entry and "name" in entry and "type" in entry
            assert entry["uri"] in ALL_CANONICAL_URIS

        assert len(LOCAL_CODESYSTEM_REGISTRY) >= 7
        for entry in LOCAL_CODESYSTEM_REGISTRY.values():
            assert "uri" in entry and "name" in entry
            assert entry["uri"] in ALL_CANONICAL_URIS

        assert len(STANDARD_SYSTEM_REGISTRY) >= 5
        for entry in STANDARD_SYSTEM_REGISTRY.values():
            assert "uri" in entry and "authority" in entry
            assert entry["uri"] in ALL_CANONICAL_URIS

    def test_is_canonical_uri(self) -> None:
        """is_canonical_uri doit identifier avec précision les URIs supportées."""
        assert is_canonical_uri(URI_PATIENT_MPI) is True
        assert is_canonical_uri(URI_ICD10) is True
        assert is_canonical_uri(URI_CS_PRIORITY_PATHOLOGY) is True
        assert is_canonical_uri("http://inconnu.example.org/fhir") is False
        assert is_canonical_uri("") is False
        assert is_canonical_uri(None) is False  # type: ignore[arg-type]
        assert is_canonical_uri(["list"]) is False  # type: ignore[arg-type]
        assert is_canonical_uri(123) is False  # type: ignore[arg-type]
        assert is_canonical_uri({"key": "val"}) is False  # type: ignore[arg-type]

    def test_is_togo_authority_uri(self) -> None:
        """is_togo_authority_uri doit discerner les URIs nationales des systèmes externes."""
        assert is_togo_authority_uri(BASE_URI) is True
        assert is_togo_authority_uri(URI_PATIENT_MPI) is True
        assert is_togo_authority_uri(URI_CS_FACILITY_CATEGORY) is True
        assert is_togo_authority_uri(URI_PROFILE_PATIENT) is True
        assert is_togo_authority_uri(URI_ICD10) is False
        assert is_togo_authority_uri(URI_LOINC) is False
        assert is_togo_authority_uri("https://google.com") is False
        assert is_togo_authority_uri("http://interop-sante.gouv.tg/fhir-evil.com") is False
        assert is_togo_authority_uri("http://interop-sante.gouv.tg/fhir_suffix") is False
        assert is_togo_authority_uri(None) is False  # type: ignore[arg-type]
        assert is_togo_authority_uri(123) is False  # type: ignore[arg-type]
        assert is_togo_authority_uri(["list"]) is False  # type: ignore[arg-type]

    def test_validate_canonical_uri(self) -> None:
        """validate_canonical_uri doit valider toutes les constantes exportées."""
        assert validate_canonical_uri(URI_FACILITY) is True
        assert validate_canonical_uri(URI_SNOMED_CT) is True
        assert validate_canonical_uri("invalid-uri") is False


class TestHelperFunctions:
    """Vérification des fonctions utilitaires de résolution et de construction."""

    def test_get_identifier_system_resolution(self) -> None:
        """get_identifier_system doit résoudre les alias courants avec insensibilité à la casse."""
        assert get_identifier_system("mpi") == URI_PATIENT_MPI
        assert get_identifier_system("PATIENT_MPI") == URI_PATIENT_MPI
        assert get_identifier_system("nni") == URI_PATIENT_NNI
        assert get_identifier_system("cni") == URI_PATIENT_NNI
        assert get_identifier_system("local") == URI_PATIENT_LOCAL
        assert get_identifier_system("ipp") == URI_PATIENT_LOCAL
        assert get_identifier_system("facility") == URI_FACILITY
        assert get_identifier_system("fosa") == URI_FACILITY
        assert get_identifier_system("district") == URI_DISTRICT
        assert get_identifier_system("region") == URI_REGION
        assert get_identifier_system("encounter") == URI_ENCOUNTER
        assert get_identifier_system("sejour") == URI_ENCOUNTER
        assert get_identifier_system("practitioner") == URI_PRACTITIONER
        assert get_identifier_system("medecin") == URI_PRACTITIONER

    def test_get_identifier_system_invalid_raises_key_error(self) -> None:
        """get_identifier_system doit lever KeyError pour tout identifiant inconnu."""
        with pytest.raises(KeyError) as exc_info:
            get_identifier_system("unknown-sid")
        assert "Système d'identifiant inconnu" in str(exc_info.value)

    def test_get_code_system_resolution(self) -> None:
        """get_code_system doit résoudre les alias de CodeSystems locaux."""
        assert get_code_system("facility-category") == URI_CS_FACILITY_CATEGORY
        assert get_code_system("category") == URI_CS_FACILITY_CATEGORY
        assert get_code_system("region") == URI_CS_HEALTH_REGION
        assert get_code_system("district") == URI_CS_HEALTH_DISTRICT
        assert get_code_system("priority-pathology") == URI_CS_PRIORITY_PATHOLOGY
        assert get_code_system("pathology") == URI_CS_PRIORITY_PATHOLOGY
        assert get_code_system("pev") == URI_CS_PEV_VACCINES
        assert get_code_system("local-terms") == URI_CS_LOCAL_TERMS
        assert get_code_system("age-precision") == URI_CS_AGE_PRECISION

    def test_get_code_system_invalid_raises_key_error(self) -> None:
        """get_code_system doit lever KeyError pour tout CodeSystem inconnu."""
        with pytest.raises(KeyError) as exc_info:
            get_code_system("invalid-cs")
        assert "CodeSystem local inconnu" in str(exc_info.value)

    def test_get_standard_system_resolution(self) -> None:
        """get_standard_system doit résoudre les alias des terminologies mondiales."""
        assert get_standard_system("icd10") == URI_ICD10
        assert get_standard_system("cim-10") == URI_ICD10
        assert get_standard_system("snomed") == URI_SNOMED_CT
        assert get_standard_system("snomed-ct") == URI_SNOMED_CT
        assert get_standard_system("loinc") == URI_LOINC
        assert get_standard_system("atc") == URI_ATC
        assert get_standard_system("ucum") == URI_UCUM

    def test_get_standard_system_invalid_raises_key_error(self) -> None:
        """get_standard_system doit lever KeyError pour un système inconnu."""
        with pytest.raises(KeyError) as exc_info:
            get_standard_system("cpt")
        assert "Système international inconnu" in str(exc_info.value)

    def test_get_profile_uri_resolution(self) -> None:
        """get_profile_uri doit associer chaque nom de ressource à son profil Togo."""
        assert get_profile_uri("Patient") == URI_PROFILE_PATIENT
        assert get_profile_uri("togo-patient") == URI_PROFILE_PATIENT
        assert get_profile_uri("Encounter") == URI_PROFILE_ENCOUNTER
        assert get_profile_uri("Condition") == URI_PROFILE_CONDITION
        assert get_profile_uri("Observation") == URI_PROFILE_OBSERVATION
        assert get_profile_uri("Procedure") == URI_PROFILE_PROCEDURE
        assert get_profile_uri("MedicationRequest") == URI_PROFILE_MEDICATION_REQUEST
        assert get_profile_uri("Immunization") == URI_PROFILE_IMMUNIZATION
        assert get_profile_uri("Organization") == URI_PROFILE_ORGANIZATION
        assert get_profile_uri("Location") == URI_PROFILE_LOCATION

    def test_get_profile_uri_invalid_raises_key_error(self) -> None:
        """get_profile_uri doit lever KeyError pour une ressource non profilée."""
        with pytest.raises(KeyError) as exc_info:
            get_profile_uri("Binary")
        assert "Profil Togo inconnu" in str(exc_info.value)

    def test_builders(self) -> None:
        """Les fonctions de construction d'URIs doivent nettoyer les slashes et concaténer proprement."""
        assert build_sid_uri("custom-id") == f"{BASE_URI}/sid/custom-id"
        assert build_sid_uri("/custom-id/") == f"{BASE_URI}/sid/custom-id"
        assert build_cs_uri("custom-cs") == f"{BASE_URI}/cs/custom-cs"
        assert build_vs_uri("custom-vs") == f"{BASE_URI}/vs/custom-vs"
        assert build_profile_uri("custom-prof") == f"{BASE_URI}/StructureDefinition/custom-prof"

    @pytest.mark.parametrize(
        ("builder", "label"),
        [
            (build_sid_uri, "SID"),
            (build_cs_uri, "CodeSystem"),
            (build_vs_uri, "ValueSet"),
            (build_profile_uri, "profil"),
        ],
    )
    @pytest.mark.parametrize("invalid_input", ["", "   ", "///", None, 123])
    def test_builders_reject_empty_or_invalid_inputs(
        self, builder: object, label: str, invalid_input: object
    ) -> None:
        """Les constructeurs d'URI doivent lever ValueError sur les entrées vides ou invalides."""
        with pytest.raises(ValueError, match=f"Le nom de {label} ne peut pas être vide."):
            builder(invalid_input)  # type: ignore[operator]


class TestHardeningRegression:
    """Tests de non-régression issus des audits adversariaux (challenger_m1_1)."""

    def test_spoofed_domain_rejection(self) -> None:
        """is_togo_authority_uri doit rejeter tout domaine spoofé comme fhir-evil.com."""
        assert is_togo_authority_uri("http://interop-sante.gouv.tg/fhir-evil.com") is False
        assert is_togo_authority_uri("http://interop-sante.gouv.tg/fhir.attacker.org") is False
        assert is_togo_authority_uri("http://interop-sante.gouv.tg/fhir_malicious") is False

    def test_non_string_inputs_handled_safely(self) -> None:
        """Les prédicats d'URI ne doivent jamais crasher sur des entrées non-chaînes."""
        assert is_togo_authority_uri(None) is False  # type: ignore[arg-type]
        assert is_togo_authority_uri(12345) is False  # type: ignore[arg-type]
        assert is_togo_authority_uri(["http://interop-sante.gouv.tg/fhir"]) is False  # type: ignore[arg-type]

        assert is_canonical_uri(None) is False  # type: ignore[arg-type]
        assert is_canonical_uri(12345) is False  # type: ignore[arg-type]
        assert is_canonical_uri(["list"]) is False  # type: ignore[arg-type]
        assert is_canonical_uri({"uri": BASE_URI}) is False  # type: ignore[arg-type]

        assert validate_canonical_uri(None) is False  # type: ignore[arg-type]
        assert validate_canonical_uri(["list"]) is False  # type: ignore[arg-type]

    def test_empty_builder_inputs_raise_value_error(self) -> None:
        """Les constructeurs d'URI doivent refuser les noms vides ou composés d'espaces."""
        with pytest.raises(ValueError, match="Le nom de SID ne peut pas être vide."):
            build_sid_uri("")
        with pytest.raises(ValueError, match="Le nom de SID ne peut pas être vide."):
            build_sid_uri("   ")
        with pytest.raises(ValueError, match="Le nom de CodeSystem ne peut pas être vide."):
            build_cs_uri("")
        with pytest.raises(ValueError, match="Le nom de CodeSystem ne peut pas être vide."):
            build_cs_uri("   ")
        with pytest.raises(ValueError, match="Le nom de ValueSet ne peut pas être vide."):
            build_vs_uri("")
        with pytest.raises(ValueError, match="Le nom de ValueSet ne peut pas être vide."):
            build_vs_uri("   ")
        with pytest.raises(ValueError, match="Le nom de profil ne peut pas être vide."):
            build_profile_uri("")
        with pytest.raises(ValueError, match="Le nom de profil ne peut pas être vide."):
            build_profile_uri("   ")
