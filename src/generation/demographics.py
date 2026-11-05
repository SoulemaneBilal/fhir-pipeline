"""Moteur démographique et onomastique contextuel pour le Togo (Étape 3).

Ce module génère des identités togolaises authentiques (patronymes, prénoms coutumiers,
pyramide des âges RGPH-5, âges approximatifs VAL-003, rattachement aux 44 districts sanitaires).
"""

from __future__ import annotations

import random
import uuid
from typing import Any

from src.terminology.geography import load_health_geography

# Espace de noms UUID v5 immuable pour les patients
NAMESPACE_TOGO_BASE = uuid.uuid5(uuid.NAMESPACE_DNS, "interop-sante.gouv.tg")
NAMESPACE_TOGO_PATIENT = uuid.uuid5(NAMESPACE_TOGO_BASE, "patient")

# ==============================================================================
# 1. Onomastique Togolaise Authentique
# ==============================================================================

# Patronymes du Sud (Éwé, Mina, Ouatchi - Grand Lomé, Maritime, Plateaux)
SURNAMES_SOUTH: list[str] = [
    "Mensah",
    "Koffi",
    "Akakpo",
    "Ayité",
    "Amouzou",
    "Lawson",
    "Olympio",
    "d'Almeida",
    "Foli",
    "Dosseh",
    "Adanlete",
    "Adjété",
    "Dogbé",
    "Gbeho",
    "Agbodjan",
    "Kuevi",
    "Seddoh",
    "Kpogo",
    "Houenou",
    "Aklassato",
    "Sanvee",
    "Quashie",
    "Agbovon",
    "Dzokoto",
    "Hounkpatin",
    "Kodjovi",
    "Ananou",
    "Gado",
    "Ekue",
    "Mawussi",
    "Dossou",
    "Agbo",
    "Kpodar",
    "Agbeko",
    "Aziable",
]

# Patronymes du Nord et Centre (Kabiyè, Tem/Kotokoli, Moba, Bassar, Losso - Kara, Savanes, Centrale)
SURNAMES_NORTH: list[str] = [
    "Gnassingbé",
    "Tchalla",
    "Bataka",
    "Kpatcha",
    "Esso",
    "Piyabalo",
    "Tchakondo",
    "Koriko",
    "Ouro-Gnao",
    "Traoré",
    "Alassani",
    "Dermane",
    "Yentchabre",
    "Kombaté",
    "Kolani",
    "Damigou",
    "Sambiani",
    "Bawa",
    "N'Sougan",
    "Tchamie",
    "Boukari",
    "Tchedre",
    "Agoro",
    "Salami",
    "Kankpe",
    "Tassane",
    "Akondo",
    "N'Gani",
    "Djato",
    "Mouzou",
    "Palanga",
    "Walla",
    "Padaro",
]

# Prénoms masculins du Sud (coutumiers des jours de la semaine et modernes)
GIVEN_NAMES_MALE_SOUTH: list[str] = [
    "Kodjo",  # Lundi
    "Komla",  # Mardi
    "Kokou",  # Mercredi
    "Yao",  # Jeudi
    "Koffi",  # Vendredi
    "Komi",  # Samedi
    "Kossi",  # Dimanche
    "Mawuko",
    "Sena",
    "Elom",
    "Edoh",
    "Dela",
    "Senyo",
    "Eyram",
    "Folly",
    "Atsu",
    "Etse",
    "Messan",
    "Wolanyo",
    "Dzifa",
    "Dodji",
    "Sylvanus",
]

# Prénoms féminins du Sud
GIVEN_NAMES_FEMALE_SOUTH: list[str] = [
    "Adjo",  # Lundi
    "Abla",  # Mardi
    "Akou",  # Mercredi
    "Yawa",  # Jeudi
    "Afi",  # Vendredi
    "Afiavi",
    "Bayi",  # Samedi
    "Esi",  # Dimanche
    "Kossiwa",
    "Mawusi",
    "Kafui",
    "Dédé",
    "Mansa",
    "Ahoefa",
    "Essenam",
    "Abra",
    "Akuvi",
    "Kayi",
    "Fafa",
    "Enam",
    "Senam",
    "Sitsofe",
    "Yram",
]

# Prénoms masculins du Nord et Centre
GIVEN_NAMES_MALE_NORTH: list[str] = [
    "Essodina",
    "Piyabalo",
    "Toyi",
    "Tchao",
    "Mazamesso",
    "Alaza",
    "Kondi",
    "Issifou",
    "Salifou",
    "Yentemma",
    "Kombate",
    "Douti",
    "Lalle",
    "Bakary",
    "Sadikou",
    "Esso-Wavana",
    "Tarek",
    "Moubarak",
    "Bassirou",
    "Harouna",
    "Inoussa",
]

