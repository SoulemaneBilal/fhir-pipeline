"""Fixtures Pytest partagées pour la suite de tests."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Renvoie le chemin racine absolu du projet."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_seed() -> int:
    """Graine pseudo-aléatoire fixe pour les tests de déterminisme."""
    return 42
