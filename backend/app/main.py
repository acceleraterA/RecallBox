from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import crud
from app.config import settings
from app.database import SessionLocal
from app.routers.items import router as items_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    with SessionLocal() as db:
        crud.get_or_create_default_user(db)
    yield


app = FastAPI(title="RecallBox API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
