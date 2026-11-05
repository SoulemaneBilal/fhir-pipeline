"""Évaluateurs unitaires pour les 6 dimensions normatives de qualité (Étape 6).

Dimensions couvertes :
1. Complétude : détection des nulls, NaN, chaînes vides et codes sentinelles (-1, 999, NA, ND, INCONNU).
2. Exactitude : formats de dates non standard, approximations textuelles d'âge, Mojibake, virgules décimales.
3. Cohérence : grossesses masculines, inversions temporelles, discordances pyramide sanitaire.
4. Unicité : doublons de clés primaires, doublons stricts, quasi-doublons de patients inter-structures.
5. Validité : conformité aux référentiels CIM-10, LOINC, ATC, géographie Togo et unités UCUM.
6. Actualité : dates dans le futur et dates historiques aberrantes (< 01/01/1900).

Conformément à AGENT.md #2, les colonnes d'audit (source_file, source_row,
ingested_at, content_hash) sont systématiquement exclues des évaluations métier.
"""

from __future__ import annotations

import re
import warnings
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.profiling.schemas import DimensionScore, QualityDimension

# Colonnes techniques d'audit obligatoires à ignorer
AUDIT_COLUMNS: frozenset[str] = frozenset(
    {"source_file", "source_row", "ingested_at", "content_hash"}
)

# Codes sentinelles numériques et textuels fréquents
NUMERIC_SENTINELS: frozenset[float] = frozenset({-1.0, 999.0, -999.0, 9999.0})
STRING_SENTINELS: frozenset[str] = frozenset(
    {
        "-1",
        "999",
        "-999",
        "9999",
        "NA",
        "ND",
        "N/A",
        "INCONNU",
        "?",
        "NULL",
        "NONE",
        "UNKNOWN",
        "MISSING",
    }
)

# Unités de mesure internationales conformes au standard UCUM
VALID_UCUM_UNITS: frozenset[str] = frozenset(
    {
        "Cel",
        "mm[Hg]",
        "g/dL",
        "mg/dL",
        "mmol/L",
        "g/L",
        "/min",
        "{breaths}/min",
        "{beats}/min",
        "%",
        "cm",
        "m",
        "kg",
        "g",
        "1",
        "10*9/L",
        "10*12/L",
        "fl",
        "pg",
        "umol/L",
        "U/L",
        "mL/min",
        "kat",
        "[IU]",
        "dB",
    }
)

VALID_GENDERS: frozenset[str] = frozenset({"male", "female", "other", "unknown"})

# Regex de formats de dates non standard
RE_DATE_SLASH = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
RE_DATE_DASH_NON_ISO = re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")
RE_DATE_DOT = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{2,4}$")
RE_DATE_SLASH_INVERTED = re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")

# Regex d'approximations textuelles d'âge
RE_APPROX_AGE = re.compile(
    r"\b(environ|env\.?|vers|né\s+vers|~)\s*\d+|\b\d+\s*ans\b",
    re.IGNORECASE,
)

# Regex de corruption d'encodage Mojibake (UTF-8 lu en Latin-1)
RE_MOJIBAKE = re.compile(r"Ã[©ô¨»à§êîûÃ]|Ã[\x80-\xbf]|Â[^\s]", re.UNICODE)

# Regex de virgule décimale francophone
RE_COMMA_DECIMAL = re.compile(r"^\s*[-+]?\d+,\d+\s*$")


def get_eval_columns(df: pd.DataFrame) -> list[str]:
    """Retourne la liste des colonnes métier hors audit."""
    return [col for col in df.columns if col not in AUDIT_COLUMNS]


def _compute_status(score: float) -> str:
    """Détermine le statut textuel à partir du score (0 à 100%)."""
    if score >= 95.0:
        return "EXCELLENT"
    if score >= 85.0:
        return "BON"
    if score >= 70.0:
        return "MOYEN"
    return "CRITIQUE"


# ==============================================================================
# 1. Complétude (Completeness)
# ==============================================================================


