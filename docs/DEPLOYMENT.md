# Deployment

## Local / self-hosted: Docker Compose

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend python ../scripts/seed_db.py
```

Services:

| Service | Image/build | Port | Notes |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | 5432 | pgvector preinstalled; `init.sql`/`init_db()` create the extension + tables |
| `backend` | `./backend/Dockerfile` | 8000 | FastAPI + uvicorn; healthcheck hits `/api/health` |
| `frontend` | `./frontend/Dockerfile` | 3000 | Next.js standalone build |

Data persists in the `pgdata` and `backend_storage` named volumes. To reset
everything: `docker compose down -v`.

> **Note on this repository's build environment**: this project was
> developed in a sandbox without Docker installed, so `docker-compose.yml`
> and both Dockerfiles are written and reviewed carefully but not executed
> end-to-end in that environment. They follow standard, well-tested patterns
> (official `pgvector/pgvector` image, multi-stage Next.js `standalone`
> build, healthchecks, named volumes) — verify with `docker compose up
> --build` on a Docker-enabled machine before treating this as
> production-ready, and see `PLAN.md` for exactly what *was* verified there
> (the full non-Docker Python test suite, including real model downloads).

## Free hosted deployment

A fully free-tier path:

1. **Database + Auth: Supabase**
   - Create a Supabase project (free tier).
   - In the SQL editor, run `CREATE EXTENSION IF NOT EXISTS vector;` once.
   - Copy the connection string into `DATABASE_URL` (use the pooler
     connection string, `postgresql+psycopg://...`).
   - Enable Supabase Auth (email/password is enough) and copy
     `SUPABASE_URL` / `SUPABASE_ANON_KEY` into the frontend's environment.

2. **Backend: Render or Fly.io**
   - Point either at `backend/Dockerfile`.
   - Set env vars: `DATABASE_URL` (Supabase), `JWT_SECRET`,
     `LLM_PROVIDER_ORDER`, `GEMINI_API_KEY` (optional).
   - Run `python scripts/seed_db.py` once via a one-off job/shell after the
     first deploy to ingest `sample_data/`.

3. **Frontend: Vercel**
   - Import the `frontend/` directory as the project root.
   - Set `NEXT_PUBLIC_API_URL` to the deployed backend's `/api` URL.

### Swapping in Supabase Auth

The local JWT flow (`app/core/security.py` + `app/api/routes/auth.py`) and
Supabase Auth both end up producing a JWT with a `role` claim the rest of
the backend reads via `get_current_user` (`app/api/deps.py`). To switch:

1. Set the frontend to call Supabase's client SDK for login instead of
   `POST /api/auth/login`, storing the Supabase session JWT the same way
   `lib/api.ts` stores the local one.
2. Change `decode_access_token` in `app/core/security.py` to verify against
   Supabase's JWKS instead of the local `JWT_SECRET` (Supabase publishes
   its JWKS URL per project).
3. Map Supabase's user metadata (`role`, `department`) into the same claim
   shape (`{sub, role, email}`) the rest of the backend already expects.

No route, no retrieval code, and no RBAC logic changes — that's the point of
keeping auth behind a thin verification boundary.

## Ollama (optional local LLM fallback)

If you want the Ollama fallback to actually work (rather than falling
through to the mock provider):

```bash
# On the host (not inside the backend container)
ollama pull llama3.2
ollama serve
```

`docker-compose.yml` points `OLLAMA_BASE_URL` at
`http://host.docker.internal:11434` so the backend container can reach an
Ollama daemon running on the host. On Linux, add
`extra_hosts: ["host.docker.internal:host-gateway"]` to the `backend`
service if `host.docker.internal` doesn't resolve.

## Environment variables reference

See [.env.example](../.env.example) for the authoritative list with
descriptions.

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

- **backend job**: spins up a `pgvector/pgvector:pg16` service container,
  installs `requirements-dev.txt`, runs `ruff check .`, then the full pytest
  suite (including the DB-backed RBAC/API/integration tests that skip
  locally without Postgres — here they run for real).
- **frontend job**: `npm install`, `npm run lint`, `npm run build`.

There is no deploy step configured (this is a portfolio project, not a
running production service) — wire one in following the Render/Fly/Vercel
steps above if you fork this for real use.
