"""Générateur contextuel de Vérité Terrain (Ground Truth) pour le Togo (Étape 3).

Ce module orchestre la synthèse algorithmique d'une cohorte clinique togolaise complète,
déterministe et réaliste (Voie B contextuelle, ADR D-04) produisant 6 tables Parquet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from src.generation.clinical_rules import ClinicalRulesEngine
from src.generation.demographics import DemographicGenerator
from src.generation.schemas import (
    CONDITION_SCHEMA,
    ENCOUNTER_SCHEMA,
    IMMUNIZATION_SCHEMA,
    OBSERVATION_SCHEMA,
    PATIENT_SCHEMA,
    PRESCRIPTION_SCHEMA,
    create_pyarrow_table,
)


def generate_ground_truth(
    count: int = 1000,
    seed: int = 42,
    output_dir: Path | str = Path("data/truth"),
) -> dict[str, Path]:
    """Génère une cohorte clinique synthétique togolaise complète en format Parquet.

    Args:
        count: Nombre de dossiers patients à synthétiser (doit être > 0).
        seed: Graine pseudo-aléatoire pour garantir un déterminisme bit-à-bit strict.
        output_dir: Dossier de destination pour l'écriture des 6 tables Parquet.

    Returns:
        Dictionnaire associant chaque table clinique à son chemin de fichier Parquet.

    Raises:
        ValueError: Si count <= 0.
    """
    if count <= 0:
        raise ValueError(f"Le paramètre 'count' doit être strictement positif (reçu: {count})")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    demo_engine = DemographicGenerator(seed=seed)
    clinical_engine = ClinicalRulesEngine(seed=seed)

    all_patients: list[dict[str, Any]] = []
    all_encounters: list[dict[str, Any]] = []
    all_conditions: list[dict[str, Any]] = []
    all_observations: list[dict[str, Any]] = []
    all_prescriptions: list[dict[str, Any]] = []
    all_immunizations: list[dict[str, Any]] = []

    for idx in range(1, count + 1):
        patient_raw = demo_engine.sample_identity(index=idx)
        # Extraction de la métadonnée interne d'âge avant validation de schéma
        clinical_data = clinical_engine.generate_clinical_events_for_patient(
            patient=patient_raw,
            patient_idx=idx,
        )

        patient_clean = {k: v for k, v in patient_raw.items() if not k.startswith("_")}
        all_patients.append(patient_clean)

        all_encounters.extend(clinical_data["encounters"])
        all_conditions.extend(clinical_data["conditions"])
        all_observations.extend(clinical_data["observations"])
        all_prescriptions.extend(clinical_data["prescriptions"])
        all_immunizations.extend(clinical_data["immunizations"])

    # Tri déterministe lexicographique garantissant l'idempotence et la reproductibilité bit-à-bit
    all_patients.sort(key=lambda x: str(x["patient_id"]))
    all_encounters.sort(
        key=lambda x: (str(x["patient_id"]), str(x["start_date"]), str(x["encounter_id"]))
    )
    all_conditions.sort(
        key=lambda x: (str(x["patient_id"]), str(x["encounter_id"]), str(x["condition_id"]))
    )
    all_observations.sort(
        key=lambda x: (str(x["patient_id"]), str(x["encounter_id"]), str(x["observation_id"]))
    )
    all_prescriptions.sort(
        key=lambda x: (str(x["patient_id"]), str(x["encounter_id"]), str(x["prescription_id"]))
    )
    all_immunizations.sort(
        key=lambda x: (str(x["patient_id"]), str(x["occurrence_date"]), str(x["immunization_id"]))
    )

    # Conversion en tables PyArrow avec schémas stricts
    patients_table = create_pyarrow_table(all_patients, PATIENT_SCHEMA)
    encounters_table = create_pyarrow_table(all_encounters, ENCOUNTER_SCHEMA)
    conditions_table = create_pyarrow_table(all_conditions, CONDITION_SCHEMA)
    observations_table = create_pyarrow_table(all_observations, OBSERVATION_SCHEMA)
    prescriptions_table = create_pyarrow_table(all_prescriptions, PRESCRIPTION_SCHEMA)
    immunizations_table = create_pyarrow_table(all_immunizations, IMMUNIZATION_SCHEMA)

    # Chemins de destination
    patients_path = out_path / "patients.parquet"
    encounters_path = out_path / "encounters.parquet"
    conditions_path = out_path / "conditions.parquet"
    observations_path = out_path / "observations.parquet"
    prescriptions_path = out_path / "prescriptions.parquet"
    immunizations_path = out_path / "immunizations.parquet"

    # Sérialisation Parquet standardisée (compression SNAPPY)
    pq.write_table(patients_table, patients_path, compression="SNAPPY")
    pq.write_table(encounters_table, encounters_path, compression="SNAPPY")
    pq.write_table(conditions_table, conditions_path, compression="SNAPPY")
    pq.write_table(observations_table, observations_path, compression="SNAPPY")
    pq.write_table(prescriptions_table, prescriptions_path, compression="SNAPPY")
    pq.write_table(immunizations_table, immunizations_path, compression="SNAPPY")

    return {
        "patients": patients_path,
        "encounters": encounters_path,
        "conditions": conditions_path,
        "observations": observations_path,
        "prescriptions": prescriptions_path,
        "medications": prescriptions_path,  # Alias
        "immunizations": immunizations_path,
    }
