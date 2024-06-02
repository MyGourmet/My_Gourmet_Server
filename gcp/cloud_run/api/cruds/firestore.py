# Standard Library
import logging
from datetime import datetime
from typing import Any, List

# Third Party Library
from fastapi import HTTPException  # type: ignore

# First Party Library
from api.core.data_class import StoreData  # type: ignore

logging.basicConfig(level=logging.INFO)


def save_to_firestore(store_data: StoreData, photo_id: str, user_id: str, db: Any) -> None:
    logging.info(f"Preparing to save store data to Firestore: {store_data}")
    try:
        # Firestoreの`users`コレクションのphotoドキュメントを取得
        user_ref = db.collection("users").document(user_id)
        photo_ref = user_ref.collection("photos").document(photo_id)
        photo_doc = photo_ref.get()

        if photo_doc.exists:
            # ドキュメントが存在する場合、areaStoreIdsを更新
            logging.info(
                f"Photo document {photo_id} exists for user {user_id}. Updating areaStoreIds."
            )
            photo_data = photo_doc.to_dict()
            area_store_ids = photo_data.get("areaStoreIds", [])
            if store_data.store_id not in area_store_ids:
                area_store_ids.append(store_data.store_id)
                photo_ref.update({"areaStoreIds": area_store_ids, "updatedAt": datetime.utcnow()})
                logging.info(f"Updated areaStoreIds: {area_store_ids}")
            else:
                logging.info(f"Store ID {store_data.store_id} already in areaStoreIds.")
        else:
            # ドキュメントが存在しない場合、新しく作成
            logging.info(
                f"Photo document {photo_id} does not exist for user {user_id}. Creating new document."
            )
            photo_data = {
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
                "userId": user_id,
                "otherUrls": [],
                "tags": [],
                "storeId": store_data.store_id,
                "areaStoreIds": [store_data.store_id],
            }
            photo_ref.set(photo_data)
            logging.info(f"Created new photo document with data: {photo_data}")

        store_data_dict = {
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "name": store_data.name,
            "phoneNumber": store_data.phoneNumber,
            "website": store_data.website,
            "openingHours": store_data.openingHours,
            "imageUrls": store_data.imageUrls,
        }

        # `stores` コレクションにデータを保存
        db.collection("stores").document(store_data.store_id).set(store_data_dict)
        logging.info(f"Saved store data to stores collection with ID {store_data.store_id}")

    except Exception as e:
        logging.error(f"An error occurred while saving to Firestore: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving to Firestore: {e}",
        )


def get_latest_document_id(user_id: str, db: Any) -> str:
    logging.info(f"Fetching latest document ID for user {user_id}")
    photos_ref = db.collection("users").document(user_id).collection("photos")
    # IDに基づいて最新のドキュメントを取得
    latest_photos = photos_ref.order_by("__name__", direction="DESCENDING").limit(1).get()
    if latest_photos:  # 空のリストを確認
        latest_photo_id: str = latest_photos[0].id  # 最新のドキュメントIDを取得
        logging.info(f"Latest photo document ID: {latest_photo_id}")
        return latest_photo_id
    else:
        logging.info("No photo documents found.")
        return ""
