from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import crud
from app.config import settings
from app.database import SessionLocal
from app.routers.agent import router as agent_router
from app.routers.items import router as items_router
from app.routers.rag import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.enable_auth:
        with SessionLocal() as db:
            crud.get_or_create_default_user(db)
    yield


app = FastAPI(title="RecallBox API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items_router)
app.include_router(rag_router)
app.include_router(agent_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