# Prénoms féminins du Nord et Centre
GIVEN_NAMES_FEMALE_NORTH: list[str] = [
    "Hodalo",
    "Pyalo",
    "Mazalo",
    "Toyi",
    "Essohanam",
    "Somié",
    "Gnamba",
    "Zalika",
    "Mariama",
    "Amina",
    "Fati",
    "Alima",
    "Balkissa",
    "Yendoubé",
    "Assana",
    "Halima",
    "Maimouna",
    "Safiatou",
    "Rachida",
    "Zeinabou",
    "Nadège",
]

# Groupes ethno-linguistiques associés aux régions
ETHNIC_GROUPS_BY_REGION: dict[str, list[tuple[str, float]]] = {
    "TG-LOM": [("Ewe", 0.45), ("Mina", 0.30), ("Kabiye", 0.15), ("Tem", 0.10)],
    "TG-MAR": [("Ewe", 0.50), ("Mina", 0.35), ("Ouatchi", 0.15)],
    "TG-PLA": [("Ewe", 0.55), ("Ana-Ife", 0.20), ("Kabiye", 0.15), ("Akebou", 0.10)],
    "TG-CEN": [("Tem", 0.55), ("Kabiye", 0.25), ("Bassari", 0.10), ("Peul", 0.10)],
    "TG-KAR": [("Kabiye", 0.65), ("Losso", 0.15), ("Lamba", 0.10), ("Bassar", 0.10)],
    "TG-SAV": [("Moba", 0.50), ("Gourma", 0.25), ("Mossis", 0.15), ("Peul", 0.10)],
}

# Indicatifs de téléphone togolais réalistes (Togocom 90-93, Moov Africa 70-71)
TOGO_PHONE_PREFIXES: list[str] = ["90", "91", "92", "93", "70", "71"]


# ==============================================================================
# 2. Pyramide Démographique et Répartition Spatiale
# ==============================================================================

# Distribution par tranches d'âges au Togo (RGPH-5, âge médian ~19.5 ans)
AGE_BRACKETS: list[tuple[int, int, float]] = [
    (0, 4, 0.16),  # 16% Nourrissons et petite enfance
    (5, 14, 0.24),  # 24% Enfants d'âge scolaire
    (15, 24, 0.19),  # 19% Adolescents et jeunes adultes
    (25, 49, 0.28),  # 28% Adultes actifs / procréation
    (50, 64, 0.09),  # 9% Adultes mûrs
    (65, 85, 0.04),  # 4% Personnes âgées
]


