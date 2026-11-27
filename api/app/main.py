from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import me, mentees, roadmaps, submissions


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().upload_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(title="Mentor Hub API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(me.router)
app.include_router(mentees.router)
app.include_router(roadmaps.router)
app.include_router(submissions.router)


@app.get("/health")
async def health():
    return {"ok": True}
