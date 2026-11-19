#!/bin/sh
set -eu

psql --no-psqlrc --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<'SQL'
\getenv planner_password PLANNER_DB_PASSWORD
\getenv keycloak_password KEYCLOAK_DB_PASSWORD

CREATE ROLE planner LOGIN PASSWORD :'planner_password';
CREATE ROLE keycloak LOGIN PASSWORD :'keycloak_password';
CREATE DATABASE ai_task_planner OWNER planner;
CREATE DATABASE keycloak OWNER keycloak;
SQL
