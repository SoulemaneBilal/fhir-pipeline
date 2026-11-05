"""Moteur d'altération contrôlée et de stress-test du pipeline FHIR Togo.

Orchestre la dégradation paramétrée des 6 tables de Vérité Terrain :
- Respect rigoureux du taux cible (rate +/- 5%)
- Reproductibilité binaire bit-à-bit sous graine fixe (seed)
- Injection de doublons patients inter-établissements avec IDs distincts pour Splink
- Traçabilité intégrale et réversibilité absolue via alterations_log.parquet
"""

from __future__ import annotations

import random
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.degradation.catalog import DegradationCatalog, load_rules_catalog
from src.degradation.mutators import (
    mutate_approximate_age,
    mutate_clinical_freetext,
    mutate_date_format,
    mutate_encoding_mojibake,
    mutate_facility_name,
    mutate_invert_name_order,
    mutate_measurement_separator,
    mutate_measurement_unit,
    mutate_missing,
    mutate_name_spelling,
    mutate_sentinel,
    mutate_strip_accents,
)
from src.degradation.schemas import ALTERATION_LOG_SCHEMA, AlterationRecord, DegradationConfig

CLINICAL_TABLES = [
    "patients",
    "encounters",
    "conditions",
    "observations",
    "prescriptions",
    "immunizations",
]

PRIMARY_KEYS = {
    "patients": "patient_id",
    "encounters": "encounter_id",
    "conditions": "condition_id",
    "observations": "observation_id",
    "prescriptions": "prescription_id",
    "immunizations": "immunization_id",
}


