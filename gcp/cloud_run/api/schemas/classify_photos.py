# Standard Library
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union

# Third Party Library
import numpy as np  # type: ignore
import requests  # type: ignore
import tensorflow as tf  # type: ignore
from fastapi import FastAPI, HTTPException  # type: ignore
from google.cloud import storage  # type: ignore
from tensorflow.keras.preprocessing.image import (  # type: ignore
    img_to_array,
    load_img,
)

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.ERROR)


app = FastAPI()

# Constants
MODEL_BUCKET_NAME = os.getenv(
    "MODEL_BUCKET_NAME", "model-jp-my-gourmet-image-classification-2023-08"
)
GCS_PREFIX = "photo-jp-my-gourmet-image-classification-2023-08"
PROJECT = os.getenv("GCP_PROJECT", "default-project")
READY_FOR_USE = "readyForUse"


# 認証処理
def authenticate_user(access_token: str, user_id: str):
    if not access_token:
        raise HTTPException(status_code=401, detail="AccessToken not provided")
    if not user_id:
        raise HTTPException(status_code=400, detail="userId not provided")
    logging.info(
        f"Processing saveImage request for user: {user_id} with accessToken: [REDACTED]"
    )


def get_photos_from_google_photo_api(
    access_token: str, page_size: int, next_page_token: Optional[str] = None
) -> Dict[str, Any]:
    logging.info(
        f"Fetching photos with pageSize={page_size} and nextPageToken={next_page_token}"
    )
    try:
        search_request_data = {"pageSize": page_size}
        if next_page_token:
            search_request_data["pageToken"] = next_page_token

        response = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {access_token}"},
            json=search_request_data,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return {}


# 画像分類の初期化
def initialize_classifier(storage_client):
    bucket = storage_client.bucket(PROJECT)
    model_bucket = storage_client.bucket(MODEL_BUCKET_NAME)
    _, model_local_path = tempfile.mkstemp()
    blob_model = model_bucket.blob("gourmet_cnn_vgg_final.tflite")
    blob_model.download_to_filename(model_local_path)
    interpreter = tf.lite.Interpreter(model_path=model_local_path)
    interpreter.allocate_tensors()
    return (
        bucket,
        interpreter,
        interpreter.get_input_details(),
        interpreter.get_output_details(),
    )


def classify_image(
    url: str,
    interpreter: tf.lite.Interpreter,
    input_details: Any,
    output_details: Any,
) -> Tuple[Optional[int], Optional[bytes]]:
    logging.info(f"Starting classification for image: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching image: {e}",
        )

    try:
        _, temp_local_path = tempfile.mkstemp()
        with open(temp_local_path, "wb") as f:
            f.write(response.content)

        img = load_img(temp_local_path, target_size=(224, 224))
        x = img_to_array(img)
        x /= 255.0
        x = np.expand_dims(x, axis=0)

        interpreter.set_tensor(input_details[0]["index"], x)
        interpreter.invoke()

        result = interpreter.get_tensor(output_details[0]["index"])
        predicted = result.argmax()

        return predicted, response.content

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error processing image: {e}",
        )

    finally:
        if os.path.exists(temp_local_path):
            os.remove(temp_local_path)


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
        image_url = blob.public_url
        return image_url

    except Exception as e:
        logging.error(f"Failed to upload image to Cloud Storage: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while saving to Firestore: {e}",
        )


def save_to_firestore(image_url: str, shot_at: datetime, user_id: str, db):
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


def update_user_doc_status(user_id: str, db):
    db.collection("users").document(user_id).update(
        {"classifyPhotosStatus": READY_FOR_USE}
    )


def get_latest_document_id(user_id: str, db) -> str:
    photos_ref = db.collection("users").document(user_id).collection("photos")
    # IDに基づいて最新のドキュメントを取得
    latest_photos = (
        photos_ref.order_by("__name__", direction="DESCENDING").limit(1).get()
    )
    latest_photo_id = latest_photos[0].id  # 最新のドキュメントIDを取得
    return latest_photo_id


def filter_photo(
    photo,
) -> Union[False, datetime]:
    """写真が処理対象かどうかを判断する。"""
    if "screenshot" in photo["filename"].lower():
        return False
    shot_at = photo.get("mediaMetadata", {}).get("creationTime")
    if not shot_at:
        logging.info(
            f"No shot_at time for photo {photo['filename']}. Skipping."
        )
        return False
    return datetime.strptime(shot_at, "%Y-%m-%dT%H:%M:%S%z")


# 以下の関数は、取得した最新のドキュメントIDから日時情報を抽出します
def extract_datetime_from_id(document_id: str) -> datetime:
    # ドキュメントIDから日時情報を抽出
    # 形式: 'YYYYMMDD_HHMMSS'
    date_time_str = document_id[:8] + " " + document_id[9:15]
    # 文字列からdatetimeオブジェクトを作成
    date_time_obj = datetime.strptime(date_time_str, "%Y%m%d %H%M%S")
    return date_time_obj


def process_images(access_token: str, user_id: str, db, storage_client):
    bucket, interpreter, input_details, output_details = initialize_classifier(
        storage_client
    )

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
        latest_photo_datetime = latest_photo_datetime.replace(
            tzinfo=timezone.utc
        )

    next_token: Optional[str] = None
    for _ in range(1):
        photos_data = get_photos_from_google_photo_api(
            access_token, page_size=50, next_page_token=next_token
        )
        if not photos_data.get("mediaItems"):
            logging.info("No mediaItems found in the response.")
            return {"message": "No media items found"}

        for photo in photos_data["mediaItems"]:
            shot_at_datetime = filter_photo(photo)
            if has_fetched_before and shot_at_datetime < latest_photo_datetime:
                update_user_doc_status(user_id, db)
                return {"message": "Successfully processed photos"}

            if not shot_at_datetime:
                continue

            predicted, content = classify_image(
                photo["baseUrl"],
                interpreter,
                input_details,
                output_details,
            )
            # predictedがNoneでないことを確認してからリストをインデックス参照する
            if (
                predicted is not None
                and content
                and classes[predicted] in classes[:-1]
            ):  # "other" is excluded
                image_url = save_to_cloud_storage(
                    content, f"{uuid.uuid4()}.jpg", bucket, user_id
                )
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


def save_image(user_id: str, access_token: str, db, storage_client):
    authenticate_user(access_token, user_id)
    process_images(access_token, user_id, db, storage_client)
    return {"message": "Successfully save image"}
