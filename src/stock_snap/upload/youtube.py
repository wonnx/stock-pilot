"""YouTube Data API v3 upload for YouTube Shorts."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import httpx

from stock_snap.utils.config import config

logger = logging.getLogger(__name__)
YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_API_BASE = "https://www.googleapis.com/youtube/v3"
YT_TOKEN_URL = "https://oauth2.googleapis.com/token"

# YouTube Data API v3 quota: 10,000 units/day. Upload costs 1,600 units.
UPLOAD_QUOTA_COST = 1600
_QUOTA_FILE = Path("/tmp/yt_quota_usage.json")


def _load_quota() -> dict:
    """Load daily quota usage from temp file."""
    if _QUOTA_FILE.exists():
        try:
            data = json.loads(_QUOTA_FILE.read_text())
            from datetime import date
            if data.get("date") == str(date.today()):
                return data
        except Exception:
            pass
    return {"date": str(__import__("datetime").date.today()), "used": 0}


def _save_quota(data: dict) -> None:
    try:
        _QUOTA_FILE.write_text(json.dumps(data))
    except Exception:
        pass


class YouTubeUploader:
    """Upload videos to YouTube Shorts via Data API v3."""

    def __init__(self) -> None:
        self._client_id = config.YOUTUBE_CLIENT_ID
        self._client_secret = config.YOUTUBE_CLIENT_SECRET
        self._refresh_token = config.YOUTUBE_REFRESH_TOKEN
        # Fallback: static access token (legacy)
        self._static_oauth_token = config.YOUTUBE_OAUTH_TOKEN
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    def _refresh_access_token(self) -> bool:
        """Exchange refresh token for a new access token. Returns True on success."""
        if not (self._client_id and self._client_secret and self._refresh_token):
            return False
        try:
            resp = httpx.post(
                YT_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=15,
            )
            resp.raise_for_status()
            body = resp.json()
            self._access_token = body["access_token"]
            # expires_in seconds, subtract 60s buffer
            self._token_expiry = time.time() + body.get("expires_in", 3600) - 60
            logger.info("YouTube access token refreshed (expires in ~%ds)", body.get("expires_in", 3600))
            return True
        except Exception as e:
            logger.error("YouTube token refresh failed: %s", e)
            return False

    def _get_access_token(self) -> str | None:
        """Return a valid access token, refreshing if needed."""
        # Prefer refresh-token flow
        if self._client_id and self._client_secret and self._refresh_token:
            if not self._access_token or time.time() >= self._token_expiry:
                if not self._refresh_access_token():
                    return None
            return self._access_token
        # Fallback: static token
        if self._static_oauth_token:
            return self._static_oauth_token
        return None

    def _check_quota(self) -> bool:
        """Return False if daily upload quota would be exceeded."""
        quota = _load_quota()
        if quota["used"] + UPLOAD_QUOTA_COST > 10_000:
            logger.error(
                "YouTube daily quota exceeded: used=%d, cost=%d, limit=10000",
                quota["used"], UPLOAD_QUOTA_COST,
            )
            return False
        return True

    def _record_quota(self) -> None:
        quota = _load_quota()
        quota["used"] += UPLOAD_QUOTA_COST
        _save_quota(quota)
        logger.info("YouTube quota used today: %d / 10000", quota["used"])

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None = None,
        max_retries: int = 3,
        dry_run: bool = False,
    ) -> str | None:
        """Upload a video as YouTube Shorts. Returns video ID or None.

        Args:
            video_path: Local path to the .mp4 file.
            title: Video title (max 100 chars).
            description: Video description (max 5000 chars).
            tags: List of tags. '#Shorts' appended automatically.
            max_retries: Number of upload attempts on transient errors.
            dry_run: If True, skip actual upload and return a placeholder ID.
        """
        if dry_run:
            logger.info("[dry-run] YouTube Shorts upload skipped for: %s", video_path)
            return "dry-run-video-id"

        if not self._check_quota():
            return None

        token = self._get_access_token()
        if not token:
            logger.error("No YouTube OAuth token available — set YOUTUBE_REFRESH_TOKEN or YOUTUBE_OAUTH_TOKEN")
            return None

        if not video_path.exists():
            logger.error("Video file not found: %s", video_path)
            return None

        tags = list(tags or [])
        if "#Shorts" not in tags:
            tags.append("#Shorts")

        metadata = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags,
                "categoryId": "25",  # News & Politics
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                # Re-fetch token in case it expired between retries
                token = self._get_access_token()
                if not token:
                    logger.error("Token unavailable on attempt %d", attempt)
                    return None

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/mp4",
                    "X-Upload-Content-Length": str(video_path.stat().st_size),
                }
                # Initiate resumable upload session
                init_resp = httpx.post(
                    YT_UPLOAD_URL,
                    params={"uploadType": "resumable", "part": "snippet,status"},
                    headers=headers,
                    content=json.dumps(metadata).encode(),
                    timeout=30,
                )
                init_resp.raise_for_status()
                upload_url = init_resp.headers.get("Location")
                if not upload_url:
                    logger.error("No upload URL in YouTube response")
                    return None

                # Upload video bytes
                video_data = video_path.read_bytes()
                up_resp = httpx.put(
                    upload_url,
                    content=video_data,
                    headers={"Content-Type": "video/mp4"},
                    timeout=300,
                )
                up_resp.raise_for_status()
                video_id = up_resp.json().get("id")
                if video_id:
                    logger.info("YouTube Shorts uploaded: https://youtu.be/%s", video_id)
                    self._record_quota()
                    return video_id
                logger.error("YouTube response missing video id: %s", up_resp.text[:200])
                return None

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                # 4xx client errors are not retryable (except 429 rate-limit)
                if status_code != 429 and 400 <= status_code < 500:
                    logger.error("YouTube upload client error %d: %s", status_code, e.response.text[:200])
                    return None
                last_error = e
                wait = 2 ** attempt
                logger.warning("YouTube upload attempt %d/%d failed (%d) — retrying in %ds", attempt, max_retries, status_code, wait)
                time.sleep(wait)
            except Exception as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning("YouTube upload attempt %d/%d error: %s — retrying in %ds", attempt, max_retries, e, wait)
                time.sleep(wait)

        logger.error("YouTube upload failed after %d attempts: %s", max_retries, last_error)
        return None


youtube = YouTubeUploader()
