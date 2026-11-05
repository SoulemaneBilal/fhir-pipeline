#!/usr/bin/env bash
# ==============================================================================
# Script d'initialisation multi-base pour PostgreSQL 15 (Docker)
# Crée automatiquement les bases hapi_fhir et omop_cdm (Décision D-05)
# et configure les schémas cdm54 et vocab requis par OHDSI OMOP CDM 5.4.
# ==============================================================================
set -euo pipefail

echo "==> [Postgres Init] Initialisation des bases de données multiples..."

ADMIN_USER="${POSTGRES_USER:-pipeline_admin}"
DEFAULT_DBS="hapi_fhir,omop_cdm"
DBS_TO_CREATE="${POSTGRES_MULTIPLE_DATABASES:-$DEFAULT_DBS}"

create_database() {
    local db="$1"
    echo "--> [Postgres Init] Vérification de l'existence de la base '$db'..."
    local db_exists
    db_exists=$(psql -v ON_ERROR_STOP=1 --username "$ADMIN_USER" --dbname "postgres" -tc "SELECT 1 FROM pg_database WHERE datname = '$db'" | tr -d '[:space:]')
    if [ "$db_exists" = "1" ]; then
        echo "--> [Postgres Init] La base de données '$db' existe déjà."
    else
        echo "--> [Postgres Init] Création de la base '$db' (propriétaire: '$ADMIN_USER')..."
        psql -v ON_ERROR_STOP=1 --username "$ADMIN_USER" --dbname "postgres" -c "CREATE DATABASE \"$db\" OWNER \"$ADMIN_USER\";"
        psql -v ON_ERROR_STOP=1 --username "$ADMIN_USER" --dbname "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE \"$db\" TO \"$ADMIN_USER\";"
        echo "--> [Postgres Init] Base '$db' créée avec succès."
    fi
}

# Découpage de la liste séparée par des virgules
IFS=',' read -ra DB_ARRAY <<< "$DBS_TO_CREATE"
for db in "${DB_ARRAY[@]}"; do
    db="$(echo "$db" | xargs)"
    if [ -n "$db" ]; then
        create_database "$db"
    fi
done

# Initialisation des schémas requis par OMOP CDM 5.4 (D-05)
OMOP_DATABASE="${OMOP_DB:-omop_cdm}"
echo "--> [Postgres Init] Configuration des schémas OHDSI dans '$OMOP_DATABASE'..."
psql -v ON_ERROR_STOP=1 --username "$ADMIN_USER" --dbname "$OMOP_DATABASE" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS cdm54 AUTHORIZATION "$ADMIN_USER";
    CREATE SCHEMA IF NOT EXISTS vocab AUTHORIZATION "$ADMIN_USER";
    GRANT ALL ON SCHEMA cdm54 TO "$ADMIN_USER";
    GRANT ALL ON SCHEMA vocab TO "$ADMIN_USER";
EOSQL

echo "==> [Postgres Init] Initialisation multi-base terminée avec succès."
