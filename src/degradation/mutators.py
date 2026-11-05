"""Mutateurs unitaires pour l'altération contrôlée de données médicales et administratives.

Implémente l'ensemble des fonctions pures de dégradation sous PRNG isolé (seed),
respectant la tolérance aux types, aux valeurs manquantes et le déterminisme strict.
"""

from __future__ import annotations

import math
import random
import re
import unicodedata
from typing import Any

# ==============================================================================
# 1. Dates et Âges
# ==============================================================================


def mutate_date_format(val: Any, seed: int = 42) -> str | None:
    """Convertit une date ISO 8601 (YYYY-MM-DD) en format composite disparate."""
    if val is None or val == "":
        return val

    val_str = str(val).strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", val_str)
    if not match:
        return val_str

    year, month, day = match.group(1), match.group(2), match.group(3)
    rng = random.Random(seed)

    formats = [
        f"{day}/{month}/{year}",
        f"{day}-{month}-{year}",
        f"{year}/{month}/{day}",
        f"{day}.{month}.{year[-2:]}",
        f"{day}/{month}/{year[-2:]}",
        f"{day}{month}{year}",
    ]
    return rng.choice(formats)


def mutate_approximate_age(val: Any, seed: int = 42) -> str:
    """Remplace une date de naissance ou un âge numérique par un libellé textuel approximatif."""
    rng = random.Random(seed)
    age = 35

    if isinstance(val, (int, float)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            age = 35
        else:
            age = max(1, int(val))
    elif isinstance(val, str) and val.strip():
        match = re.match(r"^(\d{4})", val.strip())
        if match:
            birth_year = int(match.group(1))
            age = max(1, 2024 - birth_year)
        else:
            try:
                age = max(1, int(float(val)))
            except ValueError:
                age = 35

    templates = [
        f"environ {age} ans",
        f"~ {age} ans",
        f"env. {age} ans",
        f"{age} ans env.",
        f"vers {age} ans",
        f"né vers {2024 - age}",
    ]
    return rng.choice(templates)


# ==============================================================================
# 2. Patronymes et Identité
# ==============================================================================

TOGOLESE_NAME_VARIANTS: dict[str, list[str]] = {
    "Mensah": ["Mensa", "Menza", "Mensha"],
    "Lawson": ["Lauson", "Lawsson", "Lousson"],
    "Adjamagbo": ["Adjamagba", "Adjamabo", "Ajamagbo"],
    "Ametowobla": ["Ametowoba", "Ametowbla", "Ametoobla"],
    "Tchagbele": ["Tchagbélé", "Chagbele", "Tchagbele-Koffi"],
    "Koffi": ["Kofi", "Koffie", "Coffi"],
    "Kodjo": ["Kojo", "Kodzo", "Cojo"],
    "Ablavi": ["Abla", "Ablavy", "Ablawe"],
    "Afantchao": ["Afantcha", "Afanchao"],
    "Agbeve": ["Agbevey", "Agbévé"],
    "Akakpo": ["Akapo", "Akakpoh"],
    "Amegan": ["Amega", "Ameganvi"],
    "Ayeva": ["Ayéva", "Aieva"],
    "Dosseh": ["Dossè", "Doseh"],
    "Gbeassor": ["Gbéassor", "Gbeassor-T"],
}


def mutate_name_spelling(val: Any, seed: int = 42) -> str:
    """Introduit des coquilles typographiques ou variantes phonétiques togolaises réalistes."""
    if val is None or val == "":
        return "Inconnu"

    name_str = str(val).strip()
    rng = random.Random(seed)

    if name_str in TOGOLESE_NAME_VARIANTS:
        return rng.choice(TOGOLESE_NAME_VARIANTS[name_str])

    # Algorithme générique de mutation préservant la plausibilité
    if len(name_str) >= 4:
        idx = rng.randint(1, len(name_str) - 2)
        mode = rng.choice(["swap", "dup", "drop"])
        if mode == "swap":
            return name_str[:idx] + name_str[idx + 1] + name_str[idx] + name_str[idx + 2 :]
        elif mode == "dup":
            return name_str[:idx] + name_str[idx] + name_str[idx:]
        elif mode == "drop" and len(name_str) > 4:
            return name_str[:idx] + name_str[idx + 1 :]

    return f"{name_str}e"


def mutate_strip_accents(val: Any) -> str:
    """Supprime tous les accents et diacritiques d'une chaîne de caractères."""
    if val is None:
        return ""
    text = str(val)
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def mutate_invert_name_order(
    family_name: str, given_name: str | None = None, seed: int = 42
) -> str:
    """Inverse l'ordre nom / prénom pour simuler des inversions de saisie."""
    _ = seed
    if given_name is not None and given_name != "":
        return f"{given_name} {family_name}"

    if family_name and " " in family_name:
        parts = family_name.split()
        return " ".join(reversed(parts))

    return family_name


# ==============================================================================
# 3. Données Cliniques et Mesures
# ==============================================================================


def mutate_clinical_freetext(val: Any, seed: int = 42) -> str:
    """Transforme un diagnostic médical standard en libellé informel ou abréviation libre."""
    if val is None or val == "":
        return "palu simple"

    text = str(val).lower()
    rng = random.Random(seed)

    if "paludisme" in text or "palu" in text or "falciparum" in text:
        return rng.choice(["palu simple", "accès palustre", "palu grave", "susp. palu"])
    if "hypertension" in text or "hta" in text:
        return rng.choice(
            ["HTA stade 1", "hta essentielle", "tension artérielle", "crise de tension"]
        )
    if "gastro" in text or "diarrh" in text:
        return rng.choice(["GEA fébrile", "gastro aiguë", "syndrome de diarrhée", "diarrhée aiguë"])
    if "respiratoire" in text or "bronch" in text or "pneumo" in text:
        return rng.choice(["IRA haute", "infection respiratoire", "bronchite aiguë", "IRA fébrile"])
    if "tuberculose" in text:
        return rng.choice(["Susp. TB", "suspicion BK", "TB pulmonaire"])

    return f"{val} (forme libre)"


def mutate_measurement_separator(val: Any) -> str:
    """Remplace le séparateur décimal point par la virgule francophone."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return ""
    s = (f"{val:.1f}" if val.is_integer() else str(val)) if isinstance(val, float) else str(val)
    return s.replace(".", ",")


def mutate_measurement_unit(val: Any, seed: int = 42) -> str | None:
    """Altère ou omet l'unité de mesure standard UCUM."""
    rng = random.Random(seed)
    unit_str = str(val).strip() if val is not None else ""

    substitutions: dict[str, list[str | None]] = {
        "g/dL": ["g/l", "g/L", "mg/dL", "", None],
        "Cel": ["°C", "deg C", "C", "", None],
        "mg/dL": ["mg/l", "g/L", "", None],
        "mmol/L": ["mmol/l", "mg/L", "", None],
        "mm[Hg]": ["mmHg", "cmHg", "", None],
        "kg": ["kilos", "KG", "", None],
    }

    if unit_str in substitutions:
        return rng.choice(substitutions[unit_str])

    return rng.choice([None, "", f"{unit_str}_non_std"])


# ==============================================================================
# 4. Données Manquantes et Sentinelles
# ==============================================================================


def mutate_sentinel(val: Any = None, seed: int = 42) -> str:
    """Injecte une valeur sentinelle standard d'indétermination hospitalière."""
    _ = val
    rng = random.Random(seed)
    sentinels = ["-1", "999", "-999", "9999", "NA", "ND", "N/A", "INCONNU"]
    return rng.choice(sentinels)


def mutate_missing(val: Any = None) -> Any:
    """Supprime une valeur en la remplaçant par None pour simuler une omission."""
    _ = val
    return None


# ==============================================================================
# 5. Encodage et Formations Sanitaires
# ==============================================================================


def mutate_encoding_mojibake(val: Any, seed: int = 42) -> str:
    """Simule une altération d'encodage Mojibake (UTF-8 décodé en Latin-1)."""
    _ = seed
    if val is None or val == "":
        return ""

    text = str(val)
    try:
        corrupted = text.encode("utf-8").decode("latin-1")
        if corrupted != text:
            return corrupted
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Remplacement manuel des voyelles courantes si le texte est ASCII
    replacements = {"é": "Ã©", "è": "Ã¨", "ô": "Ã´", "à": "Ã ", "e": "Ã©", "o": "Ã´"}
    chars = list(text)
    for i, c in enumerate(chars):
        if c in replacements:
            chars[i] = replacements[c]
            break
    return "".join(chars)


def mutate_facility_name(val: Any, seed: int = 42) -> str:
    """Génère des variantes d'usage et sigles pour les formations sanitaires togolaises."""
    if val is None or val == "":
        return "CMS Adidogomé"

    text = str(val)
    rng = random.Random(seed)

    if "adidogom" in text.lower():
        return rng.choice(
            [
                "CMS Adidogomé",
                "CMS Adidogome",
                "Centre de Santé Adidogomé",
                "Adidogomé (CMS)",
            ]
        )
    if "tokoin" in text.lower():
        return rng.choice(["USP Tokoin", "CMS Tokoin Solidarité", "CHU Tokoin"])
    if "Centre Médico-Social" in text:
        return text.replace("Centre Médico-Social", "CMS")
    if "Unité de Soins Périphériques" in text:
        return text.replace("Unité de Soins Périphériques", "USP")
    if "Centre Hospitalier" in text:
        return text.replace("Centre Hospitalier", "CHR")

    return rng.choice([f"CMS {text}", f"{text} (Annexe)", f"Centre {text}"])
