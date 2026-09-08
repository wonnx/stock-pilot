"""Public URL hosting for rendered media.

The Instagram Graph API does not accept file bytes for Reels — it fetches the video
from a URL we hand it, so every render needs a publicly reachable address first.

catbox.moe filled that role but rejects requests coming from CI runner IP ranges,
so scheduled runs never got past this step. On GitHub Actions the asset is instead
attached to a rolling GitHub Release in this (public) repository, whose
``browser_download_url`` is public and stable enough for Instagram to pull from.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

API_ROOT = "https://api.github.com"
UPLOAD_ROOT = "https://uploads.github.com"

# All generated media lives under one rolling release rather than one release per
# run, so the Releases tab stays readable.
RELEASE_TAG = os.getenv("MEDIA_RELEASE_TAG", "media")
RELEASE_TITLE = "Generated media (auto)"
RELEASE_NOTES = (
    "파이프라인이 생성한 영상·썸네일을 Instagram/YouTube 가 받아갈 수 있도록 "
    "임시로 올려두는 릴리스입니다. 소스 릴리스가 아니며 수동으로 관리하지 않습니다."
)

# How many assets to retain. Instagram fetches within minutes of upload, so this is
# only a debugging convenience — old assets are pruned to bound repository size.
KEEP_ASSETS = int(os.getenv("MEDIA_RELEASE_KEEP", "20"))

UPLOAD_TIMEOUT = float(os.getenv("MEDIA_UPLOAD_TIMEOUT", "300"))


def _token() -> str:
    return os.getenv("GITHUB_TOKEN", "")


def _repo() -> str:
    return os.getenv("GITHUB_REPOSITORY", "")


def is_available() -> bool:
    """True when the GitHub Release host can be used (token + repo present)."""
    return bool(_token() and _repo())


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_or_create_release(client: httpx.Client, repo: str) -> dict | None:
    """Fetch the rolling media release, creating it on first use."""
    resp = client.get(f"{API_ROOT}/repos/{repo}/releases/tags/{RELEASE_TAG}", headers=_headers())
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code != 404:
        logger.error("릴리스 조회 실패 (%s): %s", resp.status_code, resp.text[:300])
        return None

    resp = client.post(
        f"{API_ROOT}/repos/{repo}/releases",
        headers=_headers(),
        json={
            "tag_name": RELEASE_TAG,
            "name": RELEASE_TITLE,
            "body": RELEASE_NOTES,
            "prerelease": True,
        },
    )
    if resp.status_code not in (200, 201):
        logger.error("릴리스 생성 실패 (%s): %s", resp.status_code, resp.text[:300])
        return None
    logger.info("미디어 릴리스 생성: %s", RELEASE_TAG)
    return resp.json()


def _delete_asset(client: httpx.Client, repo: str, asset_id: int) -> None:
    resp = client.delete(f"{API_ROOT}/repos/{repo}/releases/assets/{asset_id}", headers=_headers())
    if resp.status_code not in (204, 404):
        logger.warning("에셋 삭제 실패 (%s): %s", resp.status_code, resp.text[:200])


def _prune(client: httpx.Client, repo: str, release_id: int) -> None:
    """Keep only the most recent KEEP_ASSETS assets on the release."""
    resp = client.get(
        f"{API_ROOT}/repos/{repo}/releases/{release_id}/assets",
        headers=_headers(),
        params={"per_page": 100},
    )
    if resp.status_code != 200:
        return
    assets = sorted(resp.json(), key=lambda a: a.get("created_at", ""), reverse=True)
    for asset in assets[KEEP_ASSETS:]:
        _delete_asset(client, repo, asset["id"])
        logger.info("오래된 에셋 정리: %s", asset.get("name"))


def _await_ready(client: httpx.Client, repo: str, asset_id: int, timeout: float = 30.0) -> None:
    """Wait until GitHub reports the asset as fully uploaded.

    A freshly uploaded asset can briefly report state "starting", during which the
    download URL 404s — handing that URL to Instagram would fail the publish.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"{API_ROOT}/repos/{repo}/releases/assets/{asset_id}", headers=_headers())
        if resp.status_code == 200 and resp.json().get("state") == "uploaded":
            return
        time.sleep(2.0)
    logger.warning("에셋이 %.0f초 안에 uploaded 상태가 되지 않음 (id=%s)", timeout, asset_id)


def upload_to_github_release(file_path: Path, mime: str = "video/mp4") -> str | None:
    """Attach *file_path* to the rolling media release and return its public URL.

    Returns None when the environment has no token/repo or the upload fails.
    """
    token, repo = _token(), _repo()
    if not token or not repo:
        logger.warning("GITHUB_TOKEN/GITHUB_REPOSITORY 미설정 — 릴리스 호스팅 사용 불가")
        return None

    file_path = Path(file_path)
    if not file_path.exists():
        logger.error("업로드할 파일이 없음: %s", file_path)
        return None

    with httpx.Client(timeout=UPLOAD_TIMEOUT, follow_redirects=True) as client:
        release = _get_or_create_release(client, repo)
        if not release:
            return None
        release_id = release["id"]

        data = file_path.read_bytes()
        upload_headers = {**_headers(), "Content-Type": mime}
        url = f"{UPLOAD_ROOT}/repos/{repo}/releases/{release_id}/assets"

        resp = client.post(url, headers=upload_headers, params={"name": file_path.name}, content=data)

        # 422 means an asset with this name already exists — replace it.
        if resp.status_code == 422:
            existing = client.get(
                f"{API_ROOT}/repos/{repo}/releases/{release_id}/assets",
                headers=_headers(),
                params={"per_page": 100},
            )
            if existing.status_code == 200:
                for asset in existing.json():
                    if asset.get("name") == file_path.name:
                        _delete_asset(client, repo, asset["id"])
            resp = client.post(
                url, headers=upload_headers, params={"name": file_path.name}, content=data
            )

        if resp.status_code not in (200, 201):
            logger.error("릴리스 에셋 업로드 실패 (%s): %s", resp.status_code, resp.text[:300])
            return None

        asset = resp.json()
        _await_ready(client, repo, asset["id"])
        _prune(client, repo, release_id)

        download_url = asset.get("browser_download_url")
        if not download_url:
            logger.error("업로드 응답에 browser_download_url 없음")
            return None

        logger.info(
            "릴리스 에셋 업로드 완료: %s (%.1f MB)", download_url, len(data) / 1024**2
        )
        return download_url


def upload_to_catbox(file_path: Path, mime: str = "video/mp4") -> str | None:
    """Upload to catbox.moe. Works locally; blocked from CI runner IP ranges."""
    file_path = Path(file_path)
    with open(file_path, "rb") as f:
        resp = httpx.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (file_path.name, f, mime)},
            timeout=120,
        )
    if resp.status_code >= 400:
        # catbox answers every rejection with 412, so the body is the only clue.
        logger.error("catbox %s: %s", resp.status_code, resp.text.strip()[:200])
    resp.raise_for_status()
    url = resp.text.strip()
    return url if url.startswith("https://") else None


def publish_media(file_path: Path, mime: str = "video/mp4") -> str | None:
    """Put *file_path* somewhere Instagram can fetch it and return the public URL.

    Prefers a GitHub Release asset — catbox.moe rejects CI runner IP ranges, which
    is what kept every scheduled run from publishing. catbox stays as the fallback
    for local runs, where there is no GitHub token in the environment.
    """
    if is_available():
        return upload_to_github_release(file_path, mime)

    logger.info("GitHub 릴리스 호스팅 사용 불가 — catbox 로 대체")
    return upload_to_catbox(file_path, mime)
