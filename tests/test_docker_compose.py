"""Tests de validation automatisée de la configuration Docker Compose (Étape 1).

Vérifie la conformité de l'orchestration Docker Compose pour l'Étape 1 :
- Présence et parsing YAML valide de docker-compose.yml.
- Déclaration obligatoire des services : postgres, hapi-fhir, mongodb, openhim-core, openhim-console.
- Configuration des doubles bases PostgreSQL (hapi_fhir, omop_cdm) et du script d'init.
- Configuration Distroless-compliant du healthcheck HAPI FHIR (java -cp /app HealthCheck).
- Gestion des dépendances (depends_on condition: service_healthy).
- Absence de collision sur les ports hôtes.
- Volumes nommés persistants.
- Validation statique via la commande CLI `docker compose config`.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def compose_path(project_root: Path) -> Path:
    """Fournit le chemin absolu du fichier docker-compose.yml."""
    path = project_root / "docker-compose.yml"
    assert path.exists(), f"Le fichier {path} doit exister à la racine du projet."
    return path


@pytest.fixture
def compose_data(compose_path: Path) -> dict[str, Any]:
    """Charge et parse le contenu YAML de docker-compose.yml."""
    content = compose_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "Le fichier docker-compose.yml doit être un dictionnaire YAML."
    return data


def test_compose_top_level_keys(compose_data: dict[str, Any]) -> None:
    """Vérifie la présence des sections maîtresses services, networks et volumes."""
    assert "services" in compose_data, "La section 'services' est requise."
    assert "volumes" in compose_data, "La section 'volumes' est requise."
    assert "networks" in compose_data, "La section 'networks' est requise."


def test_required_services_declared(compose_data: dict[str, Any]) -> None:
    """Vérifie que les 5 services requis pour l'Étape 1 sont déclarés."""
    services = compose_data.get("services", {})
    required = ["postgres", "hapi-fhir", "mongodb", "openhim-core", "openhim-console"]
    for svc in required:
        assert svc in services, f"Le service '{svc}' doit être déclaré dans docker-compose.yml."


def test_postgres_service_configuration(compose_data: dict[str, Any], project_root: Path) -> None:
    """Vérifie la configuration du service PostgreSQL (double base et init script)."""
    pg = compose_data["services"]["postgres"]
    assert "image" in pg and "postgres" in pg["image"]
    assert "healthcheck" in pg, "Postgres doit définir un healthcheck."
    healthcheck_cmd = " ".join(pg["healthcheck"].get("test", []))
    assert "pg_isready" in healthcheck_cmd, "Le healthcheck Postgres doit utiliser pg_isready."

    # Volumes & Script d'initialisation
    volumes = pg.get("volumes", [])
    has_init_script = any("init-multi-db.sh" in str(v) for v in volumes)
    assert has_init_script, "Postgres doit monter le script init-multi-db.sh."

    script_path = project_root / "docker" / "postgres" / "init-multi-db.sh"
    assert script_path.exists(), f"Le script {script_path} doit exister."
    assert os.access(script_path, os.X_OK), f"Le script {script_path} doit être exécutable."
    script_content = script_path.read_text(encoding="utf-8")
    assert "hapi_fhir" in script_content, "Le script d'init doit mentionner hapi_fhir."
    assert "omop_cdm" in script_content, "Le script d'init doit mentionner omop_cdm."
    assert "cdm54" in script_content, "Le script d'init doit configurer le schéma cdm54."
    assert "vocab" in script_content, "Le script d'init doit configurer le schéma vocab."

    # Ports
    ports = [str(p) for p in pg.get("ports", [])]
    assert any("5432" in p for p in ports), "Postgres doit exposer le port 5432."


