import os
import shutil
import uuid
from datetime import date, time
from pathlib import Path
from typing import Optional

def parse_date(date_str: Optional[str]) -> date:
    try:
        return date.fromisoformat(str(date_str)) if date_str else date.today()
    except Exception:
        return date.today()

def parse_time(time_str: Optional[str]) -> time:
    try:
        if time_str:
            parts = [int(p) for p in str(time_str).split(":")[:2]]
            return time(parts[0], parts[1])
    except Exception:
        pass
    return time(13, 0)

def save_khutba_photo(photo_field) -> Optional[str]:
    if not photo_field:
        return None
    if hasattr(photo_field, "filename") and photo_field.filename:
        ext = os.path.splitext(photo_field.filename or "")[1] or ".jpg"
        img_name = f"imam_{uuid.uuid4().hex[:10]}{ext}"
        dest = Path("static/khutba") / img_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as buf:
            shutil.copyfileobj(photo_field.file, buf)
        return f"/static/khutba/{img_name}"
    elif isinstance(photo_field, str) and photo_field:
        return photo_field
    return None

def make_full_image_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = "https://donations-api.jamiamosque.co.ke"
    return f"{base}{url}" if url.startswith("/") else f"{base}/{url}"
