"""
APK Download API — serves Nexaris.apk directly from the backend.

Endpoint:
    GET /api/v1/download/apk

Headers set:
    Content-Type: application/vnd.android.package-archive
    Content-Disposition: attachment; filename="Nexaris.apk"

Security:
    - Path traversal prevention (hardcoded filename)
    - Rate-limited by the global middleware (120 req/min per IP)
    - Only serves the single official APK file
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="/download", tags=["download"])

# Hardcoded APK path — prevents directory traversal
_DOWNLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "downloads"
_APK_FILENAME = "Nexaris.apk"
_APK_PATH = _DOWNLOADS_DIR / _APK_FILENAME


def _get_apk_info() -> dict | None:
    """Return APK metadata if the file exists."""
    if not _APK_PATH.is_file():
        return None
    stat = _APK_PATH.stat()
    size_mb = round(stat.st_size / (1024 * 1024), 1)

    # Compute SHA256 checksum (cached per mtime in production)
    sha256 = hashlib.sha256()
    with open(_APK_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return {
        "filename": _APK_FILENAME,
        "size_bytes": stat.st_size,
        "size_mb": size_mb,
        "sha256": sha256.hexdigest(),
        "version": "1.0.0",
        "min_android": "8.0 (API 26)",
        "download_url": "/api/v1/download/apk",
    }


@router.get("/apk")
async def download_apk():
    """
    Stream the Nexaris APK file.
    Returns 404 with a helpful message if APK is not yet uploaded.
    """
    if not _APK_PATH.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "APK not found",
                "message": "The Nexaris APK has not been uploaded yet. "
                           "Place the signed APK at: backend/downloads/Nexaris.apk",
                "expected_path": str(_APK_PATH),
            },
        )

    return FileResponse(
        path=str(_APK_PATH),
        filename=_APK_FILENAME,
        media_type="application/vnd.android.package-archive",
        headers={
            "Content-Disposition": f'attachment; filename="{_APK_FILENAME}"',
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/apk/info")
async def apk_info():
    """
    Return APK metadata (size, checksum, version) without downloading.
    Used by the frontend to show APK details before download.
    """
    info = _get_apk_info()
    if info is None:
        return JSONResponse(
            status_code=404,
            content={
                "available": False,
                "message": "APK not uploaded yet",
            },
        )
    return {"available": True, **info}
