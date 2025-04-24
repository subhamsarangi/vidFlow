import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import BASE_DIR, UPLOAD_DIR, CHUNK_DIR
from .routers import upload, content

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in (UPLOAD_DIR, CHUNK_DIR):
        Path(d).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Routers
app.include_router(upload.router)
app.include_router(content.router)


@app.get("/", include_in_schema=False)
async def root():
    return HTMLResponse((BASE_DIR / "templates" / "index.html").read_text())
