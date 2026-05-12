"""
Supabase Storage client for dataset uploads, chunk files, and logs.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings


class SupabaseStorage:
    """Thin async wrapper around Supabase Storage REST API."""

    def __init__(self) -> None:
        self.base_url = f"{settings.SUPABASE_URL}/storage/v1"
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        }

    async def upload(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> dict:
        url = f"{self.base_url}/object/{self.bucket}/{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                content=data,
                headers={**self.headers, "Content-Type": content_type},
            )
            resp.raise_for_status()
            return resp.json()

    async def download(self, path: str) -> bytes:
        url = f"{self.base_url}/object/{self.bucket}/{path}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.content

    async def delete(self, paths: list[str]) -> dict:
        url = f"{self.base_url}/object/{self.bucket}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.delete(
                url,
                json={"prefixes": paths},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def get_public_url(self, path: str) -> str:
        return f"{self.base_url}/object/public/{self.bucket}/{path}"


storage = SupabaseStorage()
