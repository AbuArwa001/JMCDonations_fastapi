import asyncio
import re

def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    return re.sub(r'[\s_-]+', '-', s)

try:
    slugify("")
    print("Empty string works")
except Exception as e:
    print("Empty string failed:", e)

try:
    slugify(None)
    print("None works")
except Exception as e:
    print("None failed:", e)