class DemographicGenerator:
    """Générateur d'attributs démographiques pour la cohorte synthétique."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self._load_geography()

    def _load_geography(self) -> None:
        """Charge le référentiel territorial officiel du Togo."""
        geo_df = load_health_geography()
        # Dédoublonnage des 44 districts
        districts_df = geo_df[
            ["district_code", "district_name", "region_code", "region_name"]
        ].drop_duplicates()
        self.districts: list[dict[str, str]] = districts_df.to_dict(orient="records")

        # Poids démographiques approximatifs par région (Grand Lomé concentre ~25% de la pop)
        region_weights = {
            "TG-LOM": 3.0,
            "TG-MAR": 1.8,
            "TG-PLA": 1.7,
            "TG-SAV": 1.3,
            "TG-KAR": 1.2,
            "TG-CEN": 1.0,
        }
        self.district_weights: list[float] = [
            region_weights.get(d["region_code"], 1.0) for d in self.districts
        ]

    def sample_age(self) -> int:
        """Échantillonne un âge respectant la pyramide démographique togolaise."""
        bracket_weights = [weight for _, _, weight in AGE_BRACKETS]
        selected_bracket = self.rng.choices(AGE_BRACKETS, weights=bracket_weights, k=1)[0]
        min_age, max_age, _ = selected_bracket
        return self.rng.randint(min_age, max_age)

    def sample_district(self) -> dict[str, str]:
        """Sélectionne un district sanitaire parmi les 44 officiels."""
        return self.rng.choices(self.districts, weights=self.district_weights, k=1)[0]

    def sample_identity(
        self,
        index: int,
        reference_year: int = 2025,
    ) -> dict[str, Any]:
        """Génère un profil patient togolais complet et déterministe.

        Respecte formellement VAL-003 pour les âges approximatifs :
        - 1er juillet de l'année déduite (YYYY-07-01).
        - is_estimated_birth_date = True et estimated_age_flag = True.
        - age_precision = 'approximate-year'.
        """
        # Sexe biologique (ratio ~51% femmes, 49% hommes)
        gender = "female" if self.rng.random() < 0.51 else "male"

        # District et Région
        district_info = self.sample_district()
        region_code = district_info["region_code"]
        district_code = district_info["district_code"]
        district_name = district_info["district_name"]

        # Groupe ethnique
        ethnic_options = ETHNIC_GROUPS_BY_REGION.get(region_code, [("Ewe", 0.5), ("Kabiye", 0.5)])
        ethnic_group = self.rng.choices(
            [e[0] for e in ethnic_options],
            weights=[e[1] for e in ethnic_options],
            k=1,
        )[0]

        # Onomastique selon la région géographique
        is_northern = region_code in ("TG-KAR", "TG-SAV", "TG-CEN")
        if is_northern:
            # 85% de noms septentrionaux dans le Nord, 15% dans le Sud (migration)
            surname_pool = SURNAMES_NORTH if self.rng.random() < 0.85 else SURNAMES_SOUTH
            given_pool = (
                (GIVEN_NAMES_MALE_NORTH if gender == "male" else GIVEN_NAMES_FEMALE_NORTH)
                if self.rng.random() < 0.85
                else (GIVEN_NAMES_MALE_SOUTH if gender == "male" else GIVEN_NAMES_FEMALE_SOUTH)
            )
        else:
            # 80% de noms méridionaux dans le Sud
            surname_pool = SURNAMES_SOUTH if self.rng.random() < 0.80 else SURNAMES_NORTH
            given_pool = (
                (GIVEN_NAMES_MALE_SOUTH if gender == "male" else GIVEN_NAMES_FEMALE_SOUTH)
                if self.rng.random() < 0.80
                else (GIVEN_NAMES_MALE_NORTH if gender == "male" else GIVEN_NAMES_FEMALE_NORTH)
            )

        family_name = self.rng.choice(surname_pool)
        given_name = self.rng.choice(given_pool)

        # Âge et Date de Naissance
        age = self.sample_age()
        birth_year = reference_year - age

        # Règle VAL-003 pour les âges approximatifs
        # Pour les enfants (< 15 ans), état civil quasi-systématique (99%)
        # Pour les adultes 15-49 ans, ~15% d'âges estimés
        # Pour les seniors 50+ ans, ~50% d'âges estimés
        if age < 15:
            is_estimated = self.rng.random() < 0.01
        elif age < 50:
            is_estimated = self.rng.random() < 0.15
        else:
            is_estimated = self.rng.random() < 0.50

        if is_estimated:
            # Règle stricte VAL-003 : 1er juillet de l'année estimée
            birth_date = f"{birth_year:04d}-07-01"
            age_precision = "approximate-year"
        else:
            month = self.rng.randint(1, 12)
            day = self.rng.randint(1, 28)  # Sécurise tous les mois y compris février
            birth_date = f"{birth_year:04d}-{month:02d}-{day:02d}"
            age_precision = "exact"

        # Identifiants déterministes (UUID v5 et matricules)
        patient_id = str(uuid.uuid5(NAMESPACE_TOGO_PATIENT, f"seed={self.seed}:patient={index}"))
        identifier_system = "http://interop-sante.gouv.tg/fhir/sid/patient-mpi"
        identifier_value = f"TG-PAT-{index:07d}"

        gender_digit = 1 if gender == "male" else 2
        nni = f"TG-NNI-{abs(birth_year) % 100:02d}{gender_digit}{index:06d}"

        # Téléphone
        prefix = self.rng.choice(TOGO_PHONE_PREFIXES)
        d1 = self.rng.randint(10, 99)
        d2 = self.rng.randint(10, 99)
        d3 = self.rng.randint(10, 99)
        phone_number = f"+228 {prefix} {d1:02d} {d2:02d} {d3:02d}"

        # Statut matrimonial
        if age < 16:
            marital_status = "U"
        else:
            marital_status = self.rng.choices(
                ["U", "M", "D", "W"],
                weights=[0.30, 0.60, 0.05, 0.05],
                k=1,
            )[0]

        # Horodatage de création dans le système
        created_at = f"{reference_year}-01-10T08:00:00Z"

        return {
            "patient_id": patient_id,
            "identifier_system": identifier_system,
            "identifier_value": identifier_value,
            "nni": nni,
            "family_name": family_name,
            "given_name": given_name,
            "gender": gender,
            "birth_date": birth_date,
            "is_estimated_birth_date": is_estimated,
            "estimated_age_flag": is_estimated,
            "age_precision": age_precision,
            "phone_number": phone_number,
            "address_region_code": region_code,
            "address_district_code": district_code,
            "address_city": district_name,
            "residence_district_code": district_code,
            "residence_region_code": region_code,
            "marital_status": marital_status,
            "ethnic_group": ethnic_group,
            "created_at": created_at,
            "_age": age,  # Métadonnée interne utile pour la simulation clinique
        }
