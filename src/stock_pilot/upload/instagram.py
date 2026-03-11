"""Instagram Graph API upload."""
from __future__ import annotations
import logging
import time
import httpx
from stock_pilot.utils.config import config

logger = logging.getLogger(__name__)
IG_API_BASE = "https://graph.facebook.com/v19.0"


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

    def _wait_for_container(self, container_id: str, timeout: int = 120) -> bool:
        """Poll until Reels container processing completes. Returns True on FINISHED."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = httpx.get(
                f"{IG_API_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": self._token},
                timeout=15,
            )
            resp.raise_for_status()
            status = resp.json().get("status_code", "")
            logger.info("Container %s status: %s", container_id, status)
            if status == "FINISHED":
                return True
            if status == "ERROR":
                logger.error("Container processing error")
                return False
            time.sleep(5)
        logger.error("Container processing timed out after %ds", timeout)
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
