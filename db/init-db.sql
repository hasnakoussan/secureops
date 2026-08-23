-- Crée la seconde base de données (secureops_auth_db) — POSTGRES_DB
-- (secureops_db) est déjà créée via les variables d'environnement du
-- service postgres dans docker-compose.yml.
CREATE DATABASE secureops_auth_db;
GRANT ALL PRIVILEGES ON DATABASE secureops_auth_db TO secureops_user;
