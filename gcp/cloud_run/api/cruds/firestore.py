# Standard Library
import logging
from datetime import datetime
from typing import Any

# Third Party Library
from fastapi import HTTPException  # type: ignore


def save_to_firestore(image_url: str, shot_at: datetime, user_id: str, db: Any) -> None:
    logging.info(f"Preparing to save image URL to Firestore: {image_url}")
    try:
        # Firestoreに保存するデータを作成
        photo_data = {
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "userId": user_id,
            "url": image_url,
            "otherUrls": [],
            "tags": [],
            "storeId": None,
            "areaStoreIds": [],
        }

        # Firestoreの`users`コレクションにデータを保存
        user_ref = db.collection("users").document(user_id)
        doc_id = shot_at.strftime("%Y%m%d_%H%M%S")
        user_ref.collection("photos").document(doc_id).set(photo_data)
    except Exception as e:
        logging.error(f"An error occurred while saving to Firestore: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while saving to Firestore: {e}",
        )


def get_latest_document_id(user_id: str, db: Any) -> str:
    photos_ref = db.collection("users").document(user_id).collection("photos")
    # IDに基づいて最新のドキュメントを取得
    latest_photos = photos_ref.order_by("__name__", direction="DESCENDING").limit(1).get()
    if latest_photos:  # 空のリストを確認
        latest_photo_id: str = latest_photos[0].id  # 最新のドキュメントIDを取得
        return latest_photo_id
    else:
        return ""
