import os
import re
import uuid


def secure_filename(original: str, max_length: int = 63) -> str:
    name, ext = os.path.splitext(original)
    name = re.sub(r"[^\w\-]", "_", name).lower()
    uuid_suffix = uuid.uuid4().hex
    base_max = max_length - len(uuid_suffix) - len(ext) - 1
    name = name[:base_max]
    return f"{name}_{uuid_suffix}{ext}"


def sizeof_fmt(num: int, suffix="B") -> str:
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"
