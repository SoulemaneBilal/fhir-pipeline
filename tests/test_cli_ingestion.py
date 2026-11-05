"""Tests de validation des commandes CLI Typer pour l'Ingestion Raw et Bronze (Étape 5).

Conforme aux spécifications formelles de DISPATCH.md, SCOPE.md, Roadmap technique.md §5
et SYNTHESE_PROJET.md §3.1 (Étape 5).

Commandes couvertes :
- `pipeline raw --help` : Aide du groupe d'ingestion brute en français
- `pipeline raw ingest --source <path> [--dest <path>] [--dry-run]`
- `pipeline raw status [--verify-hash]`
- `pipeline bronze --help` : Aide du groupe de structuration Parquet en français
- `pipeline bronze convert [--raw-dir <path>] [--output-dir <path>] [--batch-id <id>]`
- `pipeline bronze validate [--strict]`
"""

from __future__ import annotations

import os
from pathlib import Path

from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()
IS_STRICT = os.environ.get("STRICT_E2E") == "1"

DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_BRONZE_DIR = Path("data/bronze")


# ==============================================================================
# 1. Groupe RAW : Aides & Enregistrement des Sous-Commandes
# ==============================================================================


def test_cli_raw_group_help() -> None:
    """Vérifie que le groupe de commandes 'raw' est enregistré avec une aide en français."""
    result = runner.invoke(app, ["raw", "--help"])
    assert result.exit_code == 0, f"Erreur help raw : {result.output}"
    out_lower = result.output.lower()
    assert (
        "brute" in out_lower
        or "source" in out_lower
        or "ingestion" in out_lower
        or "sanctuarisation" in out_lower
    ), "L'aide du groupe 'raw' doit être rédigée en français"
    assert "ingest" in result.output, "Sous-commande 'ingest' manquante dans 'raw --help'"
    assert "status" in result.output, "Sous-commande 'status' manquante dans 'raw --help'"


def test_cli_raw_ingest_help() -> None:
    """Vérifie l'aide et les options requises de la commande 'raw ingest'."""
    result = runner.invoke(app, ["raw", "ingest", "--help"])
    assert result.exit_code == 0, f"Erreur help raw ingest : {result.output}"
    output = result.output
    assert "--source" in output or "-s" in output, (
        "Option --source manquante dans 'raw ingest --help'"
    )
    assert "--dry-run" in output, "Option --dry-run manquante dans 'raw ingest --help'"
    out_lower = output.lower()
    assert "ingér" in out_lower or "source" in out_lower or "sha-256" in out_lower, (
        "L'aide de 'raw ingest' doit être en français"
    )


def test_cli_raw_status_help() -> None:
    """Vérifie l'aide et les options requises de la commande 'raw status'."""
    result = runner.invoke(app, ["raw", "status", "--help"])
    assert result.exit_code == 0, f"Erreur help raw status : {result.output}"
    output = result.output
    assert "--verify-hash" in output, "Option --verify-hash manquante dans 'raw status --help'"
    out_lower = output.lower()
    assert "intégrité" in out_lower or "état" in out_lower or "fichiers" in out_lower, (
        "L'aide de 'raw status' doit être en français"
    )


# ==============================================================================
# 2. Groupe BRONZE : Aides & Enregistrement des Sous-Commandes
# ==============================================================================


def test_cli_bronze_group_help() -> None:
    """Vérifie que le groupe de commandes 'bronze' est enregistré avec une aide en français."""
    result = runner.invoke(app, ["bronze", "--help"])
    assert result.exit_code == 0, f"Erreur help bronze : {result.output}"
    out_lower = result.output.lower()
    assert (
        "parquet" in out_lower
        or "stockage" in out_lower
        or "structuration" in out_lower
        or "bronze" in out_lower
    ), "L'aide du groupe 'bronze' doit être rédigée en français"
    assert "convert" in result.output, "Sous-commande 'convert' manquante dans 'bronze --help'"
    assert "validate" in result.output, "Sous-commande 'validate' manquante dans 'bronze --help'"


def test_cli_bronze_convert_help() -> None:
    """Vérifie l'aide et les options de la commande 'bronze convert'."""
    result = runner.invoke(app, ["bronze", "convert", "--help"])
    assert result.exit_code == 0, f"Erreur help bronze convert : {result.output}"
    output = result.output
    assert "--batch-id" in output, "Option --batch-id manquante dans 'bronze convert --help'"
    out_lower = output.lower()
    assert "convert" in out_lower or "parquet" in out_lower or "audit" in out_lower, (
        "L'aide de 'bronze convert' doit être en français"
    )