def evaluate_completeness(df: pd.DataFrame, table_name: str = "") -> DimensionScore:
    """Évalue la complétude des données (absence de nulls, chaînes vides et sentinelles)."""
    cols = get_eval_columns(df)
    n_rows = len(df)
    if n_rows == 0 or len(cols) == 0:
        return DimensionScore(
            dimension=QualityDimension.COMPLETENESS,
            score=100.0,
            status="EXCELLENT",
            description="Table vide ou sans colonnes évaluables.",
            issues_detected=0,
            details={"total_cells": 0, "nulls_total": 0, "sentinels_total": 0, "empty_total": 0},
        )

    total_cells = n_rows * len(cols)
    nulls_total = 0
    empty_total = 0
    sentinels_total = 0
    col_details: dict[str, Any] = {}

    for col in cols:
        series = df[col]
        # 1. Nulls et NaN
        null_mask = series.isna() | series.isnull()
        col_nulls = int(null_mask.sum())

        # 2. Chaînes vides (sur les valeurs non nulles)
        non_null = series[~null_mask]
        str_repr = non_null.astype(str).str.strip()
        empty_mask = str_repr == ""
        col_empty = int(empty_mask.sum())

        # 3. Sentinelles
        val_to_check = non_null[~empty_mask]
        sentinel_count = 0

        # Vérification numérique
        if pd.api.types.is_numeric_dtype(series):
            sentinel_mask = val_to_check.isin(NUMERIC_SENTINELS)
            sentinel_count = int(sentinel_mask.sum())
        else:
            # Vérification textuelle
            upper_vals = val_to_check.astype(str).str.strip().str.upper()
            sentinel_mask = upper_vals.isin(STRING_SENTINELS)
            sentinel_count = int(sentinel_mask.sum())

        col_issues = col_nulls + col_empty + sentinel_count
        nulls_total += col_nulls
        empty_total += col_empty
        sentinels_total += sentinel_count

        col_details[col] = {
            "nulls": col_nulls,
            "empty": col_empty,
            "sentinels": sentinel_count,
            "issues": col_issues,
        }

    total_issues = nulls_total + empty_total + sentinels_total
    score = max(0.0, min(100.0, 100.0 * (1.0 - total_issues / max(1, total_cells))))

    return DimensionScore(
        dimension=QualityDimension.COMPLETENESS,
        score=round(score, 2),
        status=_compute_status(score),
        description=f"Complétude globale : {score:.1f}% ({total_issues} cellules manquantes ou sentinelles sur {total_cells}).",
        issues_detected=total_issues,
        details={
            "table_name": table_name,
            "total_cells": total_cells,
            "nulls_total": nulls_total,
            "empty_total": empty_total,
            "sentinels_total": sentinels_total,
            "columns": col_details,
        },
    )


# ==============================================================================
# 2. Exactitude (Accuracy)
# ==============================================================================


def evaluate_accuracy(df: pd.DataFrame, table_name: str = "") -> DimensionScore:
    """Évalue l'exactitude des formats (dates non-ISO, âges approximatifs, Mojibake, virgules)."""
    cols = get_eval_columns(df)
    n_rows = len(df)
    if n_rows == 0 or len(cols) == 0:
        return DimensionScore(
            dimension=QualityDimension.ACCURACY,
            score=100.0,
            status="EXCELLENT",
            description="Table vide ou sans colonnes évaluables.",
            issues_detected=0,
            details={},
        )

    total_cells = n_rows * len(cols)
    total_issues = 0
    issue_types: dict[str, int] = {
        "dates_non_iso": 0,
        "approximate_ages": 0,
        "mojibake": 0,
        "comma_decimals": 0,
    }

    for col in cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue

        str_vals = series.astype(str).str.strip()
        col_lower = col.lower()
        is_date_col = "date" in col_lower or any(
            d_word in col_lower
            for d_word in ["birth", "start", "end", "onset", "prescribed", "occurrence"]
        )

        for val in str_vals:
            if not val or val.upper() in STRING_SENTINELS:
                continue

            # A. Détection des formats de date non standard et approximations d'âge
            if is_date_col:
                if RE_APPROX_AGE.search(val):
                    issue_types["approximate_ages"] += 1
                    total_issues += 1
                    continue
                if (
                    RE_DATE_SLASH.match(val)
                    or RE_DATE_DASH_NON_ISO.match(val)
                    or RE_DATE_DOT.match(val)
                    or RE_DATE_SLASH_INVERTED.match(val)
                ):
                    issue_types["dates_non_iso"] += 1
                    total_issues += 1
                    continue

            # B. Détection du Mojibake d'encodage
            if RE_MOJIBAKE.search(val):
                issue_types["mojibake"] += 1
                total_issues += 1
                continue

            # C. Détection de virgule décimale francophone
            if (
                "quantity" in col_lower
                or "numeric" in col_lower
                or "value" in col_lower
                or table_name == "observations"
            ) and RE_COMMA_DECIMAL.match(val):
                issue_types["comma_decimals"] += 1
                total_issues += 1
                continue

    score = max(0.0, min(100.0, 100.0 * (1.0 - total_issues / max(1, total_cells))))

    return DimensionScore(
        dimension=QualityDimension.ACCURACY,
        score=round(score, 2),
        status=_compute_status(score),
        description=f"Exactitude syntaxique : {score:.1f}% ({total_issues} anomalies de format détectées).",
        issues_detected=total_issues,
        details={
            "table_name": table_name,
            "issue_breakdown": issue_types,
            "total_cells": total_cells,
        },
    )


