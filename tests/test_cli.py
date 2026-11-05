"""Tests de validation automatisée de l'interface en ligne de commande (CLI) Typer (Étape 1).

Vérifie l'enregistrement des 12 groupes de sous-commandes de la roadmap,
les messages d'aide en français, les options D-06 (--use-openhim / --direct-hapi),
la commande de diagnostic d'environnement (env check) et l'absence de régression.
"""

from __future__ import annotations

import json
from typing import Final

import pytest
from typer.testing import CliRunner

from src.cli import app, collect_environment_diagnostics

runner = CliRunner()

# Liste canonique des 12 groupes de sous-commandes roadmap + 2 groupes diagnostic + 1 groupe référentiels
ROADMAP_GROUPS: Final[list[str]] = [
    "raw",
    "bronze",
    "silver",
    "matching",
    "canonical",
    "terminology",
    "reference",
    "ig",
    "fhir",
    "omop",
    "export-ai",
    "degradation",
    "generation",
    "env",
    "infra",
]

ALL_SUBCOMMANDS: Final[list[list[str]]] = [
    ["raw", "ingest"],
    ["raw", "status"],
    ["bronze", "convert"],
    ["bronze", "validate"],
    ["bronze", "profile"],
    ["silver", "clean"],
    ["silver", "validate"],
    ["silver", "report"],
    ["matching", "run"],
    ["matching", "audit"],
    ["canonical", "transform"],
    ["canonical", "validate"],
    ["terminology", "map"],
    ["terminology", "fetch-athena"],
    ["terminology", "export-conceptmaps"],
    ["terminology", "list-pathologies"],
    ["terminology", "validate-vocabularies"],
    ["terminology", "inspect-sample"],
    ["reference", "geography-summary"],
    ["reference", "list-regions"],
    ["reference", "validate-geography"],
    ["reference", "generate-geography"],
    ["ig", "build"],
    ["ig", "validate"],
    ["ig", "publish"],
    ["fhir", "generate"],
    ["fhir", "validate"],
    ["fhir", "load"],
    ["omop", "init"],
    ["omop", "transform"],
    ["omop", "dqd"],
    ["export-ai", "generate"],
    ["export-ai", "datasheet"],
    ["degradation", "apply"],
    ["degradation", "list-rules"],
    ["generation", "run"],
    ["generation", "dhis2-demo"],
    ["env", "check"],
    ["infra", "status"],
]


def test_cli_root_help() -> None:
    """Vérifie que l'invocation racine --help affiche l'aide principale en français."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, f"Erreur d'invocation racine: {result.output}"
    assert "pipeline" in result.output.lower() or "fhir" in result.output.lower()
    for group in ROADMAP_GROUPS:
        assert group in result.output, (
            f"Groupe de commande manquant dans l'aide principale: {group}"
        )


@pytest.mark.parametrize("group", ROADMAP_GROUPS)
def test_group_help_in_french(group: str) -> None:
    """Vérifie que chaque groupe dispose d'une aide en français valide."""
    result = runner.invoke(app, [group, "--help"])
    assert result.exit_code == 0, f"Échec de l'aide pour le sous-groupe '{group}':\n{result.output}"

    output = result.output.lower()
    french_indicators = [
        "étape",
        "données",
        "pipeline",
        "santé",
        "gestion",
        "génération",
        "export",
        "aide",
        "commande",
        "ingestion",
        "stockage",
        "nettoyage",
        "rapprochement",
        "transformation",
        "normalisation",
        "guide",
        "ressources",
        "entrepôt",
        "altérations",
        "diagnostic",
        "supervision",
    ]
    has_french = any(ind in output for ind in french_indicators)
    assert has_french, f"L'aide pour '{group}' ne semble pas rédigée en français:\n{result.output}"


@pytest.mark.parametrize("command", ALL_SUBCOMMANDS)
def test_subcommand_execution(command: list[str]) -> None:
    """Vérifie que chacune des sous-commandes s'exécute proprement avec code 0."""
    result = runner.invoke(app, command)
    assert result.exit_code == 0, f"Échec commande {' '.join(command)} : {result.stdout}"


def test_fhir_load_architectural_options_d06() -> None:
    """Vérifie le respect de la Décision D-06 pour l'étape fhir load."""
    result_load_help = runner.invoke(app, ["fhir", "load", "--help"])
    assert result_load_help.exit_code == 0
    assert "--use-openhim" in result_load_help.output
    assert "--direct-hapi" in result_load_help.output

    # Défaut : OpenHIM
    res_default = runner.invoke(app, ["fhir", "load"])
    assert res_default.exit_code == 0
    assert "OpenHIM" in res_default.stdout

    # Option explicite direct HAPI
    res_direct = runner.invoke(app, ["fhir", "load", "--direct-hapi"])
    assert res_direct.exit_code == 0
    assert "Direct HAPI" in res_direct.stdout

    # Option explicite OpenHIM
    res_openhim = runner.invoke(app, ["fhir", "load", "--use-openhim"])
    assert res_openhim.exit_code == 0
    assert "OpenHIM" in res_openhim.stdout


def test_env_check_human_output() -> None:
    """Vérifie la commande de diagnostic env check avec affichage tableau Rich."""
    result = runner.invoke(app, ["env", "check"])
    assert result.exit_code == 0, f"Échec env check: {result.output}"
    assert "Python" in result.stdout
    assert "3.11" in result.stdout
    assert "uv" in result.stdout
    assert "Docker" in result.stdout


def test_env_check_json_output() -> None:
    """Vérifie la commande de diagnostic env check au format JSON."""
    result = runner.invoke(app, ["env", "check", "--json"])
    assert result.exit_code == 0, f"Échec env check --json: {result.output}"
    data = json.loads(result.stdout)
    assert "python" in data
    assert "uv" in data
    assert "docker_cli" in data
    assert "docker_daemon" in data
    assert "services" in data
    assert data["python"]["is_supported"] is True


def test_collect_environment_diagnostics_function() -> None:
    """Vérifie unitairement la fonction de collecte des diagnostics."""
    diag = collect_environment_diagnostics()
    assert isinstance(diag, dict)
    assert diag["python"]["version"].startswith("3.")
    assert "executable" in diag["python"]


def test_cli_error_on_unknown_command() -> None:
    """Vérifie le code de retour d'erreur (exit code 2) sur commande inconnue."""
    result = runner.invoke(app, ["unknown-stage-xyz"])
    assert result.exit_code != 0


def test_cli_error_on_invalid_argument_type() -> None:
    """Vérifie le rejet par Typer d'un type d'argument invalide."""
    result = runner.invoke(app, ["generation", "run", "--count", "pas-un-nombre"])
    assert result.exit_code != 0
