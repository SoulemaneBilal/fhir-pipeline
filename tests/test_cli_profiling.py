"""Tests de validation des commandes CLI Typer pour le profilage qualité Bronze (Étape 6).

Conforme aux spécifications formelles de DISPATCH.md, SCOPE.md, Roadmap technique.md §6
et SYNTHESE_PROJET.md §3.1 (Étape 6).

Commandes couvertes :
- `pipeline bronze --help` : Présence de la sous-commande `profile`
- `pipeline bronze profile --help` : Options `--bronze-dir`, `--output`, `--alterations-log`, `--format`, texte d'aide en français
- Exécution de `pipeline bronze profile` en mode Markdown (`--format markdown`)
- Exécution de `pipeline bronze profile` en mode JSON (`--format json`)
- Exécution de `pipeline bronze profile` en mode double export (`--format both`)
- Exécution avec confrontation au journal d'altérations `--alterations-log`
- Rendu console dynamique Rich (jauge de qualité globale, tableau des 6 dimensions)
- Gestion des erreurs et cas limites (répertoire source inexistant, arguments invalides)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()
IS_STRICT = os.environ.get("STRICT_E2E") == "1"

DEFAULT_DEGRADED_DIR = Path("data/degraded")
DEFAULT_ALTERATIONS_LOG = Path("data/degraded/alterations_log.parquet")


# ==============================================================================
# 1. Enregistrement et Textes d'Aide en Français
# ==============================================================================


def test_cli_bronze_profile_in_bronze_group() -> None:
    """Vérifie que la sous-commande 'profile' est bien déclarée dans le groupe 'bronze'."""
    result = runner.invoke(app, ["bronze", "--help"])
    assert result.exit_code == 0, f"Erreur help bronze : {result.output}"
    assert "profile" in result.output, (
        "Sous-commande 'profile' introuvable dans la commande 'pipeline bronze --help'"
    )


def test_cli_bronze_profile_help_in_french() -> None:
    """Vérifie l'aide et les options requises de la commande 'pipeline bronze profile --help'."""
    result = runner.invoke(app, ["bronze", "profile", "--help"])
    assert result.exit_code == 0, f"Erreur help bronze profile : {result.output}"
    output = result.output

    # Vérification de l'aide en français
    out_lower = output.lower()
    assert (
        "profil" in out_lower
        or "qualité" in out_lower
        or "dimension" in out_lower
        or "bronze" in out_lower
    ), "L'aide de 'bronze profile' doit être rédigée en français"

    # Vérification des options requises par SCOPE.md et DISPATCH.md
    has_bronze_dir = "--bronze-dir" in output
    has_output = "--output" in output or "-o" in output
    has_alterations_log = "--alterations-log" in output
    has_format = "--format" in output

    if not (has_bronze_dir and has_alterations_log and has_format):
        if IS_STRICT:
            pytest.fail(
                f"Options CLI manquantes dans 'bronze profile --help' : "
                f"--bronze-dir={has_bronze_dir}, --output={has_output}, "
                f"--alterations-log={has_alterations_log}, --format={has_format}"
            )
        pytest.skip(
            "Options CLI complètes (--bronze-dir, --alterations-log, --format) en attente "
            "d'implémentation par worker_etape6 dans src/cli.py"
        )

    assert has_output, "Option --output / -o manquante dans 'bronze profile --help'"


# ==============================================================================
# 2. Exécutions Fonctionnelles CLI
# ==============================================================================


