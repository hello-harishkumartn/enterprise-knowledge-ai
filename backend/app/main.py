import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, auth, chat, documents, evaluations, search
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENV != "test":
        from app.db.bootstrap import init_db, seed_users
        from app.db.session import SessionLocal

        try:
            init_db()
            db = SessionLocal()
            try:
                seed_users(db)
            finally:
                db.close()
        except Exception:
            logging.getLogger(__name__).warning(
                "Database not reachable at startup — is Postgres running? "
                "(see docker-compose.yml)", exc_info=True
            )
    yield


app = FastAPI(
    title="Enterprise Knowledge Intelligence Platform",
    description="Internal RAG-powered knowledge search API for Acme Financial Services.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # Auth is a Bearer token in the Authorization header, never a cookie, so
    # credentialed CORS isn't needed — and combining allow_credentials=True
    # with a wildcard origin is rejected by browsers anyway.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(evaluations.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "env": settings.ENV}
