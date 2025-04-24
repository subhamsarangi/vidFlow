from pathlib import Path

# Base dirs
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHUNK_DIR = BASE_DIR / "chunks"

# JWT settings
SECRET_KEY = "sX1XdD25s45gsG8A5eG69rEk3sxE0W7we06er32ES45ad7DdaT5X"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = 3600

# CORS / hotlink protection
ALLOWED_REFERERS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://192.168.29.76:8000",
]
