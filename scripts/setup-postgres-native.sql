-- QPort local PostgreSQL bootstrap for native Windows development.
-- Run once from the repository root with:
--   psql -U postgres -f scripts/setup-postgres-native.sql
--
-- Development-only credentials:
--   user: qport
--   password: qport
--   database: qport

SELECT 'CREATE ROLE qport LOGIN PASSWORD ''qport'''
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qport')
\gexec

ALTER ROLE qport WITH LOGIN PASSWORD 'qport';

SELECT 'CREATE DATABASE qport OWNER qport'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'qport')
\gexec

\connect qport

ALTER DATABASE qport OWNER TO qport;
GRANT ALL PRIVILEGES ON DATABASE qport TO qport;
GRANT USAGE, CREATE ON SCHEMA public TO qport;
