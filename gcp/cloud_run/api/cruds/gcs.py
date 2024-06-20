# Standard Library
import logging
import os
from typing import Any

# Third Party Library
from fastapi import HTTPException  # type: ignore
from google.cloud import storage  # type: ignore

# Constants
GCS_PREFIX = "photo-jp-my-gourmet-image-classification-2023-08"
PROJECT = os.getenv("GCP_PROJECT", "default-project")


def save_to_cloud_storage(content: bytes, filename: str, store_id: str, storage_client: Any) -> str:
    try:
        bucket = storage_client.bucket(PROJECT)
        """Firebase Storageに画像をアップロードし、公開URLを取得する"""
        blob = bucket.blob(f"{GCS_PREFIX}/{store_id}/{filename}")

        blob.upload_from_string(content, content_type="image/jpeg")

        # ファイルを公開して、公開URLを取得
        blob.make_public()
        image_url: str = blob.public_url
        return image_url

    except Exception as e:
        logging.error(f"Failed to upload image to Cloud Storage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving to Firestore: {e}",
        )
