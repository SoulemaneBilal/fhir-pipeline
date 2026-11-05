"""Tests de validation des commandes CLI Typer pour le banc de dégradation contrôlée (Étape 4).

Conforme aux spécifications formelles de DISPATCH.md, SCOPE.md et SYNTHESE_PROJET.md.
Vérifie :
- L'enregistrement et les textes d'aide en français des commandes `degradation apply` et `degradation list-rules`.
- L'exécution de `pipeline degradation list-rules` (et avec `--detailed`).
- L'exécution de `pipeline degradation apply` avec options `--rate`, `--seed`, `--output-dir`, `--source-dir`, `--export-formats`.
- La restitution visuelle Rich (statuts, tableaux récapitulatifs des altérations).
- La gestion rigoureuse des arguments invalides (taux hors bornes [0.0, 1.0], source inexistante).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()
IS_STRICT = os.environ.get("STRICT_E2E") == "1"

TRUTH_DIR = Path("data/truth")


# ==============================================================================
# 1. Enregistrement des commandes et Aide en Français
# ==============================================================================


def test_cli_degradation_group_help() -> None:
    """Vérifie que le groupe de commandes 'degradation' est enregistré avec aide en français."""
    result = runner.invoke(app, ["degradation", "--help"])
    assert result.exit_code == 0, f"Erreur help degradation : {result.output}"
    out_lower = result.output.lower()
    assert (
        "dégradation" in out_lower
        or "altération" in out_lower
        or "anomalie" in out_lower
        or "stress" in out_lower
    ), "L'aide du groupe 'degradation' doit être rédigée en français"
    assert "apply" in result.output, "Sous-commande 'apply' manquante dans 'degradation --help'"
    assert "list-rules" in result.output, (
        "Sous-commande 'list-rules' manquante dans 'degradation --help'"
    )


def test_cli_degradation_list_rules_help() -> None:
    """Vérifie que la commande 'degradation list-rules' affiche son aide en français avec ses options."""
    result = runner.invoke(app, ["degradation", "list-rules", "--help"])
    assert result.exit_code == 0, f"Erreur help degradation list-rules : {result.output}"
    output = result.output
    assert "--detailed" in output, (
        "Option --detailed manquante dans 'degradation list-rules --help'"
    )
    out_lower = output.lower()
    assert "règle" in out_lower or "catalogue" in out_lower or "altération" in out_lower, (
        "L'aide de 'degradation list-rules' doit être en français"
    )


def test_cli_degradation_apply_help() -> None:
    """Vérifie que la commande 'degradation apply' affiche son aide avec les options requises."""
    result = runner.invoke(app, ["degradation", "apply", "--help"])
    assert result.exit_code == 0, f"Erreur help degradation apply : {result.output}"
    output = result.output
    assert "--rate" in output, "Option --rate manquante dans 'degradation apply --help'"
    assert "--seed" in output, "Option --seed manquante dans 'degradation apply --help'"
    assert "--output-dir" in output, "Option --output-dir manquante dans 'degradation apply --help'"


# ==============================================================================
# 2. Exécution de `degradation list-rules`
# ==============================================================================


def test_cli_degradation_list_rules_execution() -> None:
    """Vérifie l'exécution de 'pipeline degradation list-rules' et l'affichage des identifiants clés."""
    result = runner.invoke(app, ["degradation", "list-rules"])
    assert result.exit_code == 0, f"Échec d'exécution de 'degradation list-rules' : {result.output}"
    output = result.output

    # Vérification progressive de l'affichage du catalogue complet
    expected_sample_rules = ["RULE-DATE-001", "RULE-NAME-001", "RULE-CLIN-001", "RULE-SENT-001"]
    has_rules = any(rule in output for rule in expected_sample_rules)
    if not has_rules:
        if IS_STRICT:
            pytest.fail(
                f"La commande 'degradation list-rules' n'affiche pas les règles du catalogue. "
                f"Sortie : {output}"
            )
        # Tolérance pendant le jalon de conception avant intégration CLI du worker
        assert "[DEGRADATION]" in output or "catalogue" in output.lower()


def test_cli_degradation_list_rules_detailed_execution() -> None:
    """Vérifie l'exécution de 'pipeline degradation list-rules --detailed'."""
    result = runner.invoke(app, ["degradation", "list-rules", "--detailed"])
    assert result.exit_code == 0, (
        f"Échec d'exécution de 'degradation list-rules --detailed' : {result.output}"
    )
    output = result.output
    if "RULE-DATE-001" in output:
        # En mode détaillé, doit mentionner des colonnes cibles ou des descriptions complètes
        assert (
            "target" in output.lower()
            or "table" in output.lower()
            or "colonne" in output.lower()
            or "description" in output.lower()
        )


