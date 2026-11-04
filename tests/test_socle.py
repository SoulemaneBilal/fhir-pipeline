"""Tests de validation du socle technique de l'Étape 0."""

import sys
from pathlib import Path

import src
from src import (
    canonical_model,
    cleaning,
    degradation,
    export_ai,
    fhir_transform,
    generation,
    ig,
    ingestion,
    loading,
    matching,
    omop_etl,
    profiling,
    terminology,
    validation,
)


def test_python_version_is_3_11() -> None:
    """Vérifie que l'interpréteur Python est bien sous la branche 3.11."""
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 11


def test_package_metadata() -> None:
    """Vérifie que le package racine src expose sa version."""
    assert src.__version__ == "0.1.0"


def test_subpackages_importable() -> None:
    """Vérifie que l'ensemble des 14 sous-paquets sont importables."""
    subpackages = [
        canonical_model,
        cleaning,
        degradation,
        export_ai,
        fhir_transform,
        generation,
        ig,
        ingestion,
        loading,
        matching,
        omop_etl,
        profiling,
        terminology,
        validation,
    ]
    for pkg in subpackages:
        assert pkg.__doc__ is not None
        assert len(pkg.__doc__) > 0


def test_project_root_fixture(project_root: Path) -> None:
    """Vérifie le bon fonctionnement de la fixture project_root."""
    assert project_root.exists()
    assert (project_root / "pyproject.toml").exists()
