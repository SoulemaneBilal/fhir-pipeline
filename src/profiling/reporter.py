"""Générateur de rapports d'évaluation qualité (Markdown et JSON) (Étape 6).

Produit le « Rapport Avant » synthétisant le diagnostic initial de la couche Bronze :
- Synthèse exécutive et score global de santé qualité (jauge)
- Tableau récapitulatif des 6 dimensions normatives (Complétude, Exactitude,
  Cohérence, Unicité, Validité, Actualité)
- Diagnostic approfondi par table clinique et analyse des colonnes
- Matrice de confrontation face au journal d'altérations injectées
- Recommandations opérationnelles pour l'Étape 7 (Nettoyage déclaratif Silver)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.profiling.schemas import ProfilingReport, QualityDimension

DIMENSION_LABELS_FR: dict[QualityDimension | str, str] = {
    QualityDimension.COMPLETENESS: "Complétude",
    "completeness": "Complétude",
    QualityDimension.ACCURACY: "Exactitude",
    "accuracy": "Exactitude",
    QualityDimension.CONSISTENCY: "Cohérence",
    "consistency": "Cohérence",
    QualityDimension.UNIQUENESS: "Unicité",
    "uniqueness": "Unicité",
    QualityDimension.VALIDITY: "Validité",
    "validity": "Validité",
    QualityDimension.TIMELINESS: "Actualité",
    "timeliness": "Actualité",
}

DIMENSION_DESCRIPTIONS_FR: dict[QualityDimension | str, str] = {
    QualityDimension.COMPLETENESS: "Absence de valeurs nulles, chaînes vides et codes sentinelles (-1, 999, NA, ND)",
    "completeness": "Absence de valeurs nulles, chaînes vides et codes sentinelles (-1, 999, NA, ND)",
    QualityDimension.ACCURACY: "Conformité syntaxique (dates ISO 8601, absence d'âges textuels, absence de Mojibake, points décimaux)",
    "accuracy": "Conformité syntaxique (dates ISO 8601, absence d'âges textuels, absence de Mojibake, points décimaux)",
    QualityDimension.CONSISTENCY: "Cohérence clinique et logique (absence de grossesses masculines, dates ordonnées, pyramide des soins)",
    "consistency": "Cohérence clinique et logique (absence de grossesses masculines, dates ordonnées, pyramide des soins)",
    QualityDimension.UNIQUENESS: "Unicité stricte des identifiants et absence de doublons de patients inter-structures",
    "uniqueness": "Unicité stricte des identifiants et absence de doublons de patients inter-structures",
    QualityDimension.VALIDITY: "Conformité aux référentiels officiels (CIM-10, LOINC, ATC, découpage territorial Togo, UCUM)",
    "validity": "Conformité aux référentiels officiels (CIM-10, LOINC, ATC, découpage territorial Togo, UCUM)",
    QualityDimension.TIMELINESS: "Vraisemblance temporelle (absence de dates futures et dates historiques aberrantes < 1900)",
    "timeliness": "Vraisemblance temporelle (absence de dates futures et dates historiques aberrantes < 1900)",
}


def _get_badge(score: float) -> str:
    """Retourne un indicateur visuel en fonction du score."""
    if score >= 95.0:
        return "🟢 **EXCELLENT**"
    if score >= 85.0:
        return "🟢 **BON**"
    if score >= 70.0:
        return "🟡 **MOYEN**"
    return "🔴 **CRITIQUE**"


def generate_markdown_report(report: ProfilingReport, output_path: Path | str) -> Path:
    """Génère un rapport structuré Markdown d'évaluation qualité initial (Rapport Avant)."""
    p_out = Path(output_path)
    p_out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    # 1. En-tête et Titre
    lines.append("# Rapport de Diagnostic Initial et Profilage Qualité Bronze (Rapport Avant)")
    lines.append("")
    lines.append(f"> **Identifiant du rapport** : `{report.report_id}`  ")
    lines.append(f"> **Date de génération** : `{report.generated_at}`  ")
    lines.append(
        "> **Statut du pipeline** : Couche Bronze Parquet (`data/bronze/` ou `data/degraded/`)  "
    )
    lines.append(
        f"> **Score global de santé qualité** : **{report.overall_score:.1f}%** {_get_badge(report.overall_score)}"
    )
    lines.append("")

    # 2. Synthèse exécutive
    lines.append("## 1. Synthèse Exécutive et Score Global de Santé Qualité")
    lines.append("")
    lines.append(
        "Ce rapport dresse le diagnostic exhaustif initial des données de santé brutes converties en format Parquet."
    )
    lines.append(
        "L'analyse est menée sur **6 dimensions normatives** de qualité des données, sans altération des données sources."
    )
    lines.append("")
    lines.append("### Chiffres Clés de la Synthèse Exécutive")
    lines.append(f"- **Nombre total de tables analysées** : {len(report.tables)}")
    lines.append(f"- **Volume total d'enregistrements (lignes)** : {report.total_rows_analyzed:,}")
    lines.append(f"- **Total d'anomalies de qualité détectées** : {report.total_issues_detected:,}")
    lines.append(f"- **Indice global de santé qualité** : **{report.overall_score:.2f}%**")
    lines.append("")

    for note in report.summary_notes:
        lines.append(f"- ℹ️ {note}")
    lines.append("")

    # 3. Tableau récapitulatif des 6 dimensions normatives
    lines.append("## 2. Tableau Récapitulatif des 6 Dimensions Normatives de Qualité")
    lines.append("")
    lines.append(
        "| Dimension | Nom Français | Score Qualité | Statut | Définition & Contrôles Clés |"
    )
    lines.append("| :--- | :--- | :---: | :---: | :--- |")

    for dim in QualityDimension:
        score = report.dimensions.get(dim, report.dimensions.get(dim.value, 0.0))
        label_fr = DIMENSION_LABELS_FR.get(dim, dim.value.capitalize())
        desc_fr = DIMENSION_DESCRIPTIONS_FR.get(dim, "")
        badge = _get_badge(score)
        lines.append(f"| `{dim.name}` | **{label_fr}** | **{score:.1f}%** | {badge} | {desc_fr} |")

    lines.append("")

    # 4. Diagnostic détaillé par table clinique
    lines.append("## 3. Diagnostic Détaillé par Table Clinique")
    lines.append("")
    lines.append(
        "Chaque table clinique fait l'objet d'un profilage par colonne et d'un score agrégé par dimension."
    )
    lines.append("")

    for t_name, summary in report.tables.items():
        lines.append(f"### Table clinique : `{t_name}`")
        lines.append(
            f"- **Lignes totales** : {summary.total_rows:,} | **Colonnes** : {summary.columns_count} | **Score global** : **{summary.global_score:.1f}%** {_get_badge(summary.global_score)} | **Anomalies** : {summary.issues_count}"
        )
        lines.append("")

        # Scores dimensionnels de la table
        lines.append("**Scores par dimension :**")
        dim_summary_parts = []
        for d in QualityDimension:
            sc = summary.dimension_scores.get(d, summary.dimension_scores.get(d.value, 0.0))
            lbl = DIMENSION_LABELS_FR.get(d, d.value)
            dim_summary_parts.append(f"- {lbl} : **{sc:.1f}%**")
        lines.extend(dim_summary_parts)
        lines.append("")

        # Tableau des colonnes si disponible
        if summary.columns:
            lines.append("**Métriques par colonne :**")
            lines.append("")
            lines.append(
                "| Colonne | Valeurs Nulles | Sentinelles | Complétude (%) | Valeurs Distinctes |"
            )
            lines.append("| :--- | :---: | :---: | :---: | :---: |")
            for c_name, c_metric in summary.columns.items():
                if c_metric.details.get("is_audit"):
                    continue
                null_info = f"{c_metric.null_count} ({c_metric.null_ratio * 100:.1f}%)"
                sent_info = f"{c_metric.sentinel_count} ({c_metric.sentinel_ratio * 100:.1f}%)"
                lines.append(
                    f"| `{c_name}` | {null_info} | {sent_info} | {c_metric.completeness_score:.1f}% | {c_metric.distinct_count:,} |"
                )
            lines.append("")

    # 5. Matrice de confrontation face au journal d'altérations (si fourni)
    if report.recall_metrics:
        lines.append("## 4. Matrice de Confrontation au Journal d'Altérations (Taux de Rappel)")
        lines.append("")
        lines.append(
            "Confrontation rigoureuse des anomalies détectées par le profiler face aux erreurs réelles injectées dans le journal (`alterations_log.parquet`)."
        )
        lines.append("")
        lines.append(
            "| Règle d'Altération | Nom de la Règle | Table Cible | Colonne Cible | Altérations Injectées | Détectées | Taux de Rappel | Précision |"
        )
        lines.append("| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |")

        total_inj = sum(m.total_injected for m in report.recall_metrics)
        total_det = sum(m.detected_count for m in report.recall_metrics)
        overall_recall = (total_det / max(1, total_inj)) * 100.0

        for m in report.recall_metrics:
            rec_pct = m.recall * 100.0 if m.recall <= 1.0 else m.recall
            prec_pct = (m.precision * 100.0) if m.precision is not None else 100.0
            rec_badge = "🟢" if rec_pct >= 80.0 else ("🟡" if rec_pct >= 60.0 else "🔴")
            lines.append(
                f"| `{m.rule_id}` | {m.rule_name} | `{m.target_table}` | `{m.target_column}` | {m.total_injected} | {m.detected_count} | {rec_badge} **{rec_pct:.1f}%** | {prec_pct:.1f}% |"
            )

        lines.append("")
        lines.append(
            f"**Bilan global de rappel face au corrigé** : **{overall_recall:.1f}%** ({total_det}/{total_inj} anomalies réelles interceptées). Seuil minimal requis : >= 80.0%."
        )
        lines.append("")

    # 6. Recommandations ciblées pour l'Étape 7 (Nettoyage Silver)
    lines.append("## 5. Recommandations Ciblées pour l'Étape 7 (Nettoyage Silver)")
    lines.append("")
    lines.append(
        "Sur la base des anomalies identifiées dans ce profilage initial, les actions prioritaires de nettoyage déclaratif (YAML) et de normalisation pour la couche Silver sont :"
    )
    lines.append("")
    lines.append("1. **Normalisation des dates vers ISO 8601 (`YYYY-MM-DD`)** :")
    lines.append(
        "   - Convertir systématiquement les dates aux formats `JJ/MM/AAAA`, `JJ-MM-AAAA`, `AAAA/MM/JJ` et `JJ.MM.AA`."
    )
    lines.append(
        "   - Traiter les approximations textuelles d'âge (`environ 35 ans`, `vers 40 ans`) en calculant une date de naissance approchée avec le flag `estimated_age_flag=True`."
    )
    lines.append("2. **Purge des codes sentinelles d'indétermination** :")
    lines.append(
        "   - Convertir les sentinelles (`-1`, `999`, `-999`, `NA`, `ND`, `INCONNU`) en valeurs nulles standards (`None` / `pd.NA`)."
    )
    lines.append("3. **Harmonisation des séparateurs décimaux** :")
    lines.append(
        "   - Remplacer les virgules décimales (`38,5`) par des points (`38.5`) et convertir les mesures physiologiques en types numériques standard."
    )
    lines.append("4. **Correction du Mojibake et ré-encodage UTF-8** :")
    lines.append(
        "   - Réparer les patronymes et libellés corrompus par une double lecture Latin-1 / UTF-8 (`Ã©` vers `é`, `Ã´` vers `ô`)."
    )
    lines.append("5. **Standardisation des unités de mesure selon UCUM** :")
    lines.append(
        "   - Normaliser les unités locales (`°C`, `deg C` vers `Cel`, `cmHg` vers `mm[Hg]`, `g/l` vers `g/L`)."
    )
    lines.append("6. **Dé-doublonnage des identités patient (Préparation Splink - Étape 8)** :")
    lines.append(
        "   - Rapprocher les doublons inter-établissements partageant nom, prénom approché et date de naissance identique."
    )
    lines.append("7. **Validation terminologique et géographique** :")
    lines.append(
        "   - Aligner les libellés libres et abréviations de diagnostics sur les concepts officiels CIM-10 et LOINC."
    )
    lines.append(
        "   - Aligner les noms informels de formations sanitaires sur le référentiel officiel du Togo (`data/reference/togo_health_geography.parquet`)."
    )
    lines.append("")
    lines.append("---")
    lines.append(
        "*Rapport généré automatiquement par le Moteur de Profilage Qualité (Étape 6) - Pipeline FHIR Togo.*"
    )
    lines.append("")

    p_out.write_text("\n".join(lines), encoding="utf-8")
    return p_out


def generate_json_report(report: ProfilingReport, output_path: Path | str) -> Path:
    """Sérialise le rapport de profilage au format JSON structuré machine-readable."""
    p_out = Path(output_path)
    p_out.parent.mkdir(parents=True, exist_ok=True)

    data = report.model_dump() if hasattr(report, "model_dump") else report.dict()

    # Conversion propre des clés Enum en chaînes si nécessaire
    def _convert_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                str(k.value if hasattr(k, "value") else k): _convert_keys(v) for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_convert_keys(item) for item in obj]
        return obj

    clean_data = _convert_keys(data)

    p_out.write_text(json.dumps(clean_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p_out