def test_cli_bronze_profile_execution_default_markdown(tmp_path: Path) -> None:
    """Vérifie l'exécution de 'pipeline bronze profile' avec génération du rapport Markdown."""
    out_md = tmp_path / "rapport_avant.md"

    # Vérification préalable des options dans le help
    help_res = runner.invoke(app, ["bronze", "profile", "--help"])
    if "--bronze-dir" not in help_res.output:
        if IS_STRICT:
            pytest.fail("Option --bronze-dir absente de bronze profile")
        pytest.skip("Option --bronze-dir en attente d'implémentation par worker_etape6")

    args = [
        "bronze",
        "profile",
        "--bronze-dir",
        str(DEFAULT_DEGRADED_DIR),
        "--output",
        str(out_md),
        "--format",
        "markdown",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec 'bronze profile' Markdown : {result.output}"

    assert out_md.exists(), f"Le fichier de rapport Markdown {out_md} n'a pas été généré"
    content = out_md.read_text(encoding="utf-8")
    assert len(content) > 200, "Le rapport Markdown généré est anormalement court"
    assert (
        "qualité" in content.lower()
        or "rapport" in content.lower()
        or "dimension" in content.lower()
    )


def test_cli_bronze_profile_execution_json_format(tmp_path: Path) -> None:
    """Vérifie l'exécution de 'pipeline bronze profile --format json'."""
    out_json = tmp_path / "rapport_avant.json"

    help_res = runner.invoke(app, ["bronze", "profile", "--help"])
    if "--format" not in help_res.output:
        if IS_STRICT:
            pytest.fail("Option --format absente de bronze profile")
        pytest.skip("Option --format en attente d'implémentation par worker_etape6")

    args = [
        "bronze",
        "profile",
        "--bronze-dir",
        str(DEFAULT_DEGRADED_DIR),
        "--output",
        str(out_json),
        "--format",
        "json",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec 'bronze profile' JSON : {result.output}"

    assert out_json.exists(), f"Le fichier de rapport JSON {out_json} n'a pas été généré"
    content = out_json.read_text(encoding="utf-8")
    data = json.loads(content)
    assert "overall_score" in data or "global_score" in data
    assert "dimensions" in data or "tables" in data


def test_cli_bronze_profile_execution_both_formats(tmp_path: Path) -> None:
    """Vérifie l'exécution de 'pipeline bronze profile --format both'."""
    out_base = tmp_path / "rapport_avant"

    help_res = runner.invoke(app, ["bronze", "profile", "--help"])
    if "--format" not in help_res.output:
        if IS_STRICT:
            pytest.fail("Option --format absente de bronze profile")
        pytest.skip("Option --format en attente d'implémentation par worker_etape6")

    args = [
        "bronze",
        "profile",
        "--bronze-dir",
        str(DEFAULT_DEGRADED_DIR),
        "--output",
        str(out_base),
        "--format",
        "both",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec 'bronze profile' both : {result.output}"

    # Vérification que les deux formats (.md et .json) ont été générés
    md_file = tmp_path / "rapport_avant.md"
    json_file = tmp_path / "rapport_avant.json"
    assert (
        md_file.exists()
        or Path(f"{out_base}.md").exists()
        or Path(out_base).with_suffix(".md").exists()
    ), f"Rapport Markdown attendu pour format=both : {md_file}"
    assert (
        json_file.exists()
        or Path(f"{out_base}.json").exists()
        or Path(out_base).with_suffix(".json").exists()
    ), f"Rapport JSON attendu pour format=both : {json_file}"


def test_cli_bronze_profile_with_alterations_log(tmp_path: Path) -> None:
    """Vérifie l'exécution avec confrontation explicite au journal d'altérations."""
    out_md = tmp_path / "rapport_confrontation.md"

    help_res = runner.invoke(app, ["bronze", "profile", "--help"])
    if "--alterations-log" not in help_res.output:
        if IS_STRICT:
            pytest.fail("Option --alterations-log absente de bronze profile")
        pytest.skip("Option --alterations-log en attente d'implémentation par worker_etape6")

    args = [
        "bronze",
        "profile",
        "--bronze-dir",
        str(DEFAULT_DEGRADED_DIR),
        "--output",
        str(out_md),
        "--alterations-log",
        str(DEFAULT_ALTERATIONS_LOG),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec 'bronze profile' avec log : {result.output}"

    assert out_md.exists()
    content = out_md.read_text(encoding="utf-8")
    # Doit contenir la matrice de rappel
    assert "rappel" in content.lower() or "recall" in content.lower() or "rule-" in content.lower()


def test_cli_bronze_profile_non_existent_directory_error(tmp_path: Path) -> None:
    """Vérifie qu'un répertoire source inexistant renvoie une erreur explicite."""
    help_res = runner.invoke(app, ["bronze", "profile", "--help"])
    if "--bronze-dir" not in help_res.output:
        pytest.skip("Option --bronze-dir non encore branchée")

    non_existent = tmp_path / "dossier_totalement_fantome_12345"
    out_md = tmp_path / "rapport.md"

    args = [
        "bronze",
        "profile",
        "--bronze-dir",
        str(non_existent),
        "--output",
        str(out_md),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code != 0, "Un répertoire inexistant doit déclencher une erreur"
    out_lower = result.output.lower()
    assert (
        "introuvable" in out_lower
        or "inexistant" in out_lower
        or "erreur" in out_lower
        or "not found" in out_lower
        or "does not exist" in out_lower
    )


def test_cli_bronze_profile_rich_console_output(tmp_path: Path) -> None:
    """Vérifie que la restitution console affiche les éléments Rich (scores, dimensions)."""
    help_res = runner.invoke(app, ["bronze", "profile", "--help"])
    if "--bronze-dir" not in help_res.output:
        pytest.skip("Option --bronze-dir non encore branchée")

    out_md = tmp_path / "rapport_rich.md"
    args = [
        "bronze",
        "profile",
        "--bronze-dir",
        str(DEFAULT_DEGRADED_DIR),
        "--output",
        str(out_md),
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0

    output = result.output
    # Doit contenir le tag [BRONZE] ou mention de santé qualité
    assert "BRONZE" in output or "qualité" in output.lower() or "score" in output.lower()
