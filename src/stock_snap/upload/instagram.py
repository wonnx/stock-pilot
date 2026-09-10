"""Instagram Graph API upload."""
from __future__ import annotations

import logging
import os
import time

import httpx

from stock_snap.utils.config import config

logger = logging.getLogger(__name__)
IG_API_BASE = "https://graph.facebook.com/v19.0"

# How long to wait for Instagram to finish transcoding a Reels container. The old 120s
# was enough for a 45s clip but not for a ~113s one at 2160x3840, which is why the daily
# short timed out while the aftermarket recap went through.
CONTAINER_TIMEOUT_SECS = int(os.getenv("INSTAGRAM_CONTAINER_TIMEOUT", "600"))


class InstagramUploader:
    """Upload images/reels to Instagram via Graph API."""

    def __init__(self) -> None:
        self._token = config.INSTAGRAM_ACCESS_TOKEN
        self._ig_user_id = config.INSTAGRAM_USER_ID

    def _check_config(self) -> bool:
        if not self._token or not self._ig_user_id:
            logger.error("INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID required")
            return False
        return True

    def upload_photo(self, image_url: str, caption: str) -> bool:
        """Upload a photo post."""
        if not self._check_config():
            return False
        try:
            # Step 1: Create container
            resp = httpx.post(
                f"{IG_API_BASE}/{self._ig_user_id}/media",
                params={"access_token": self._token},
                json={"image_url": image_url, "caption": caption},
                timeout=30,
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]

            # Step 2: Publish
            pub = httpx.post(
                f"{IG_API_BASE}/{self._ig_user_id}/media_publish",
                params={"access_token": self._token},
                json={"creation_id": container_id},
                timeout=30,
            )
            pub.raise_for_status()
            logger.info("Instagram photo uploaded: %s", pub.json().get("id"))
            return True
        except Exception as e:
            logger.error("Instagram photo upload failed: %s", e)
            return False

    def _wait_for_container(self, container_id: str, timeout: int | None = None) -> bool:
        """Poll until Reels container processing completes. Returns True on FINISHED."""
        timeout = CONTAINER_TIMEOUT_SECS if timeout is None else timeout
        started = time.time()
        deadline = started + timeout
        while time.time() < deadline:
            resp = httpx.get(
                f"{IG_API_BASE}/{container_id}",
                # `status` carries the human-readable reason; without it an ERROR tells
                # us only that something went wrong, which is not enough to act on.
                params={"fields": "status_code,status", "access_token": self._token},
                timeout=15,
            )
            resp.raise_for_status()
            body = resp.json()
            status = body.get("status_code", "")
            logger.info("Container %s status: %s", container_id, status)
            if status == "FINISHED":
                logger.info("Container ready after %.0fs", time.time() - started)
                return True
            if status == "ERROR":
                logger.error("Container processing error: %s", body.get("status", "(no detail)"))
                return False
            time.sleep(5)
        logger.error(
            "Container processing timed out after %ds. Instagram transcodes larger "
            "videos more slowly; raise INSTAGRAM_CONTAINER_TIMEOUT if this recurs.",
            timeout,
        )
        return False

    def upload_reel(self, video_url: str, caption: str, cover_url: str = "") -> bool:
        """Upload a Reel (short video)."""
        if not self._check_config():
            return False
        try:
            payload: dict = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": True,
            }
            if cover_url:
                payload["cover_url"] = cover_url

            # Step 1: Create container
            resp = httpx.post(
                f"{IG_API_BASE}/{self._ig_user_id}/media",
                params={"access_token": self._token},
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]
            logger.info("Reel container created: %s", container_id)

            # Step 2: Wait for video processing to finish
            if not self._wait_for_container(container_id):
                logger.error("Reel container did not finish processing")
                return False

            # Step 3: Publish
            pub = httpx.post(
                f"{IG_API_BASE}/{self._ig_user_id}/media_publish",
                params={"access_token": self._token},
                json={"creation_id": container_id},
                timeout=30,
            )
            pub.raise_for_status()
            logger.info("Instagram reel uploaded: %s", pub.json().get("id"))
            return True
        except Exception as e:
            logger.error("Instagram reel upload failed: %s", e)
            return False


instagram = InstagramUploader()
