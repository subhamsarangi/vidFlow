import logging
import traceback
import os
import re
import uuid
import shutil
import time
from pathlib import Path
import aiofiles
import mimetypes

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Header,
    Request,
    Form,
    Query,
)
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from jose import jwt, JWTError


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Config
SECRET_KEY = "sX1XdD25s45gsG8A5eG69rEk3sxE0W7we06er32ES45ad7DdaT5X"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = 3600
ALLOWED_REFERERS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://192.168.29.76:8000",
]

app = FastAPI()
# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# Directories
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHUNK_DIR = BASE_DIR / "chunks"
for d in (UPLOAD_DIR, CHUNK_DIR):
    d.mkdir(exist_ok=True)

# Mount static and templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def secure_filename(original: str, max_length: int = 63) -> str:
    name, ext = os.path.splitext(original)

    # Slugify: keep alphanumeric, underscore and hyphen, lowercase it
    name = re.sub(r"[^\w\-]", "_", name).lower()

    # Ensure it's not too long
    uuid_suffix = uuid.uuid4().hex  # 32 chars
    base_max = (
        max_length - len(uuid_suffix) - len(ext) - 1
    )  # minus underscore and extension
    name = name[:base_max]  # trim if needed

    # Compose final unique filename
    unique_name = f"{name}_{uuid_suffix}{ext}"
    return unique_name


def sizeof_fmt(num, suffix="B"):
    """Convert bytes to human-readable string."""
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


@app.get("/")
async def serve_frontend():
    return HTMLResponse((BASE_DIR / "templates" / "index.html").read_text())


@app.post("/upload_chunk/")
async def upload_chunk(
    file: UploadFile = File(...),
    chunk_index: int = Form(...),
    unique_folder: str = Form(...),
    filename: str = Form(...),
):
    try:
        file_chunk_dir = CHUNK_DIR / unique_folder
        file_chunk_dir.mkdir(parents=True, exist_ok=True)

        meta_path = file_chunk_dir / "original_filename.txt"
        if not meta_path.exists():
            sanitized = secure_filename(filename)
            async with aiofiles.open(meta_path, "w") as meta_f:
                await meta_f.write(sanitized)

        chunk_path = file_chunk_dir / f"chunk_{chunk_index}"
        async with aiofiles.open(chunk_path, "wb") as out_file:
            await out_file.write(await file.read())
        return {"status": "chunk received", "index": chunk_index}
    except Exception as e:
        logging.error(f"Error in upload_chunk: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Error uploading chunk. Check logs."
        )


@app.post("/merge_chunks/")
async def merge_chunks(unique_folder: str = Query(...)):
    try:
        file_chunk_dir = CHUNK_DIR / unique_folder
        if not file_chunk_dir.exists():
            raise HTTPException(status_code=404, detail="No chunks folder found")

        # Read back the original filename (with its extension)
        meta_path = file_chunk_dir / "original_filename.txt"
        if not meta_path.exists():
            raise HTTPException(
                status_code=400, detail="Missing metadata for original filename"
            )
        async with aiofiles.open(meta_path, "r") as meta_f:
            original_filename = (await meta_f.read()).strip()

        # Gather and sort all chunk files
        chunk_files = sorted(
            file_chunk_dir.glob("chunk_*"), key=lambda x: int(x.stem.split("_")[1])
        )

        if not chunk_files:
            raise HTTPException(
                status_code=404, detail="No chunk files available to merge."
            )

        # Merge into final video
        destination_file = UPLOAD_DIR / original_filename

        with open(destination_file, "wb") as out_file:
            for chunk_file in chunk_files:
                with open(chunk_file, "rb") as cf:
                    out_file.write(cf.read())

        shutil.rmtree(file_chunk_dir)
        # Generate time-limited token
        exp = int(time.time()) + TOKEN_EXPIRATION_SECONDS
        token = jwt.encode(
            {"file": destination_file.name, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM
        )
        video_url = f"/content/{destination_file.name}?token={token}"

        return {"status": "merge complete", "video_url": video_url}
    except Exception as e:
        logging.error(f"Error in merge_chunks: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error merging chunks. Check logs.")


@app.get("/content/{filename}")
async def file_page(filename: str, token: str, request: Request):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("file") != filename:
            raise JWTError()

        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Compute size
        file_size = file_path.stat().st_size
        size_str = sizeof_fmt(file_size)

        # Determine if it's a video file by extension
        is_video = filename.lower().endswith((".mp4", ".webm", ".ogg", ".mov", ".mkv"))

        return templates.TemplateResponse(
            "file_page.html",
            {
                "request": request,
                "filename": filename,
                "size_str": size_str,
                "is_video": is_video,
                "token": token,
            },
        )

    except Exception as e:
        logging.error(f"Error in file_page: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Error serving video page. Check logs."
        )


@app.get("/stream/{filename}")
async def stream_video(
    request: Request, filename: str, token: str = None, range: str = Header(None)
):
    try:
        # Hotlink protection: check Referer header
        referer = request.headers.get("referer")
        if not referer or not any(referer.startswith(url) for url in ALLOWED_REFERERS):
            raise HTTPException(status_code=403, detail="Hotlinking not allowed")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("file") != filename:
            raise JWTError()
        file_path = UPLOAD_DIR / filename
        file_size = os.path.getsize(file_path)
        start, end = 0, file_size - 1
        if range:
            bytes_range = range.replace("bytes=", "").split("-")
            if bytes_range[0]:
                start = int(bytes_range[0])
            if len(bytes_range) > 1 and bytes_range[1]:
                end = int(bytes_range[1])
        if start > end:
            raise HTTPException(
                status_code=416, detail="Requested Range Not Satisfiable"
            )
        chunk_size = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        }
        status_code = 206 if range else 200

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    chunk = f.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"  # fallback default

        return StreamingResponse(
            iterfile(), media_type=mime_type, headers=headers, status_code=status_code
        )
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in stream_video: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Error streaming video. Check logs."
        )