# ==============================================================================
# 3. Cohérence (Consistency)
# ==============================================================================


def evaluate_consistency(
    df: pd.DataFrame,
    table_name: str = "",
    reference_geography: pd.DataFrame | None = None,
) -> DimensionScore:
    """Évalue la cohérence clinique, temporelle et hiérarchique."""
    n_rows = len(df)
    if n_rows == 0:
        return DimensionScore(
            dimension=QualityDimension.CONSISTENCY,
            score=100.0,
            status="EXCELLENT",
            description="Table vide.",
            issues_detected=0,
            details={},
        )

    issues = 0
    issue_types: dict[str, int] = {
        "male_pregnancy": 0,
        "temporal_inversion": 0,
        "pyramid_category_mismatch": 0,
    }

    # 1. Grossesses masculines
    if "gender" in df.columns:
        male_mask = df["gender"].astype(str).str.strip().str.lower().isin(["male", "m", "homme"])
        male_df = df[male_mask]

        # Vérification des codes de diagnostic (Z34, Z35, O00-O99)
        code_cols = [c for c in ["icd10_code", "reason_code", "code"] if c in male_df.columns]
        for c in code_cols:
            c_vals = male_df[c].dropna().astype(str).str.strip().str.upper()
            preg_mask = c_vals.str.startswith(("Z34", "Z35", "O80", "O82", "O"))
            cnt = int(preg_mask.sum())
            if cnt > 0:
                issue_types["male_pregnancy"] += cnt
                issues += cnt

        # Vérification des libellés textuels
        disp_cols = [
            c for c in ["icd10_display", "reason_display", "display"] if c in male_df.columns
        ]
        for c in disp_cols:
            d_vals = male_df[c].dropna().astype(str).str.lower()
            preg_mask = d_vals.str.contains(
                r"grossesse|maternité|accouchement|obstétri", regex=True
            )
            cnt = int(preg_mask.sum())
            if cnt > 0 and len(code_cols) == 0:
                issue_types["male_pregnancy"] += cnt
                issues += cnt

    # 2. Inversion temporelle (start_date > end_date)
    date_pairs = [
        ("start_date", "end_date"),
        ("start_datetime", "end_datetime"),
        ("onset_date", "recorded_date"),
    ]
    for start_col, end_col in date_pairs:
        if start_col in df.columns and end_col in df.columns:
            sub = df[[start_col, end_col]].dropna()
            for _, r in sub.iterrows():
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        s_dt = pd.to_datetime(r[start_col], errors="coerce")
                        e_dt = pd.to_datetime(r[end_col], errors="coerce")
                    if pd.notna(s_dt) and pd.notna(e_dt) and s_dt > e_dt:
                        issue_types["temporal_inversion"] += 1
                        issues += 1
                except Exception:
                    continue

    # 3. Discordance pyramide des soins vs catégorie de formation
    cat_col = (
        "facility_category"
        if "facility_category" in df.columns
        else ("category" if "category" in df.columns else None)
    )
    if "pyramid_level" in df.columns and cat_col:
        sub = df[[cat_col, "pyramid_level"]].dropna()
        for _, r in sub.iterrows():
            c_val = str(r[cat_col]).strip().upper()
            try:
                p_val = int(r["pyramid_level"])
            except (ValueError, TypeError):
                continue

            # Discordance pyramide vs catégorie
            if (
                (c_val == "CHU" and p_val < 3)
                or (c_val in ("USP", "CMS") and p_val != 1)
                or (c_val == "CHR" and p_val in (1, 4))
            ):
                issue_types["pyramid_category_mismatch"] += 1
                issues += 1

    score = max(0.0, min(100.0, 100.0 * (1.0 - issues / max(1, n_rows))))

    return DimensionScore(
        dimension=QualityDimension.CONSISTENCY,
        score=round(score, 2),
        status=_compute_status(score),
        description=f"Cohérence clinique et structurelle : {score:.1f}% ({issues} incohérences détectées).",
        issues_detected=issues,
        details={
            "table_name": table_name,
            "issue_breakdown": issue_types,
            "total_rows": n_rows,
            "has_reference_geography": reference_geography is not None,
        },
    )