def test_hapi_fhir_service_configuration(compose_data: dict[str, Any]) -> None:
    """Vérifie la configuration de HAPI FHIR JPA R4 (Distroless healthcheck et dépendances)."""
    hapi = compose_data["services"]["hapi-fhir"]
    assert "hapiproject/hapi" in hapi.get("image", "")

    # Dépendance envers postgres healthy
    depends_on = hapi.get("depends_on", {})
    assert "postgres" in depends_on, "HAPI FHIR doit dépendre de postgres."
    assert depends_on["postgres"].get("condition") == "service_healthy"

    # Healthcheck Java (Distroless compliant)
    healthcheck = hapi.get("healthcheck", {})
    test_cmd = healthcheck.get("test", [])
    cmd_str = " ".join(str(c) for c in test_cmd)
    assert "HealthCheck" in cmd_str, "HAPI FHIR (distroless) doit utiliser le HealthCheck Java."

    # Port hôte 8080
    ports = [str(p) for p in hapi.get("ports", [])]
    assert any("8080" in p for p in ports), "HAPI FHIR doit mapper le port hôte 8080."


def test_mongodb_service_configuration(compose_data: dict[str, Any]) -> None:
    """Vérifie la configuration du service MongoDB (backing store OpenHIM)."""
    mongo = compose_data["services"]["mongodb"]
    assert "mongo" in mongo.get("image", "")
    assert "healthcheck" in mongo, "MongoDB doit définir un healthcheck."
    cmd_str = " ".join(str(c) for c in mongo["healthcheck"].get("test", []))
    assert "ping" in cmd_str, "Le healthcheck MongoDB doit utiliser ping/adminCommand."

    # Port 27017
    ports = [str(p) for p in mongo.get("ports", [])]
    assert any("27017" in p for p in ports), "MongoDB doit exposer le port 27017."


def test_openhim_services_configuration(compose_data: dict[str, Any], project_root: Path) -> None:
    """Vérifie la configuration des services OpenHIM Core et Console."""
    services = compose_data["services"]
    core = services["openhim-core"]
    console = services["openhim-console"]

    # OpenHIM Core image & dependencies
    assert "jembi/openhim-core" in core.get("image", "")
    core_deps = core.get("depends_on", {})
    assert "mongodb" in core_deps, "OpenHIM Core doit dépendre de mongodb."
    assert "hapi-fhir" in core_deps, "OpenHIM Core doit dépendre de hapi-fhir."

    # OpenHIM Console image & dependencies
    assert "jembi/openhim-console" in console.get("image", "")
    console_deps = console.get("depends_on", {})
    assert "openhim-core" in console_deps, "OpenHIM Console doit dépendre de openhim-core."

    # Ports non en conflit avec HAPI FHIR
    core_ports = [str(p) for p in core.get("ports", [])]
    assert any("5001" in p for p in core_ports), (
        "OpenHIM Core API doit être mappé sur le port 5001."
    )

    # Console port 9000
    console_ports = [str(p) for p in console.get("ports", [])]
    assert any("9000" in p for p in console_ports), (
        "OpenHIM Console doit mapper le port 9000 vers 80."
    )

    # Configuration OpenHIM Console montée
    config_path = project_root / "docker" / "openhim" / "default.json"
    assert config_path.exists(), f"Le fichier {config_path} doit exister."


def test_docker_compose_volume_persistence(compose_data: dict[str, Any]) -> None:
    """Vérifie que des volumes nommés persistants sont déclarés au niveau racine."""
    volumes = compose_data.get("volumes", {})
    assert volumes is not None and len(volumes) >= 2, (
        "La section racine 'volumes' doit déclarer les volumes postgres_data et mongodb_data."
    )
    assert "postgres_data" in volumes, "Volume persistant postgres_data manquant."
    assert "mongodb_data" in volumes, "Volume persistant mongodb_data manquant."


def test_docker_compose_cli_validation(project_root: Path) -> None:
    """Valide syntaxiquement le fichier avec la commande docker compose config si docker est installé."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        pytest.skip("Docker CLI non présent sur le système hôte.")

    env_file = project_root / ".env.example"
    compose_file = project_root / "docker-compose.yml"
    cmd = [
        docker_bin,
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        str(compose_file),
        "config",
        "--quiet",
    ]

    result = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Échec de validation 'docker compose config' :\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    )
