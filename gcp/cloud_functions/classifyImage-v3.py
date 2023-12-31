import json
import logging
import requests
from typing import Optional, Dict, Any, Tuple
from google.cloud import storage
import tempfile
import tensorflow as tf
import os
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
from firebase_functions import https_fn
import firebase_admin
from firebase_admin import firestore
import traceback

# ロガーの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

# Firebaseの初期化
app = firebase_admin.initialize_app()
db = firestore.client()


def get_photos_from_google_photo_api(
    access_token: str, page_size: int = 50, next_page_token: Optional[str] = None
) -> Dict[str, Any]:
    try:
        search_request_data = {"pageSize": page_size}
        if next_page_token:
            search_request_data["pageToken"] = next_page_token

        response = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {access_token}"},
            json=search_request_data,
            timeout=10,  # タイムアウトの設定
        )
        response.raise_for_status()  # HTTPエラーをチェック
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return {}  #


def classify_image(
    url: str,
    interpreter: tf.lite.Interpreter,
    input_details: Any,
    output_details: Any,
    image_size: int = 224,
) -> Tuple[Optional[int], Optional[bytes]]:
    try:
        response = requests.get(url, timeout=10)  # タイムアウトの設定
        response.raise_for_status()
        if response.status_code != 200:
            return None, None

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_local_path = temp_file.name
            temp_file.write(response.content)

        img = load_img(temp_local_path, target_size=(image_size, image_size))
        x = img_to_array(img)
        x /= 255.0
        x = np.expand_dims(x, axis=0)

        interpreter.set_tensor(input_details[0]["index"], x)
        interpreter.invoke()

        result = interpreter.get_tensor(output_details[0]["index"])
        predicted = result.argmax()

        os.remove(temp_local_path)  # 一時ファイルの削除
        return predicted, response.content
    except Exception as e:
        logging.error(f"Error in classify_image: {e}")
        return None, None


def save_to_cloud_storage(
    content: bytes, filename: str, bucket: storage.Bucket, user_id: str, class_name: str
) -> None:
    prefix = f"photo-jp-my-gourmet-image-classification-2023-08/{user_id}/{class_name}/"
    blob = bucket.blob(prefix + filename)
    blob.upload_from_string(content)


@https_fn.on_call()
def handler(req: https_fn.CallableRequest) -> Optional[Dict[str, Any]]:
    try:
        logging.info("Handler function started.")
        access_token: str = req.data.get("access_token", "no_access_token")
        if access_token == "no_access_token":
            logging.error("Access Token not provided")
            return {"error": "Access Token not provided"}

        user_id: str = req.data.get("userId", "no_user_id")
        if user_id == "no_user_id":
            logging.error("User ID not provided")
            return {"error": "User ID not provided"}

        storage_client = storage.Client()
        bucket = storage_client.bucket("my-gourmet-160fb.appspot.com")

        image_size = 224
        model_bucket_name = "model-jp-my-gourmet-image-classification-2023-08"
        model_bucket = storage_client.bucket(model_bucket_name)
        _, model_local_path = tempfile.mkstemp()
        blob_model = model_bucket.blob("gourmet_cnn_vgg_final.tflite")
        blob_model.download_to_filename(model_local_path)
        interpreter = tf.lite.Interpreter(model_path=model_local_path)
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        classes = ["ramen", "japanese_food", "international_cuisine", "cafe", "other"]

        next_token: Optional[str] = None
        for _ in range(1):  # ループを1回だけ実行する
            photos_data = get_photos_from_google_photo_api(
                access_token, page_size=50, next_page_token=next_token
            )
            if not photos_data.get("mediaItems"):
                logging.info("No mediaItems found in the response.")
                break

            for photo in photos_data["mediaItems"]:
                if (
                    photo["mimeType"] != "image/jpeg"
                    or "screenshot" in photo["filename"].lower()
                ):
                    continue  # JPEG形式でない、またはスクリーンショットを含む画像を除外
                predicted, content = classify_image(
                    photo["baseUrl"],
                    interpreter,
                    input_details,
                    output_details,
                    image_size,
                )
                if (
                    content and classes[predicted] in classes[:-1]
                ):  # "other" is excluded
                    save_to_cloud_storage(
                        content, photo["filename"], bucket, user_id, classes[predicted]
                    )

            next_token = photos_data.get("nextPageToken")
            if not next_token:
                break

        os.remove(model_local_path)

        # Firestore logging
        classify_logs_ref: firestore.CollectionReference = db.collection("classifylogs")
        query_ref: firestore.Query = classify_logs_ref.where("userId", "==", user_id)
        query_results = query_ref.stream()
        new_state = "completed"

        for doc in query_results:
            doc.reference.update({"state": new_state})

        logging.info("Handler function successfully completed.")

    except Exception as e:
        logging.error("An error occurred: %s", str(e))
        logging.error("Stack Trace:", exc_info=True)
        return {"error": str(e)}

    return None
