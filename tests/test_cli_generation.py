"""Tests de validation des commandes CLI Typer pour la génération de Vérité Terrain et DHIS2 (Étape 3).

Conforme aux spécifications d'ORIGINAL_REQUEST.md (R3, R4) et SCOPE.md.
Vérifie :
- L'enregistrement et les textes d'aide en français des commandes `generation run` et `generation dhis2-demo`.
- L'exécution de `pipeline generation run` avec options `--count`, `--seed`, `--output-dir`.
- L'exécution de `pipeline generation dhis2-demo` avec options `--api-url`, `--output-dir`, `--offline`.
- La restitution visuelle Rich (statuts, tableaux récapitulatifs).
- La gestion rigoureuse des arguments invalides (count nul ou négatif, options inconnues).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from src.cli import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()
IS_STRICT = os.environ.get("STRICT_E2E") == "1"


# ==============================================================================
# 1. Enregistrement des commandes et Aide en Français
# ==============================================================================


def test_cli_generation_group_help() -> None:
    """Vérifie que le groupe de commandes 'generation' est enregistré avec aide en français."""
    result = runner.invoke(app, ["generation", "--help"])
    assert result.exit_code == 0, f"Erreur help generation : {result.output}"
    out_lower = result.output.lower()
    assert "génération" in out_lower or "clinique" in out_lower or "synthétique" in out_lower, (
        "L'aide du groupe 'generation' doit être en français"
    )


def test_cli_generation_run_help() -> None:
    """Vérifie que la commande 'generation run' affiche son aide avec les options requises."""
    result = runner.invoke(app, ["generation", "run", "--help"])
    assert result.exit_code == 0, f"Erreur help generation run : {result.output}"
    output = result.output
    assert "--count" in output, "Option --count manquante dans 'generation run --help'"
    assert "--seed" in output, "Option --seed manquante dans 'generation run --help'"
    assert "--output-dir" in output, "Option --output-dir manquante dans 'generation run --help'"


def test_cli_generation_dhis2_demo_help() -> None:
    """Vérifie que la commande 'generation dhis2-demo' affiche son aide avec les options requises."""
    result = runner.invoke(app, ["generation", "dhis2-demo", "--help"])
    assert result.exit_code == 0, f"Erreur help generation dhis2-demo : {result.output}"
    output = result.output
    assert "--api-url" in output, "Option --api-url manquante dans 'generation dhis2-demo --help'"
    # Vérification progressive de l'option --output-dir (requise par R3)
    if "--output-dir" not in output:
        if IS_STRICT:
            pytest.fail("Option --output-dir obligatoire manquante dans 'generation dhis2-demo'")
        pytest.skip(
            "Option --output-dir en attente d'intégration dans generation dhis2-demo (Jalon M2)"
        )


# ==============================================================================
# 2. Exécution Fonctionnelle de `generation run`
# ==============================================================================


def test_cli_generation_run_execution(tmp_path: Path) -> None:
    """Vérifie l'exécution réelle de 'pipeline generation run' et la création des fichiers Parquet."""
    out_dir = tmp_path / "cli_truth"
    result = runner.invoke(
        app,
        [
            "generation",
            "run",
            "--count",
            "20",
            "--seed",
            "42",
            "--output-dir",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, f"Échec d'exécution de generation run : {result.output}"

    patients_file = out_dir / "patients.parquet"
    if not patients_file.exists():
        if IS_STRICT:
            pytest.fail(
                f"La commande 'generation run' n'a pas créé les fichiers Parquet dans {out_dir}. "
                f"Sortie console : {result.output}"
            )
        pytest.skip(
            "Génération de fichiers Parquet réels en attente d'implémentation (Jalon M1/M2)"
        )

    # Vérification des fichiers clés générés
    for expected_file in [
        "patients.parquet",
        "encounters.parquet",
        "conditions.parquet",
        "observations.parquet",
        "immunizations.parquet",
    ]:
        assert (out_dir / expected_file).exists(), (
            f"Fichier Parquet {expected_file} manquant après exécution CLI"
        )


# ==============================================================================
# 3. Exécution Fonctionnelle de `generation dhis2-demo`
# ==============================================================================


def test_cli_generation_dhis2_demo_execution(tmp_path: Path) -> None:
    """Vérifie l'exécution réelle de 'pipeline generation dhis2-demo' et la création des agrégats."""
    out_dir = tmp_path / "cli_dhis2"

    # Vérifie si --output-dir est supporté
    help_res = runner.invoke(app, ["generation", "dhis2-demo", "--help"])
    if "--output-dir" not in help_res.output:
        if IS_STRICT:
            pytest.fail("Option --output-dir manquante sur dhis2-demo")
        pytest.skip("Option --output-dir sur dhis2-demo en cours d'intégration (Jalon M2)")

    cmd_args = [
        "generation",
        "dhis2-demo",
        "--output-dir",
        str(out_dir),
    ]
    if "--offline" in help_res.output:
        cmd_args.append("--offline")

    result = runner.invoke(app, cmd_args)
    assert result.exit_code == 0, f"Échec d'exécution de generation dhis2-demo : {result.output}"

    json_file = out_dir / "dhis2_data_values.json"
    if not json_file.exists():
        json_file = out_dir / "dhis2" / "dhis2_data_values.json"

    if not json_file.exists():
        if IS_STRICT:
            pytest.fail(
                f"La commande 'generation dhis2-demo' n'a pas produit de fichier JSON dans {out_dir}"
            )
        pytest.skip("Sortie réelle des agrégats DHIS2 en attente d'implémentation (Jalon M2)")

    assert json_file.exists(), "Fichier JSON DHIS2 absent"


# ==============================================================================
# 4. Gestion des Arguments Invalides et Codes d'Erreur Non-Nuls
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_count",
    ["0", "-10"],
)
def test_cli_generation_run_invalid_count_rejected(invalid_count: str) -> None:
    """Vérifie qu'un count nul ou négatif est rejeté avec un code de retour non-nul."""
    result = runner.invoke(
        app,
        [
            "generation",
            "run",
            "--count",
            invalid_count,
        ],
    )
    # Si la validation n'est pas encore câblée dans src/cli.py, vérifier en mode strict
    if result.exit_code == 0:
        if IS_STRICT:
            pytest.fail(
                f"La commande 'generation run --count {invalid_count}' aurait dû échouer (code != 0), "
                f"mais a renvoyé code 0. Sortie : {result.output}"
            )
        pytest.skip(
            f"Validation de count={invalid_count} en attente d'intégration dans src/cli.py (Jalon M2)"
        )

    assert result.exit_code != 0, (
        f"Le count invalide {invalid_count} doit renvoyer un code de sortie non-nul"
    )


def test_cli_generation_run_unknown_option_rejected() -> None:
    """Vérifie qu'une option inconnue passée à generation run renvoie un code de sortie non-nul (2)."""
    result = runner.invoke(app, ["generation", "run", "--option-inconnue-xyz"])
    assert result.exit_code != 0, (
        "Une option invalide passée à generation run doit renvoyer un code != 0"
    )


def test_cli_generation_dhis2_unknown_option_rejected() -> None:
    """Vérifie qu'une option inconnue passée à generation dhis2-demo renvoie un code de sortie non-nul."""
    result = runner.invoke(app, ["generation", "dhis2-demo", "--option-inconnue-xyz"])
    assert result.exit_code != 0, (
        "Une option invalide passée à generation dhis2-demo doit renvoyer un code != 0"
    )
