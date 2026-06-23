import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401 - import registers every model with Base.metadata before create_all
from app.agents.pipelines import register_pipelines
from app.api.routes import (
    admin,
    auth,
    documents,
    execution,
    generation,
    history,
    intelligence,
    knowledge_base,
    projects,
    settings as settings_routes,
)
from app.core.database import Base, engine
from app.vectorstore.chroma_client import init_collections


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    init_collections()
    register_pipelines()
    yield


app = FastAPI(title="NBC Agentic Test Automation Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(generation.router)
app.include_router(history.router)
app.include_router(execution.router)
app.include_router(intelligence.router)
app.include_router(knowledge_base.router)
app.include_router(admin.router)
app.include_router(settings_routes.router)

logger = logging.getLogger("nbc_platform")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Without this, an unhandled exception anywhere in a route gives the frontend a bare 500
    with no body - completely undiagnosable from the UI. This logs the full traceback to the
    server console (so the actual cause is always visible there) and returns it as `detail` too,
    so the Streamlit error message tells you something useful without needing server access."""

    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
