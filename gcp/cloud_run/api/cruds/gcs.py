# Standard Library
import logging

# Third Party Library
from fastapi import HTTPException  # type: ignore
from google.cloud import storage  # type: ignore

# Constants
GCS_PREFIX = "photo-jp-my-gourmet-image-classification-2023-08"


def save_to_cloud_storage(
    content: bytes,
    filename: str,
    bucket: storage.Bucket,
    user_id: str,
) -> str:
    try:
        logging.info(f"Preparing to upload image to Cloud Storage: {filename}")
        """Firebase Storageに画像をアップロードし、公開URLを取得する"""
        blob = bucket.blob(f"{GCS_PREFIX}/{user_id}/{filename}")
        blob.upload_from_string(content, content_type="image/jpeg")

        # ファイルを公開して、公開URLを取得
        blob.make_public()
        image_url: str = blob.public_url
        if image_url:
            return image_url
        else:
            return ""

    except Exception as e:
        logging.error(f"Failed to upload image to Cloud Storage: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while saving to Firestore: {e}",
        )
