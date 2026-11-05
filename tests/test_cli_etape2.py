"""Tests de validation automatisée des commandes CLI Typer d'Étape 2 (Référentiels & Vocabulaires).

Conforme aux spécifications R4 d'ORIGINAL_REQUEST.md et PROJECT.md.
Vérifie l'enregistrement et l'exécution des commandes :
- reference : geography-summary, list-regions, validate-geography, generate-geography
- terminology : list-pathologies, validate-vocabularies, inspect-sample
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()
IS_STRICT = os.environ.get("STRICT_E2E") == "1"

GEOGRAPHY_PARQUET_PATH = Path("data/reference/togo_health_geography.parquet")
VOCAB_PARQUET_PATH = Path("terminology/sample_vocabularies.parquet")


def _has_command(subcommand_path: list[str]) -> bool:
    """Vérifie si une sous-commande est enregistrée dans l'application Typer."""
    result = runner.invoke(app, [*subcommand_path, "--help"])
    return result.exit_code == 0


def _require_command(subcommand_path: list[str]) -> None:
    if not _has_command(subcommand_path):
        cmd_str = " ".join(subcommand_path)
        if IS_STRICT:
            pytest.fail(f"Commande CLI obligatoire manquante : {cmd_str}")
        pytest.skip(f"Commande CLI '{cmd_str}' non encore intégrée (Jalon M4 en attente)")


# ==============================================================================
# Tier 1 : Enregistrement des groupes et sous-commandes & Aide en Français
# ==============================================================================


def test_tier1_reference_group_registered() -> None:
    """Vérifie que le groupe de sous-commandes 'reference' est enregistré avec aide en français."""
    _require_command(["reference"])
    result = runner.invoke(app, ["reference", "--help"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "géograph" in output_lower or "référentiel" in output_lower or "santé" in output_lower, (
        "L'aide du groupe 'reference' doit être en français"
    )


@pytest.mark.parametrize(
    "cmd",
    [
        "geography-summary",
        "list-regions",
        "validate-geography",
        "generate-geography",
    ],
)
def test_tier1_reference_subcommands_help(cmd: str) -> None:
    """Vérifie que chaque sous-commande de 'reference' répond à --help en français."""
    # Tolère variantes de nommage (ex. inspect-geography pour geography-summary)
    candidates = [cmd]
    if cmd == "geography-summary":
        candidates.append("inspect-geography")

    active_cmd = None
    for c in candidates:
        if _has_command(["reference", c]):
            active_cmd = c
            break

    if not active_cmd:
        if IS_STRICT:
            pytest.fail(f"Sous-commande reference '{cmd}' manquante dans src/cli.py")
        pytest.skip(f"Sous-commande reference '{cmd}' non encore intégrée (Jalon M4 en attente)")

    result = runner.invoke(app, ["reference", active_cmd, "--help"])
    assert result.exit_code == 0
    assert len(result.output) > 20, f"Aide vide pour reference {active_cmd}"


@pytest.mark.parametrize(
    "cmd",
    [
        "list-pathologies",
        "validate-vocabularies",
        "inspect-sample",
    ],
)
def test_tier1_terminology_etape2_subcommands_help(cmd: str) -> None:
    """Vérifie les nouvelles sous-commandes de terminology pour l'Étape 2."""
    candidates = [cmd]
    if cmd == "inspect-sample":
        candidates.append("inspect-mock")

    active_cmd = None
    for c in candidates:
        if _has_command(["terminology", c]):
            active_cmd = c
            break

    if not active_cmd:
        if IS_STRICT:
            pytest.fail(f"Sous-commande terminology '{cmd}' manquante dans src/cli.py")
        pytest.skip(f"Sous-commande terminology '{cmd}' non encore intégrée (Jalon M4 en attente)")

    result = runner.invoke(app, ["terminology", active_cmd, "--help"])
    assert result.exit_code == 0
    assert len(result.output) > 20, f"Aide vide pour terminology {active_cmd}"


# ==============================================================================
# Tier 2 & 3 : Exécution Fonctionnelle avec Référentiels Présents
# ==============================================================================


def test_tier2_cli_list_regions_execution() -> None:
    """Vérifie l'exécution de 'reference list-regions' et l'affichage des 6 régions."""
    _require_command(["reference", "list-regions"])
    result = runner.invoke(app, ["reference", "list-regions"])
    assert result.exit_code == 0, f"Erreur d'exécution: {result.output}"

    # Vérifie la présence des 6 régions dans la sortie console
    for reg in [
        "Savanes",
        "Kara",
        "Centrale",
        "Plateaux",
        "Maritime",
        "Grand Lomé",
    ]:
        assert reg.lower() in result.output.lower(), (
            f"Région {reg} absente de la sortie de list-regions"
        )


def test_tier2_cli_validate_geography_execution() -> None:
    """Vérifie l'exécution de 'reference validate-geography'."""
    _require_command(["reference", "validate-geography"])
    if not GEOGRAPHY_PARQUET_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Fichier Parquet {GEOGRAPHY_PARQUET_PATH} absent pour test CLI")
        pytest.skip(f"{GEOGRAPHY_PARQUET_PATH} absent, impossible d'exécuter la validation CLI")

    result = runner.invoke(app, ["reference", "validate-geography"])
    assert result.exit_code == 0, f"Validation géographique échouée: {result.output}"


def test_tier2_cli_list_pathologies_execution() -> None:
    """Vérifie l'exécution de 'terminology list-pathologies'."""
    _require_command(["terminology", "list-pathologies"])
    result = runner.invoke(app, ["terminology", "list-pathologies"])
    assert result.exit_code == 0, f"Erreur d'exécution: {result.output}"

    # Vérifie la présence de pathologies prioritaires
    for pathol in ["Paludisme", "Malaria", "HTA", "Diab"]:
        assert pathol.lower() in result.output.lower() or "b50" in result.output.lower(), (
            f"Élément clinique '{pathol}' absent de la sortie list-pathologies"
        )


def test_tier2_cli_validate_vocabularies_execution() -> None:
    """Vérifie l'exécution de 'terminology validate-vocabularies'."""
    _require_command(["terminology", "validate-vocabularies"])
    if not VOCAB_PARQUET_PATH.exists():
        if IS_STRICT:
            pytest.fail(f"Fichier Parquet {VOCAB_PARQUET_PATH} absent pour test CLI")
        pytest.skip(
            f"{VOCAB_PARQUET_PATH} absent, impossible d'exécuter la validation vocabulaires CLI"
        )

    result = runner.invoke(app, ["terminology", "validate-vocabularies"])
    assert result.exit_code == 0, f"Validation vocabulaires échouée: {result.output}"


# ==============================================================================
# Tier 4 : Robustesse et Gestion des Arguments Invalides
# ==============================================================================


def test_tier4_cli_invalid_options_handling() -> None:
    """Vérifie que les options inconnues renvoient un code d'erreur non nul."""
    if _has_command(["reference"]):
        res = runner.invoke(app, ["reference", "--invalid-option-xyz"])
        assert res.exit_code != 0