# ==============================================================================
# 4. Unicité (Uniqueness)
# ==============================================================================


def evaluate_uniqueness(
    df: pd.DataFrame,
    table_name: str = "",
    primary_key: str | None = None,
) -> DimensionScore:
    """Évalue l'unicité (doublons de clés primaires, stricts et quasi-doublons suspects)."""
    n_rows = len(df)
    if n_rows == 0:
        return DimensionScore(
            dimension=QualityDimension.UNIQUENESS,
            score=100.0,
            status="EXCELLENT",
            description="Table vide.",
            issues_detected=0,
            details={},
        )

    cols = get_eval_columns(df)
    pk_col = primary_key
    if not pk_col:
        # Recherche heuristique de la clé primaire
        candidates = [
            f"{table_name.rstrip('s')}_id",
            f"{table_name}_id",
            "patient_id",
            "encounter_id",
            "id",
        ]
        for cand in candidates:
            if cand in df.columns:
                pk_col = cand
                break
        if not pk_col:
            id_cols = [c for c in df.columns if c.endswith("_id")]
            if id_cols:
                pk_col = id_cols[0]

    pk_dups = 0
    if pk_col and pk_col in df.columns:
        pk_dups = int(df[pk_col].duplicated().sum())

    # Doublons stricts de lignes (hors audit)
    strict_dups = int(df.duplicated(subset=cols, keep="first").sum())

    # Quasi-doublons de patients inter-établissements (identifiant distinct mais profil similaire)
    quasi_dups = 0
    if {"family_name", "birth_date"}.issubset(set(df.columns)):
        # Même nom et date de naissance
        quasi_dups = int(df.duplicated(subset=["family_name", "birth_date"], keep="first").sum())
    elif "identifier_value" in df.columns and pk_col:
        # Même identifiant national avec des clés primaires distinctes
        quasi_dups = int(df.duplicated(subset=["identifier_value"], keep="first").sum())

    total_issues = pk_dups + (quasi_dups if pk_dups == 0 else 0)
    if total_issues == 0 and strict_dups > 0:
        total_issues = strict_dups

    score = max(0.0, min(100.0, 100.0 * (1.0 - total_issues / max(1, n_rows))))

    return DimensionScore(
        dimension=QualityDimension.UNIQUENESS,
        score=round(score, 2),
        status=_compute_status(score),
        description=f"Unicité des enregistrements : {score:.1f}% ({total_issues} doublons détectés).",
        issues_detected=total_issues,
        details={
            "pk_column": pk_col,
            "pk_duplicates": pk_dups,
            "strict_duplicates": strict_dups,
            "quasi_duplicates": quasi_dups,
            "total_rows": n_rows,
        },
    )


# ==============================================================================
# 5. Validité (Validity)
# ==============================================================================


