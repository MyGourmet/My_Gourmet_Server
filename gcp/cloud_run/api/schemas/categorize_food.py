# Standard Library
import logging
import os
from base64 import b64decode
from typing import Any

# Third Party Library
from fastapi import FastAPI, HTTPException  # type: ignore

# First Party Library
from api.core.gemini import categorize_from_gemini_api
from api.cruds.firestore import save_category_and_photo_to_firestore
from api.cruds.gcs import save_own_photo_to_cloud_storage

logging.basicConfig(level=logging.INFO)

app = FastAPI()


def translate_food_category(category: str) -> str:
    category_translation = {
        "ラーメン": "ramen",
        "カフェ": "cafe",
        "和食": "japanese_food",
        "洋食": "western_food",
        "エスニック": "ethnic_food",
        "飲食物ではない": "not_food",
    }

    for key in category_translation:
        if key in category:
            return category_translation[key]

    return "not_food"


def process_image(
    user_id: str,
    photo_id: str,
    photo_data: bytes,
    db: Any,
    storage_client: Any,
):
    try:
        # 画像をGCSに保存
        logging.info("process_image start")
        filename = f"{photo_id}.jpg"
        image_url = save_own_photo_to_cloud_storage(photo_data, filename, photo_id, storage_client)
        logging.info(f"Image saved to GCS: {image_url}")

        # 分析結果を返却
        category = categorize_from_gemini_api(photo_data)

        eng_category = translate_food_category(category)

        save_category_and_photo_to_firestore(user_id, photo_id, eng_category, image_url, db)

    except (AttributeError, KeyError) as e:
        logging.error(f"Error processing image: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing the image",
        )


def categorize_food(
    user_id: str,
    photo_id: str,
    photo: str,
    db: Any,
    storage_client: Any,
):
    # Base64エンコードされた画像データをデコード
    photo_data = b64decode(photo)

    # 画像処理の実行
    process_image(user_id, photo_id, photo_data, db, storage_client)
    return {"message": "Successfully processed photos"}
