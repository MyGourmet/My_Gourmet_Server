# Standard Library
import logging
from typing import Any, Optional

# Third Party Library
import requests  # type: ignore
from fastapi import HTTPException  # type: ignore


def get_photos_from_google_photo_api(
    access_token: str, page_size: int, next_page_token: Optional[str] = None
) -> Any:
    logging.info(f"Fetching photos with pageSize={page_size} and nextPageToken={next_page_token}")
    try:
        search_request_data = {"pageSize": page_size}
        if next_page_token:
            search_request_data["pageToken"] = next_page_token

        post_url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
        response = requests.post(
            post_url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=search_request_data,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Request failed: {e}",
        )


def should_process_photo(
    photo: Any,
) -> bool:
    """写真が処理対象かどうかを判断する。"""
    if "screenshot" in photo["filename"].lower():
        return False
    if not photo.get("mediaMetadata", {}).get("creationTime"):
        logging.info(f"No shot_at time for photo {photo['filename']}. Skipping.")
        return False
    return True
