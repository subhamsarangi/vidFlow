import os
import logging
import mimetypes
import traceback

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from ..auth import verify_token
from ..config import UPLOAD_DIR, SECRET_KEY, ALLOWED_REFERERS
from ..utils import sizeof_fmt

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/content/{filename}")
async def file_page(filename: str, token: str, request: Request):
    try:
        verify_token(token, filename)
        path = UPLOAD_DIR / filename
        if not path.exists():
            raise HTTPException(404, "File not found")

        return templates.TemplateResponse(
            "file_page.html",
            {
                "request": request,
                "filename": filename,
                "size_str": sizeof_fmt(path.stat().st_size),
                "is_video": filename.lower().endswith(
                    (".mp4", ".mov", ".webm", ".mkv")
                ),
                "token": token,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"{e}\n{traceback.format_exc()}")
        raise HTTPException(500, "Error serving page")


@router.get("/stream/{filename}")
async def stream_video(
    request: Request, filename: str, token: str = None, range: str = Header(None)
):
    try:
        referer = request.headers.get("referer", "")
        if not any(referer.startswith(r) for r in ALLOWED_REFERERS):
            raise HTTPException(403, "Hotlinking not allowed")

        verify_token(token, filename)
        file_path = UPLOAD_DIR / filename
        total = os.path.getsize(file_path)
        start, end = 0, total - 1
        if range:
            rs, re = range.replace("bytes=", "").split("-")
            if rs:
                start = int(rs)
            if re:
                end = int(re)
        if start > end:
            raise HTTPException(416, "Range not satisfiable")
        length = end - start + 1

        def reader():
            with open(file_path, "rb") as f:
                f.seek(start)
                n = length
                while n > 0:
                    chunk = f.read(min(1024 * 1024, n))
                    if not chunk:
                        break
                    n -= len(chunk)
                    yield chunk

        mime, _ = mimetypes.guess_type(str(file_path))
        return StreamingResponse(
            reader(),
            media_type=mime or "application/octet-stream",
            headers={
                "Content-Range": f"bytes {start}-{end}/{total}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
            status_code=206 if range else 200,
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"{e}\n{traceback.format_exc()}")
        raise HTTPException(500, "Error streaming video")
