"""Module de génération de la population de référence parfaite (Vérité Terrain) et agrégats DHIS2.

Génère des parcours de soins réalistes (Voie B contextuelle, ADR D-04) selon les
distributions sanitaires et épidémiologiques du Togo avec graine fixe, ainsi que les
agrégats mensuels DHIS2 dataValueSets.
"""

from src.generation.contextual_generator import generate_ground_truth
from src.generation.dhis2_generator import extract_or_generate_dhis2_aggregates

__all__ = [
    "extract_or_generate_dhis2_aggregates",
    "generate_ground_truth",
]