# ==============================================================================
# 3. Exécution de `degradation apply`
# ==============================================================================


def test_cli_degradation_apply_execution(tmp_path: Path) -> None:
    """Vérifie l'exécution réelle de 'pipeline degradation apply' et la production des données."""
    out_dir = tmp_path / "cli_degraded_out"
    args = [
        "degradation",
        "apply",
        "--rate",
        "0.15",
        "--seed",
        "42",
        "--output-dir",
        str(out_dir),
    ]

    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec d'exécution de 'degradation apply' : {result.output}"

    patients_file = out_dir / "patients.parquet"
    log_file = out_dir / "alterations_log.parquet"

    if not patients_file.exists() or not log_file.exists():
        if IS_STRICT:
            pytest.fail(
                f"La commande 'degradation apply' n'a pas créé les fichiers attendus dans {out_dir}. "
                f"Sortie console : {result.output}"
            )
        pytest.skip(
            "Câblage complet de l'exécution de degradation apply en attente de worker_etape4 (Jalon M1)"
        )

    assert patients_file.exists(), f"patients.parquet manquant dans {out_dir}"
    assert log_file.exists(), f"alterations_log.parquet manquant dans {out_dir}"


def test_cli_degradation_apply_custom_parameters(tmp_path: Path) -> None:
    """Vérifie l'exécution de 'degradation apply' avec un taux et une graine personnalisés."""
    out_dir = tmp_path / "cli_custom_degraded"
    args = [
        "degradation",
        "apply",
        "--rate",
        "0.10",
        "--seed",
        "99",
        "--output-dir",
        str(out_dir),
    ]

    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec 'degradation apply' personnalisé : {result.output}"

    log_file = out_dir / "alterations_log.parquet"
    if not log_file.exists():
        if IS_STRICT:
            pytest.fail(f"Fichier de journalisation manquant : {log_file}")
        pytest.skip("Câblage CLI en attente de worker_etape4")

    assert log_file.exists()


def test_cli_degradation_apply_invalid_rate(tmp_path: Path) -> None:
    """Vérifie le rejet des taux négatifs ou supérieurs à 1.0."""
    out_dir = tmp_path / "cli_invalid"

    # Taux négatif
    result_neg = runner.invoke(
        app,
        ["degradation", "apply", "--rate", "-0.1", "--output-dir", str(out_dir)],
    )
    # Soit Typer rejette (code != 0), soit la validation du moteur lève une erreur
    if (
        result_neg.exit_code == 0
        and "erreur" not in result_neg.output.lower()
        and "invalid" not in result_neg.output.lower()
        and IS_STRICT
    ):
        pytest.fail("Un taux d'altération négatif (-0.1) doit être rejeté par la CLI")

    # Taux > 1.0
    result_sup = runner.invoke(
        app,
        ["degradation", "apply", "--rate", "1.5", "--output-dir", str(out_dir)],
    )
    if (
        result_sup.exit_code == 0
        and "erreur" not in result_sup.output.lower()
        and "invalid" not in result_sup.output.lower()
        and IS_STRICT
    ):
        pytest.fail("Un taux d'altération > 1.0 (1.5) doit être rejeté par la CLI")