def evaluate_validity(
    df: pd.DataFrame,
    table_name: str = "",
    vocabs_path: Path | str | None = None,
    geography_path: Path | str | None = None,
) -> DimensionScore:
    """Évalue la conformité des données aux référentiels (CIM-10, LOINC, ATC, Togo, UCUM, genres)."""
    n_rows = len(df)
    if n_rows == 0:
        return DimensionScore(
            dimension=QualityDimension.VALIDITY,
            score=100.0,
            status="EXCELLENT",
            description="Table vide.",
            issues_detected=0,
            details={},
        )

    # Résolution des référentiels
    v_path = Path(vocabs_path) if vocabs_path else Path("terminology/sample_vocabularies.parquet")
    g_path = (
        Path(geography_path)
        if geography_path
        else Path("data/reference/togo_health_geography.parquet")
    )

    valid_icd10: set[str] = set()
    valid_loinc: set[str] = set()
    valid_atc: set[str] = set()
    valid_snomed: set[str] = set()

    if v_path.exists():
        try:
            df_voc = pd.read_parquet(v_path)
            for _, r in df_voc.iterrows():
                voc_id = str(r.get("vocabulary_id", "")).upper()
                c_code = str(r.get("concept_code", "")).strip()
                if not c_code:
                    continue
                if voc_id == "ICD10":
                    valid_icd10.add(c_code)
                elif voc_id == "LOINC":
                    valid_loinc.add(c_code)
                elif voc_id == "ATC":
                    valid_atc.add(c_code)
                elif voc_id == "SNOMED":
                    valid_snomed.add(c_code)
        except Exception:
            pass

    valid_facilities: set[str] = set()
    valid_districts: set[str] = set()
    valid_regions: set[str] = set()

    if g_path.exists():
        try:
            df_geo = pd.read_parquet(g_path)
            if "facility_id" in df_geo.columns:
                valid_facilities.update(df_geo["facility_id"].dropna().astype(str).str.strip())
            if "district_code" in df_geo.columns:
                valid_districts.update(df_geo["district_code"].dropna().astype(str).str.strip())
            if "region_code" in df_geo.columns:
                valid_regions.update(df_geo["region_code"].dropna().astype(str).str.strip())
        except Exception:
            pass

    issues = 0
    total_checked = 0
    issue_types: dict[str, int] = {
        "invalid_icd10": 0,
        "invalid_loinc": 0,
        "invalid_atc": 0,
        "invalid_facility": 0,
        "invalid_district": 0,
        "invalid_region": 0,
        "non_ucum_unit": 0,
        "invalid_gender": 0,
    }

    # 1. Validation CIM-10
    if "icd10_code" in df.columns and valid_icd10:
        vals = df["icd10_code"].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in valid_icd10:
                    issue_types["invalid_icd10"] += 1
                    issues += 1

    # 2. Validation LOINC
    if "loinc_code" in df.columns and valid_loinc:
        vals = df["loinc_code"].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in valid_loinc:
                    issue_types["invalid_loinc"] += 1
                    issues += 1

    # 3. Validation ATC
    if "atc_code" in df.columns and valid_atc:
        vals = df["atc_code"].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in valid_atc:
                    issue_types["invalid_atc"] += 1
                    issues += 1

    # 4. Validation Géographie Togo
    if "facility_id" in df.columns and valid_facilities:
        vals = df["facility_id"].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in valid_facilities:
                    issue_types["invalid_facility"] += 1
                    issues += 1

    if "district_code" in df.columns and valid_districts:
        vals = df["district_code"].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in valid_districts:
                    issue_types["invalid_district"] += 1
                    issues += 1

    if "region_code" in df.columns and valid_regions:
        vals = df["region_code"].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in valid_regions:
                    issue_types["invalid_region"] += 1
                    issues += 1

    # 5. Validation Unités UCUM
    unit_col = (
        "value_unit" if "value_unit" in df.columns else ("unit" if "unit" in df.columns else None)
    )
    if unit_col:
        vals = df[unit_col].dropna().astype(str).str.strip()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in VALID_UCUM_UNITS:
                    issue_types["non_ucum_unit"] += 1
                    issues += 1

    # 6. Validation Valeurs de Genre
    if "gender" in df.columns:
        vals = df["gender"].dropna().astype(str).str.strip().str.lower()
        for v in vals:
            if v and v.upper() not in STRING_SENTINELS:
                total_checked += 1
                if v not in VALID_GENDERS:
                    issue_types["invalid_gender"] += 1
                    issues += 1

    denom = max(total_checked, n_rows)
    score = max(0.0, min(100.0, 100.0 * (1.0 - issues / max(1, denom))))

    return DimensionScore(
        dimension=QualityDimension.VALIDITY,
        score=round(score, 2),
        status=_compute_status(score),
        description=f"Validité terminologique et géographique : {score:.1f}% ({issues} valeurs hors référentiels sur {denom} contrôlées).",
        issues_detected=issues,
        details={
            "table_name": table_name,
            "issue_breakdown": issue_types,
            "total_checked": total_checked,
        },
    )


