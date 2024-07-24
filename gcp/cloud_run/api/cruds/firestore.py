# Standard Library
import logging
from datetime import datetime, timezone
from typing import Any

# Third Party Library
from fastapi import HTTPException  # type: ignore

# First Party Library
from api.core.data_class import StoreData  # type: ignore

logging.basicConfig(level=logging.INFO)


def save_store_data_to_firestore(
    store_data: StoreData, photo_id: str, user_id: str, db: Any
) -> None:
    logging.info(f"Preparing to save store data to Firestore: {store_data}")
    try:
        # Firestoreの`users`コレクションのphotoドキュメントを取得
        user_ref = db.collection("users").document(user_id)
        photo_ref = user_ref.collection("photos").document(photo_id)
        photo_doc = photo_ref.get()

        current_time = datetime.now(timezone.utc)

        if photo_doc.exists:
            # ドキュメントが存在する場合、areaStoreIdsを更新
            logging.info(
                f"Photo document {photo_id} exists for user {user_id}. Updating areaStoreIds."
            )
            photo_data = photo_doc.to_dict()
            area_store_ids = photo_data.get("areaStoreIds", [])
            if store_data.store_id not in area_store_ids:
                area_store_ids.append(store_data.store_id)
                photo_ref.update({"areaStoreIds": area_store_ids, "updatedAt": current_time})
                logging.info(f"Updated areaStoreIds: {area_store_ids}")
            else:
                logging.info(f"Store ID {store_data.store_id} already in areaStoreIds.")
        else:
            # ドキュメントが存在しない場合、新しく作成
            logging.info(
                f"Photo document {photo_id} does not exist for user {user_id}. Creating new document."
            )
            photo_data = {
                "createdAt": current_time,
                "updatedAt": current_time,
                "userId": user_id,
                "otherUrls": [],
                "tags": [],
                "storeId": store_data.store_id,
                "areaStoreIds": [store_data.store_id],
            }
            photo_ref.set(photo_data)
            logging.info(f"Created new photo document with data: {photo_data}")

        store_data_dict = {
            "createdAt": current_time,
            "updatedAt": current_time,
            "name": store_data.name,
            "address": store_data.address,
            "city": store_data.city,
            "prefecture": store_data.prefecture,
            "country": store_data.country,
            "phoneNumber": store_data.phoneNumber,
            "website": store_data.website,
            "openingHours": store_data.openingHours,
            "imageUrls": store_data.imageUrls,
        }

        db.collection("stores").document(store_data.store_id).set(store_data_dict)
        logging.info(f"Saved store data to stores collection with ID {store_data.store_id}")

        logging.info(f"Saved opening hours to stores/{store_data.store_id}/openingHours/hours")

    except Exception as e:
        logging.error(f"An error occurred while saving to Firestore: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving to Firestore: {e}",
        )


def save_category_and_photo_to_firestore(
    user_id: str, photo_id: str, category: str, image_url: str, db: Any
) -> None:
    logging.info(
        f"Preparing to save category and photo to Firestore: category={category}, image_url={image_url}"
    )
    try:
        # Firestoreの`users`コレクションのphotoドキュメントを取得
        user_ref = db.collection("users").document(user_id)
        photo_ref = user_ref.collection("photos").document(photo_id)
        photo_doc = photo_ref.get()

        current_time = datetime.now(timezone.utc)

        if photo_doc.exists:
            # ドキュメントが存在する場合、image_urlとcategoryを更新
            logging.info(
                f"Photo document {photo_id} exists for user {user_id}. Updating image_url and category."
            )
            photo_ref.update(
                {"image_url": image_url, "category": category, "updatedAt": current_time}
            )
            logging.info(
                f"Updated image_url and category: image_url={image_url}, category={category}"
            )
        else:
            # ドキュメントが存在しない場合、新しく作成
            logging.info(
                f"Photo document {photo_id} does not exist for user {user_id}. Creating new document."
            )
            photo_data = {
                "createdAt": current_time,
                "updatedAt": current_time,
                "userId": user_id,
                "image_url": image_url,
                "category": category,
            }
            photo_ref.set(photo_data)
            logging.info(f"Created new photo document with data: {photo_data}")

    except Exception as e:
        logging.error(f"An error occurred while saving to Firestore: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving to Firestore: {e}",
        )
