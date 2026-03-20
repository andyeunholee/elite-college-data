# cache_manager.py
import json
import os
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CACHE_MAX_AGE_DAYS = 30  # Refresh data if older than this


def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{key}.json")


def load_cache(key: str) -> dict | None:
    """Return cached data if it exists and is not stale. Otherwise None."""
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
    if datetime.now() - cached_at > timedelta(days=CACHE_MAX_AGE_DAYS):
        return None
    return data


def save_cache(key: str, payload: dict) -> None:
    """Save data to cache with current timestamp."""
    payload["cached_at"] = datetime.now().isoformat()
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def clear_cache(key: str | None = None) -> None:
    """Delete one cache file or all cache files."""
    if key:
        path = _cache_path(key)
        if os.path.exists(path):
            os.remove(path)
    else:
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith(".json"):
                os.remove(os.path.join(CACHE_DIR, fname))


def cache_age(key: str) -> str:
    """Return human-readable age of a cache entry."""
    path = _cache_path(key)
    if not os.path.exists(path):
        return "No cache"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
    delta = datetime.now() - cached_at
    hours = int(delta.total_seconds() // 3600)
    if hours < 24:
        return f"{hours}h ago"
    return f"{delta.days}d ago"
