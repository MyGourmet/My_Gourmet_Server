# Standard Library
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

# Third Party Library
from fastapi import FastAPI  # type: ignore

# First Party Library
from api.core.auth import authenticate_user, update_user_doc_status
from api.core.classify import classify_image, initialize_classifier
from api.core.photo import get_photos_from_google_photo_api, should_process_photo
from api.cruds.firestore import get_latest_document_id, save_to_firestore
from api.cruds.gcs import save_to_cloud_storage

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.ERROR)


app = FastAPI()

# Constants
READY_FOR_USE = "readyForUse"


# 以下の関数は、取得した最新のドキュメントIDから日時情報を抽出します
def extract_datetime_from_id(document_id: str) -> datetime:
    # ドキュメントIDから日時情報を抽出
    # 形式: 'YYYYMMDD_HHMMSS'
    date_time_str = document_id[:8] + " " + document_id[9:15]
    # 文字列からdatetimeオブジェクトを作成
    date_time_obj = datetime.strptime(date_time_str, "%Y%m%d %H%M%S")
    return date_time_obj


def process_images(access_token: str, user_id: str, db: Any, storage_client: Any) -> dict[str, str]:
    bucket, interpreter, input_details, output_details = initialize_classifier(storage_client)

    classes = [
        "ramen",
        "japanese_food",
        "international_cuisine",
        "cafe",
        "other",
    ]

    photo_count = 0
    user_doc_ref = db.collection("users").document(user_id)
    photos_ref = user_doc_ref.collection("photos")
    has_fetched_before = any(photos_ref.limit(1).get())
    latest_photo_datetime = datetime.now(timezone.utc)
    if has_fetched_before:
        latest_photo_id = get_latest_document_id(user_id, db)
        latest_photo_datetime = extract_datetime_from_id(latest_photo_id)
        latest_photo_datetime = latest_photo_datetime.replace(tzinfo=timezone.utc)

    next_token: Optional[str] = None
    # データ前処理

    # データ処理
    for _ in range(3):
        photos_data = get_photos_from_google_photo_api(
            access_token, page_size=100, next_page_token=next_token
        )
        if not photos_data.get("mediaItems"):
            logging.info("No mediaItems found in the response.")
            return {"message": "No media items found"}

        for photo in photos_data["mediaItems"]:
            if not should_process_photo(photo):
                continue
            shot_at_datetime = datetime.strptime(
                photo.get("mediaMetadata", {}).get("creationTime"), "%Y-%m-%dT%H:%M:%S%z"
            )
            # photoオブジェクトに下記の3行の処理が渡されていくイメージ
            if has_fetched_before and shot_at_datetime <= latest_photo_datetime:
                update_user_doc_status(user_id, db)
                return {"message": "Successfully processed less 8 photos"}

            predicted, content = classify_image(
                photo["baseUrl"],
                interpreter,
                input_details,
                output_details,
            )

            # データ後処理

            # predictedがNoneでないことを確認してからリストをインデックス参照する
            if (
                predicted is not None and content and classes[predicted] in classes[:-1]
            ):  # "other" is excluded
                image_url = save_to_cloud_storage(content, f"{uuid.uuid4()}.jpg", bucket, user_id)
                save_to_firestore(
                    image_url,
                    shot_at_datetime,
                    user_id,
                    db,
                )

                logging.info(f"photo_count: {photo_count}")
                photo_count += 1  # 写真を正常に保存したらカウントを1増やす
                # 8枚の写真が処理されたらclassifyPhotosStatusを更新
                if photo_count == 8:
                    logging.info(f"classifyPhotosStatus: {READY_FOR_USE}")
                    update_user_doc_status(user_id, db)

        next_token = photos_data.get("nextPageToken")
        if not next_token:
            break

    return {"message": "Successfully processed photos"}


def save_image(user_id: str, access_token: str, db: Any, storage_client: Any) -> dict[str, str]:
    authenticate_user(access_token, user_id)
    process_images(access_token, user_id, db, storage_client)
    return {"message": "Successfully save image"}
