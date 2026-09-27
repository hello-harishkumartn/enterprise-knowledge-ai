-- Mounted into /docker-entrypoint-initdb.d/ (see docker-compose.yml) so the
-- pgvector extension exists from the moment the `db` container first
-- initializes its data directory — belt-and-suspenders alongside
-- app.db.bootstrap.init_db(), which also creates it defensively on backend
-- startup for the non-Docker local-dev path.
CREATE EXTENSION IF NOT EXISTS vector;
