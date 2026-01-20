#!/bin/bash
# Create Grafana database for Grafana's internal storage
# This runs before init.sql because it's named 00-*

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create grafana database if it doesn't exist
    SELECT 'CREATE DATABASE grafana'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'grafana')\gexec

    -- Grant access to wardragon user
    GRANT ALL PRIVILEGES ON DATABASE grafana TO wardragon;
EOSQL

echo "Grafana database created successfully"