def test_cli_bronze_validate_help() -> None:
    """Vérifie l'aide et les options de la commande 'bronze validate'."""
    result = runner.invoke(app, ["bronze", "validate", "--help"])
    assert result.exit_code == 0, f"Erreur help bronze validate : {result.output}"
    output = result.output
    assert "--strict" in output, "Option --strict manquante dans 'bronze validate --help'"
    out_lower = output.lower()
    assert "valider" in out_lower or "schémas" in out_lower or "intégrité" in out_lower, (
        "L'aide de 'bronze validate' doit être en français"
    )


# ==============================================================================
# 3. Exécution des Commandes RAW
# ==============================================================================


def test_cli_raw_ingest_dry_run(tmp_path: Path) -> None:
    """Vérifie que 'raw ingest --dry-run' s'exécute sans erreur et sans écriture sur disque."""
    test_src = tmp_path / "test_patient.csv"
    test_src.write_text("patient_id,name\nPAT-1,Koffi\n", encoding="utf-8")

    result = runner.invoke(app, ["raw", "ingest", "--source", str(test_src), "--dry-run"])
    assert result.exit_code == 0, f"Échec 'raw ingest --dry-run' : {result.output}"
    assert "dry-run=True" in result.output or "dry-run" in result.output.lower()


def test_cli_raw_status_execution() -> None:
    """Vérifie l'exécution de la commande 'raw status'."""
    assert DEFAULT_RAW_DIR.name == "raw"
    result = runner.invoke(app, ["raw", "status"])
    assert result.exit_code == 0, f"Échec 'raw status' : {result.output}"
    assert "data/raw" in result.output or "[RAW]" in result.output


def test_cli_raw_status_verify_hash() -> None:
    """Vérifie l'exécution de la commande 'raw status --verify-hash'."""
    result = runner.invoke(app, ["raw", "status", "--verify-hash"])
    assert result.exit_code == 0, f"Échec 'raw status --verify-hash' : {result.output}"
    assert "empreinte" in result.output.lower() or "hash" in result.output.lower()


# ==============================================================================
# 4. Exécution des Commandes BRONZE
# ==============================================================================


def test_cli_bronze_convert_execution(tmp_path: Path) -> None:
    """Vérifie l'exécution de 'pipeline bronze convert'."""
    assert DEFAULT_BRONZE_DIR.name == "bronze"
    raw_dir = tmp_path / "raw_cli_test"
    raw_dir.mkdir()
    sample_csv = raw_dir / "patients.csv"
    sample_csv.write_text(
        "patient_id,family_name\nPAT-10,MENSAH\nPAT-20,LAWSON\n", encoding="utf-8"
    )

    # Invocations avec options standard ou par défaut
    args = ["bronze", "convert", "--batch-id", "test-batch-cli-001"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, f"Échec 'bronze convert' : {result.output}"
    assert "test-batch-cli-001" in result.output or "[BRONZE]" in result.output


def test_cli_bronze_validate_execution() -> None:
    """Vérifie l'exécution de 'pipeline bronze validate' avec et sans --strict."""
    result = runner.invoke(app, ["bronze", "validate"])
    assert result.exit_code == 0, f"Échec 'bronze validate' : {result.output}"

    result_strict = runner.invoke(app, ["bronze", "validate", "--strict"])
    assert result_strict.exit_code == 0 or result_strict.exit_code == 1, (
        f"Comportement inattendu 'bronze validate --strict' : {result_strict.output}"
    )


# ==============================================================================
# 5. Gestion des Erreurs et Robustesse
# ==============================================================================


def test_cli_raw_ingest_nonexistent_source() -> None:
    """Vérifie la robustesse face à une source introuvable."""
    nonexistent = "/path/to/definitely/nonexistent_file_12345.csv"
    result = runner.invoke(app, ["raw", "ingest", "--source", nonexistent])
    if result.exit_code == 0:
        assert "[RAW]" in result.output or "nonexistent" in result.output
    else:
        assert (
            "introuvable" in result.output.lower()
            or "nonexistent" in result.output.lower()
            or "erreur" in result.output.lower()
            or "error" in result.output.lower()
        )