class DegradationEngine:
    """Moteur central d'injection d'anomalies réalistes et traçabilité."""

    def __init__(
        self,
        rate: float = 0.15,
        seed: int = 42,
        rules_catalog: DegradationCatalog | None = None,
    ) -> None:
        if not (0.0 <= rate <= 1.0):
            raise ValueError(
                f"Le taux d'altération (rate) doit être compris entre 0.0 et 1.0, reçu : {rate}"
            )

        self.config = DegradationConfig(rate=rate, seed=seed)
        self.catalog = rules_catalog or load_rules_catalog()
        self.rate = rate
        self.seed = seed

    def run(
        self,
        source_dir: Path | str,
        output_dir: Path | str,
        rate: float | None = None,
        seed: int | None = None,
        export_formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Point d'entrée principal pour exécuter la dégradation."""
        eff_rate = self.rate if rate is None else rate
        eff_seed = self.seed if seed is None else seed
        return apply_degradation(
            source_dir=source_dir,
            output_dir=output_dir,
            rate=eff_rate,
            seed=eff_seed,
            rules_catalog=self.catalog,
            export_formats=export_formats,
        )

    def degrade_dataset(
        self,
        source_dir: Path | str,
        output_dir: Path | str,
        rate: float | None = None,
        seed: int | None = None,
        export_formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Alias pour run."""
        return self.run(
            source_dir=source_dir,
            output_dir=output_dir,
            rate=rate,
            seed=seed,
            export_formats=export_formats,
        )


def apply_degradation(
    source_dir: Path | str,
    output_dir: Path | str,
    rate: float = 0.15,
    seed: int = 42,
    rules_catalog: DegradationCatalog | None = None,
    export_formats: list[str] | None = None,
) -> dict[str, Any]:
    """Exécute l'injection d'erreurs contrôlées sur les 6 tables de vérité terrain."""
    if not (0.0 <= rate <= 1.0):
        raise ValueError(
            f"Le taux d'altération (rate) doit être compris entre 0.0 et 1.0, reçu : {rate}"
        )

    _ = rules_catalog
    _ = export_formats

    src_path = Path(source_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Chargement déterministe des tables sources
    tables: dict[str, pd.DataFrame] = {}
    for table_name in CLINICAL_TABLES:
        table_file = src_path / f"{table_name}.parquet"
        if not table_file.exists():
            raise FileNotFoundError(f"Table source obligatoire introuvable : {table_file}")
        tables[table_name] = pd.read_parquet(table_file)

    rng = random.Random(seed)
    alterations: list[AlterationRecord] = []
    alt_counter = 0

    def make_alteration_id() -> str:
        nonlocal alt_counter
        alt_counter += 1
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"alt_{seed}_{alt_counter}"))

    def _clean_val(v: Any) -> str | None:
        if v is None or pd.isna(v):
            return None
        return str(v)

    # 2. Si rate == 0.0, sauvegarde à l'identique sans mutation
    if rate == 0.0:
        for t_name, df in tables.items():
            t_out = out_path / f"{t_name}.parquet"
            table_pa = pa.Table.from_pandas(df, preserve_index=False)
            pq.write_table(table_pa, t_out, compression="SNAPPY")

        # Journal vide
        empty_dict = {f.name: [] for f in ALTERATION_LOG_SCHEMA}
        empty_table = pa.Table.from_pydict(empty_dict, schema=ALTERATION_LOG_SCHEMA)
        pq.write_table(empty_table, out_path / "alterations_log.parquet", compression="SNAPPY")
        with open(out_path / "alterations_log.jsonl", "w", encoding="utf-8") as f:
            pass
        return {"tables": tables, "alterations_count": 0}

    # 3. Altérations de la table 'patients' et Injection de Doublons
    patients_df = tables["patients"].copy()
    n_patients = len(patients_df)
    total_target_ids = max(1, int(round(n_patients * rate))) if n_patients > 0 else 0

    # Définition du nombre de doublons pour Splink (RULE-DUPL-001)
    # Les doublons ont un row_id distinct, ils comptent dans le nombre d'IDs patients touchés
    num_duplicates = max(1, int(round(total_target_ids * 0.10))) if total_target_ids > 0 else 0
    num_patients_to_alter = max(0, total_target_ids - num_duplicates)

    # Tirage déterministe des patients à altérer
    all_indices = list(range(n_patients))
    chosen_indices = (
        rng.sample(all_indices, num_patients_to_alter) if num_patients_to_alter > 0 else []
    )
    chosen_indices.sort()

    for idx in chosen_indices:
        row = patients_df.iloc[idx]
        p_id = str(row["patient_id"])

        # Sélection déterministe d'une règle d'altération
        rule_choice = rng.choice(
            [
                "RULE-DATE-001",
                "RULE-NAME-001",
                "RULE-NAME-002",
                "RULE-NAME-003",
                "RULE-SENT-001",
                "RULE-MISS-001",
                "RULE-ENCO-001",
                "RULE-DATE-002",
            ]
        )

        col_name = "family_name"
        orig_val = row["family_name"]
        alt_val = orig_val
        desc = ""

        if rule_choice == "RULE-DATE-001":
            col_name = "birth_date"
            orig_val = row["birth_date"]
            alt_val = mutate_date_format(orig_val, seed=rng.randint(0, 100000))
            desc = "Format de date altéré en notation composite"
        elif rule_choice == "RULE-DATE-002":
            col_name = "birth_date"
            orig_val = row["birth_date"]
            alt_val = mutate_approximate_age(orig_val, seed=rng.randint(0, 100000))
            desc = "Remplacement de date de naissance par âge approximatif textuel"
        elif rule_choice == "RULE-NAME-001":
            col_name = "family_name"
            orig_val = row["family_name"]
            alt_val = mutate_name_spelling(orig_val, seed=rng.randint(0, 100000))
            desc = "Coquille patronymique réaliste"
        elif rule_choice == "RULE-NAME-002":
            col_name = "family_name"
            orig_val = row["family_name"]
            alt_val = mutate_strip_accents(orig_val)
            if alt_val == orig_val:
                alt_val = mutate_name_spelling(orig_val, seed=rng.randint(0, 100000))
            desc = "Suppression des accents et diacritiques"
        elif rule_choice == "RULE-NAME-003":
            col_name = "family_name"
            orig_val = row["family_name"]
            alt_val = mutate_invert_name_order(
                orig_val, row["given_name"], seed=rng.randint(0, 100000)
            )
            desc = "Inversion du nom et prénom"
        elif rule_choice == "RULE-SENT-001":
            col_name = "phone_number"
            orig_val = row["phone_number"]
            alt_val = mutate_sentinel(orig_val, seed=rng.randint(0, 100000))
            desc = "Injection de code sentinelle d'indétermination"
        elif rule_choice == "RULE-MISS-001":
            col_name = "phone_number"
            orig_val = row["phone_number"]
            alt_val = mutate_missing(orig_val)
            desc = "Valeur manquante (omission de saisie)"
        elif rule_choice == "RULE-ENCO-001":
            col_name = "family_name"
            orig_val = row["family_name"]
            alt_val = mutate_encoding_mojibake(orig_val, seed=rng.randint(0, 100000))
            desc = "Corruption d'encodage Mojibake (UTF-8 lu en Latin-1)"

        if alt_val == orig_val or alt_val is None and orig_val is None:
            # Forcer une altération garantie pour traçabilité
            col_name = "birth_date"
            orig_val = row["birth_date"]
            alt_val = mutate_date_format(orig_val, seed=rng.randint(0, 100000))
            rule_choice = "RULE-DATE-001"
            desc = "Format de date altéré en notation composite"

        patients_df.at[idx, col_name] = alt_val
        alterations.append(
            AlterationRecord(
                alteration_id=make_alteration_id(),
                table_name="patients",
                row_id=p_id,
                column_name=col_name,
                original_value=_clean_val(orig_val),
                altered_value=_clean_val(alt_val),
                rule_id=rule_choice,
                description=desc,
                timestamp="2024-01-01T00:00:00Z",
            )
        )

    # 4. Injection de Doublons de Patients pour Splink (RULE-DUPL-001)
    # Les doublons ont des identifiants distincts (UUID v5 déterministe)
    dup_source_indices = rng.sample(all_indices, num_duplicates) if num_duplicates > 0 else []
    dup_rows = []

    for dup_i, src_idx in enumerate(dup_source_indices):
        orig_row = patients_df.iloc[src_idx].copy()
        orig_pid = str(orig_row["patient_id"])
        new_pid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"splink_dup_{orig_pid}_{seed}_{dup_i}"))

        orig_row["patient_id"] = new_pid
        # Légère altération sur le patronyme ou prénom
        orig_fam = orig_row["family_name"]
        orig_row["family_name"] = mutate_name_spelling(orig_fam, seed=rng.randint(0, 100000))
        dup_rows.append(orig_row)

        alterations.append(
            AlterationRecord(
                alteration_id=make_alteration_id(),
                table_name="patients",
                row_id=new_pid,
                column_name="patient_id",
                original_value=orig_pid,
                altered_value=new_pid,
                rule_id="RULE-DUPL-001",
                description=f"Doublon patient inter-établissements injecté pour Splink depuis {orig_pid}",
                timestamp="2024-01-01T00:00:00Z",
            )
        )

    if dup_rows:
        patients_df = pd.concat([patients_df, pd.DataFrame(dup_rows)], ignore_index=True)
    tables["patients"] = patients_df

    # 5. Altérations des autres tables cliniques
    # Encounters
    enc_df = tables["encounters"].copy()
    n_enc = int(round(len(enc_df) * rate))
    for enc_idx in rng.sample(range(len(enc_df)), n_enc):
        row = enc_df.iloc[enc_idx]
        eid = str(row["encounter_id"])
        choice = rng.choice(["facility", "reason", "date"])
        if choice == "facility":
            orig = row["facility_name"]
            alt = mutate_facility_name(orig, seed=rng.randint(0, 100000))
            enc_df.at[enc_idx, "facility_name"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="encounters",
                    row_id=eid,
                    column_name="facility_name",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-FACI-001",
                    description="Variante informelle de nom de structure sanitaire",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
        elif choice == "reason":
            orig = row["reason_display"]
            alt = mutate_clinical_freetext(orig, seed=rng.randint(0, 100000))
            enc_df.at[enc_idx, "reason_display"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="encounters",
                    row_id=eid,
                    column_name="reason_display",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-CLIN-001",
                    description="Diagnostic formalisé remplacé par libellé en texte libre",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
        else:
            orig = row["start_date"]
            alt = mutate_date_format(orig, seed=rng.randint(0, 100000))
            enc_df.at[enc_idx, "start_date"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="encounters",
                    row_id=eid,
                    column_name="start_date",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-DATE-001",
                    description="Date d'épisode de soins en format hétérogène",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
    tables["encounters"] = enc_df

    # Conditions
    cond_df = tables["conditions"].copy()
    n_cond = int(round(len(cond_df) * rate))
    for c_idx in rng.sample(range(len(cond_df)), n_cond):
        row = cond_df.iloc[c_idx]
        cid = str(row["condition_id"])
        choice = rng.choice(["display", "date"])
        if choice == "display":
            orig = row["icd10_display"]
            alt = mutate_clinical_freetext(orig, seed=rng.randint(0, 100000))
            cond_df.at[c_idx, "icd10_display"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="conditions",
                    row_id=cid,
                    column_name="icd10_display",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-CLIN-001",
                    description="Libellé nosologique en texte libre",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
        else:
            orig = row["onset_date"]
            alt = mutate_date_format(orig, seed=rng.randint(0, 100000))
            cond_df.at[c_idx, "onset_date"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="conditions",
                    row_id=cid,
                    column_name="onset_date",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-DATE-001",
                    description="Date de début de pathologie composite",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
    tables["conditions"] = cond_df

    # Observations
    obs_df = tables["observations"].copy()
    n_obs = int(round(len(obs_df) * rate))
    for o_idx in rng.sample(range(len(obs_df)), n_obs):
        row = obs_df.iloc[o_idx]
        oid = str(row["observation_id"])
        choice = rng.choice(["unit", "sep"])
        if choice == "unit":
            orig = row["value_unit"]
            alt = mutate_measurement_unit(orig, seed=rng.randint(0, 100000))
            obs_df.at[o_idx, "value_unit"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="observations",
                    row_id=oid,
                    column_name="value_unit",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-MEAS-002",
                    description="Unité de mesure non conforme ou omise",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
        else:
            orig = row["value_string"]
            numeric_val = row["value_numeric"]
            alt = mutate_measurement_separator(numeric_val)
            obs_df.at[o_idx, "value_string"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="observations",
                    row_id=oid,
                    column_name="value_string",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-MEAS-001",
                    description="Séparateur décimal virgule francophone",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
    tables["observations"] = obs_df

    # Prescriptions
    presc_df = tables["prescriptions"].copy()
    n_presc = int(round(len(presc_df) * rate))
    for pr_idx in rng.sample(range(len(presc_df)), n_presc):
        row = presc_df.iloc[pr_idx]
        prid = str(row["prescription_id"])
        choice = rng.choice(["date", "miss"])
        if choice == "date":
            orig = row["prescribed_date"]
            alt = mutate_date_format(orig, seed=rng.randint(0, 100000))
            presc_df.at[pr_idx, "prescribed_date"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="prescriptions",
                    row_id=prid,
                    column_name="prescribed_date",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-DATE-001",
                    description="Date de prescription composite",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
        else:
            orig = row["dosage_instruction"]
            alt = mutate_missing(orig)
            presc_df.at[pr_idx, "dosage_instruction"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="prescriptions",
                    row_id=prid,
                    column_name="dosage_instruction",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-MISS-001",
                    description="Instruction posologique manquante",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
    tables["prescriptions"] = presc_df

    # Immunizations
    imm_df = tables["immunizations"].copy()
    n_imm = int(round(len(imm_df) * rate))
    for imm_idx in rng.sample(range(len(imm_df)), n_imm):
        row = imm_df.iloc[imm_idx]
        imid = str(row["immunization_id"])
        choice = rng.choice(["date", "facility"])
        if choice == "date":
            orig = row["occurrence_date"]
            alt = mutate_date_format(orig, seed=rng.randint(0, 100000))
            imm_df.at[imm_idx, "occurrence_date"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="immunizations",
                    row_id=imid,
                    column_name="occurrence_date",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-DATE-001",
                    description="Date d'immunisation composite",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
        else:
            orig = row["facility_id"]
            alt = mutate_sentinel(orig, seed=rng.randint(0, 100000))
            imm_df.at[imm_idx, "facility_id"] = alt
            alterations.append(
                AlterationRecord(
                    alteration_id=make_alteration_id(),
                    table_name="immunizations",
                    row_id=imid,
                    column_name="facility_id",
                    original_value=_clean_val(orig),
                    altered_value=_clean_val(alt),
                    rule_id="RULE-SENT-001",
                    description="Code sentinelle injecté dans identifiant de formation sanitaire",
                    timestamp="2024-01-01T00:00:00Z",
                )
            )
    tables["immunizations"] = imm_df

    # 6. Sauvegarde déterministe des tables Parquet
    for t_name, df in tables.items():
        t_out = out_path / f"{t_name}.parquet"
        table_pa = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table_pa, t_out, compression="SNAPPY")

    # 7. Sauvegarde déterministe du journal d'altérations (Parquet et JSONL)
    records_dict: dict[str, list[Any]] = {f.name: [] for f in ALTERATION_LOG_SCHEMA}
    for r in alterations:
        records_dict["alteration_id"].append(r.alteration_id)
        records_dict["table_name"].append(r.table_name)
        records_dict["row_id"].append(r.row_id)
        records_dict["column_name"].append(r.column_name)
        records_dict["original_value"].append(r.original_value)
        records_dict["altered_value"].append(r.altered_value)
        records_dict["rule_id"].append(r.rule_id)
        records_dict["description"].append(r.description)
        records_dict["timestamp"].append(r.timestamp)

    log_table = pa.Table.from_pydict(records_dict, schema=ALTERATION_LOG_SCHEMA)
    pq.write_table(log_table, out_path / "alterations_log.parquet", compression="SNAPPY")

    with open(out_path / "alterations_log.jsonl", "w", encoding="utf-8") as f:
        for r in alterations:
            f.write(r.model_dump_json() + "\n")

    return {
        "tables": tables,
        "alterations_count": len(alterations),
        "alterations_log_path": out_path / "alterations_log.parquet",
    }
