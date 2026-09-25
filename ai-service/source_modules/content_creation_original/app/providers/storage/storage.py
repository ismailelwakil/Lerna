"""Storage providers — private object storage + expiring signed URLs (spec #40).

* LocalStorage (default): files under data/storage/, never statically served;
  downloads only through HMAC-signed, expiring URLs.
* SupabaseStorage: implemented against the documented Storage REST API
  (requires SUPABASE_URL + SUPABASE_SERVICE_KEY; degrades to local otherwise)."""
from __future__ import annotations

from pathlib import Path

import httpx

from ...core.config import get_settings
from ...core.logging import get_logger
from ...core.security import safe_storage_key

log = get_logger("storage")


class LocalStorage:
    name = "local"

    def __init__(self) -> None:
        from ...core.config import DATA_DIR
        self._root = DATA_DIR / "storage"
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        target = (self._root / key).resolve()
        if not str(target).startswith(str(self._root.resolve())):
            raise ValueError("path traversal blocked")
        return target

    async def put(self, key: str, data: bytes, *, mime: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()


class SupabaseStorage:
    """Documented Supabase Storage REST: POST /storage/v1/object/{bucket}/{key}."""
    name = "supabase"

    def __init__(self) -> None:
        s = get_settings()
        if not (s.supabase_url and s.supabase_service_key):
            raise ValueError("SUPABASE_URL / SUPABASE_SERVICE_KEY not configured")
        self._bucket = s.storage_bucket
        self._client = httpx.AsyncClient(
            base_url=s.supabase_url,
            headers={"Authorization": f"Bearer {s.supabase_service_key}"},
            timeout=httpx.Timeout(120.0, connect=15.0))

    async def put(self, key: str, data: bytes, *, mime: str) -> None:
        resp = await self._client.post(
            f"/storage/v1/object/{self._bucket}/{key}", content=data,
            headers={"Content-Type": mime, "x-upsert": "true"})
        if resp.status_code >= 400:
            raise RuntimeError(f"supabase put {resp.status_code}")

    async def get(self, key: str) -> bytes:
        resp = await self._client.get(f"/storage/v1/object/{self._bucket}/{key}")
        if resp.status_code >= 400:
            raise RuntimeError(f"supabase get {resp.status_code}")
        return resp.content

    async def delete(self, key: str) -> None:
        await self._client.delete(f"/storage/v1/object/{self._bucket}/{key}")

    async def exists(self, key: str) -> bool:
        resp = await self._client.post(
            "/storage/v1/object/list", json={"prefix": key, "limit": 1})
        return bool(resp.json()) if resp.status_code == 200 else False


class StorageService:
    def __init__(self) -> None:
        self._provider = None

    def _ensure(self):
        if self._provider is None:
            s = get_settings()
            if s.storage_provider == "supabase":
                if not (s.supabase_url and s.supabase_service_key):
                    if s.is_prod:
                        # production explicitly selected supabase: NEVER fall
                        # back to local storage (fail closed).
                        raise RuntimeError(
                            "STORAGE_PROVIDER=supabase but SUPABASE_URL / "
                            "SUPABASE_SERVICE_KEY are not configured — "
                            "refusing to fall back to local storage in production.")
                    # dev convenience: documented local fallback
                    log.warning("supabase_unconfigured_dev_fallback_local")
                else:
                    self._provider = SupabaseStorage()  # config errors surface here
            if self._provider is None:
                self._provider = LocalStorage()
        return self._provider

    @property
    def backend(self) -> str:
        return self._ensure().name

    def new_key(self, student_id: str, ext: str) -> str:
        return safe_storage_key(student_id, ext)

    async def put(self, key: str, data: bytes, *, mime: str) -> None:
        await self._ensure().put(key, data, mime=mime)

    async def get(self, key: str) -> bytes:
        return await self._ensure().get(key)

    async def delete(self, key: str) -> None:
        await self._ensure().delete(key)

    async def exists(self, key: str) -> bool:
        return await self._ensure().exists(key)


storage = StorageService()