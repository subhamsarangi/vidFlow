import aiofiles
import shutil
import traceback
import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..config import CHUNK_DIR, UPLOAD_DIR
from ..utils import secure_filename
from ..auth import create_token

router = APIRouter()


@router.post("/upload_chunk/")
async def upload_chunk(
    file: UploadFile = File(...),
    chunk_index: int = Form(...),
    unique_folder: str = Form(...),
    filename: str = Form(...),
):
    try:
        chunk_dir = CHUNK_DIR / unique_folder
        chunk_dir.mkdir(parents=True, exist_ok=True)
        meta = chunk_dir / "original_filename.txt"
        if not meta.exists():
            sanitized = secure_filename(filename)
            async with aiofiles.open(meta, "w") as f:
                await f.write(sanitized)

        path = chunk_dir / f"chunk_{chunk_index}"
        async with aiofiles.open(path, "wb") as out:
            await out.write(await file.read())
        return {"status": "chunk received", "index": chunk_index}
    except Exception as e:
        logging.error(f"{e}\n{traceback.format_exc()}")
        raise HTTPException(500, "Error uploading chunk")


@router.post("/merge_chunks/")
async def merge_chunks(unique_folder: str):
    try:
        chunk_dir = CHUNK_DIR / unique_folder
        if not chunk_dir.exists():
            raise HTTPException(404, "No chunks folder")

        meta = chunk_dir / "original_filename.txt"
        if not meta.exists():
            raise HTTPException(400, "Missing metadata")
        async with aiofiles.open(meta, "r") as f:
            original = (await f.read()).strip()

        chunks = sorted(
            chunk_dir.glob("chunk_*"), key=lambda p: int(p.stem.split("_")[1])
        )
        if not chunks:
            raise HTTPException(404, "No chunks to merge")

        dest = UPLOAD_DIR / original

        with open(dest, "wb") as out:
            for c in chunks:
                with open(c, "rb") as cf:
                    out.write(cf.read())
        shutil.rmtree(chunk_dir)

        token = create_token(dest.name)
        return {
            "status": "merge complete",
            "video_url": f"/content/{dest.name}?token={token}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"{e}\n{traceback.format_exc()}")
        raise HTTPException(500, "Error merging chunks")
