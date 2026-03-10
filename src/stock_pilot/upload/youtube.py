"""YouTube Data API v3 upload for YouTube Shorts."""
from __future__ import annotations
import logging
from pathlib import Path
import httpx
from stock_pilot.utils.config import config

logger = logging.getLogger(__name__)
YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YT_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeUploader:
    """Upload videos to YouTube Shorts via Data API v3."""

    def __init__(self) -> None:
        self._api_key = config.YOUTUBE_API_KEY
        self._oauth_token = config.YOUTUBE_OAUTH_TOKEN

    def _check_config(self) -> bool:
        if not self._oauth_token:
            logger.error("YOUTUBE_OAUTH_TOKEN required for upload")
            return False
        return True

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str] | None = None,
    ) -> str | None:
        """Upload a video as YouTube Shorts. Returns video ID or None."""
        if not self._check_config():
            return None
        if not video_path.exists():
            logger.error("Video file not found: %s", video_path)
            return None

        tags = tags or []
        # #Shorts tag required for YouTube Shorts algorithm
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

        try:
            import json
            headers = {
                "Authorization": f"Bearer {self._oauth_token}",
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(video_path.stat().st_size),
            }
            # Initiate resumable upload
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

            # Upload video
            video_data = video_path.read_bytes()
            up_resp = httpx.put(
                upload_url,
                content=video_data,
                headers={"Content-Type": "video/mp4"},
                timeout=300,
            )
            up_resp.raise_for_status()
            video_id = up_resp.json().get("id")
            logger.info("YouTube Shorts uploaded: https://youtu.be/%s", video_id)
            return video_id
        except Exception as e:
            logger.error("YouTube upload failed: %s", e)
            return None


youtube = YouTubeUploader()