# ==============================================================================
# 6. Actualité (Timeliness)
# ==============================================================================


def evaluate_timeliness(
    df: pd.DataFrame,
    table_name: str = "",
    reference_date: datetime | str | None = None,
) -> DimensionScore:
    """Évalue l'actualité et la vraisemblance temporelle (pas de futur, pas d'antériorité < 1900)."""
    n_rows = len(df)
    if n_rows == 0:
        return DimensionScore(
            dimension=QualityDimension.TIMELINESS,
            score=100.0,
            status="EXCELLENT",
            description="Table vide.",
            issues_detected=0,
            details={},
        )

    # Résolution de la date de référence
    if reference_date is None:
        ref_dt = datetime.now(UTC).date()
    elif isinstance(reference_date, str):
        ref_dt = pd.to_datetime(reference_date).date()
    elif isinstance(reference_date, datetime):
        ref_dt = reference_date.date()
    else:
        ref_dt = reference_date

    min_dt = date(1900, 1, 1)

    # Colonnes de dates à évaluer (hors audit)
    cols = get_eval_columns(df)
    date_cols = [
        c
        for c in cols
        if "date" in c.lower()
        or any(
            w in c.lower()
            for w in ["birth", "start", "end", "onset", "prescribed", "occurrence", "encounter"]
        )
    ]

    issues = 0
    total_dates_checked = 0
    issue_types: dict[str, int] = {"future_dates": 0, "historical_aberrant_dates": 0}

    for col in date_cols:
        series = df[col].dropna()
        for raw_val in series:
            s_val = str(raw_val).strip()
            if not s_val or s_val.upper() in STRING_SENTINELS:
                continue

            # Tentative d'extraction ISO rapide
            iso_match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s_val)
            parsed_date: date | None = None
            if iso_match:
                try:
                    y, m, d = (
                        int(iso_match.group(1)),
                        int(iso_match.group(2)),
                        int(iso_match.group(3)),
                    )
                    parsed_date = date(y, m, d)
                except ValueError:
                    parsed_date = None

            if parsed_date is None:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", UserWarning)
                        dt = pd.to_datetime(s_val, errors="coerce")
                    if pd.notna(dt):
                        parsed_date = dt.date()
                except Exception:
                    parsed_date = None

            if parsed_date is not None:
                total_dates_checked += 1
                if parsed_date > ref_dt:
                    issue_types["future_dates"] += 1
                    issues += 1
                elif parsed_date < min_dt:
                    issue_types["historical_aberrant_dates"] += 1
                    issues += 1

    denom = max(total_dates_checked, 1)
    score = max(0.0, min(100.0, 100.0 * (1.0 - issues / denom)))

    return DimensionScore(
        dimension=QualityDimension.TIMELINESS,
        score=round(score, 2),
        status=_compute_status(score),
        description=f"Actualité et vraisemblance temporelle : {score:.1f}% ({issues} dates aberrantes détectées sur {total_dates_checked}).",
        issues_detected=issues,
        details={
            "table_name": table_name,
            "issue_breakdown": issue_types,
            "total_dates_checked": total_dates_checked,
        },
    )
