from datetime import datetime
import json
import uuid
import requests
from google.cloud import storage
import tempfile
import tensorflow as tf
import os
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
from firebase_functions import https_fn
from firebase_admin import firestore, initialize_app
import traceback

app = initialize_app()

db = firestore.client()


def get_photos_from_google_photo_api(access_token, page_size=50, next_page_token=None):
    search_request_data = {"pageSize": page_size}
    if next_page_token:
        search_request_data["pageToken"] = next_page_token

    response = requests.post(
        "https://photoslibrary.googleapis.com/v1/mediaItems:search",
        headers={"Authorization": "Bearer %s" % access_token},
        json=search_request_data,
    )
    return response.json()


def classify_image(url, interpreter, input_details, output_details, image_size=224):
    response = requests.get(url)
    if response.status_code != 200:
        return None, None
    _, temp_local_path = tempfile.mkstemp()
    with open(temp_local_path, "wb") as f:
        f.write(response.content)

    img = load_img(temp_local_path, target_size=(image_size, image_size))
    x = img_to_array(img)
    x /= 255.0
    x = np.expand_dims(x, axis=0)

    interpreter.set_tensor(input_details[0]["index"], x)
    interpreter.invoke()

    result = interpreter.get_tensor(output_details[0]["index"])
    predicted = result.argmax()

    os.remove(temp_local_path)

    return predicted, response.content


def save_to_cloud_storage(content, filename, bucket, user_id, db):
    try:
        # Cloud Storageに画像を保存
        prefix = f"photo-jp-my-gourmet-image-classification-2023-08/{user_id}/"
        blob = bucket.blob(prefix + filename)
        blob.upload_from_string(content)
        blob.make_public()  # 画像のURLを公開状態にする

        # Firestoreに保存するデータを作成
        photo_data = {
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "userId": user_id,
            "url": blob.public_url,
            "otherUrls": [],
            "tags": [],
            "storeId": None,
            "areaStoreIds": [],
        }

        # Firestoreの`users`コレクション内の対応するユーザードキュメントの`photos`サブコレクションにデータを保存
        user_ref = db.collection("users").document(user_id)
        photo_id = str(uuid.uuid4())  # ランダムなドキュメントIDを生成
        user_ref.collection("photos").document(photo_id).set(photo_data)
        return True, "Upload and Firestore update successful"

    except Exception as e:
        # エラーログを出力
        error_message = (
            f"An error occurred while saving to Cloud Storage or Firestore: {str(e)}"
        )
        print(error_message)
        return False, error_message


@https_fn.on_call()
def handler(req: https_fn.CallableRequest):
    try:
        # 関数の最初にログを出力
        print("Handler function started.")
        access_token = req.data.get("accessToken", "no_access_token")
        if access_token == "no_access_token":
            print("Error: Access Token not provided")
            return {"error": "Access Token not provided"}
        print("access_token: ")
        print(access_token)

        userId = req.data.get("userId", "no_user_id")
        if userId == "no_user_id":
            print("Error: userId not provided")
            return {"error": "userId not provided"}
        print("userId")
        print(userId)

        storage_client = storage.Client()
        bucket_name = "my-gourmet-160fb.appspot.com"
        bucket = storage_client.bucket(bucket_name)

        # Setup for Image Classification
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

        next_token = None
        for _ in range(1):
            photos_data = get_photos_from_google_photo_api(
                access_token, next_page_token=next_token
            )
            if not photos_data.get("mediaItems"):
                print("Error: No mediaItems found in the response.")
                break

            for photo in photos_data["mediaItems"]:
                if (
                    photo["mimeType"] != "image/jpeg"
                    or "screenshot" in photo["filename"].lower()
                ):
                    continue
                predicted, content = classify_image(
                    photo["baseUrl"], interpreter, input_details, output_details
                )
                if content and classes[predicted] in [
                    "ramen",
                    "japanese_food",
                    "international_cuisine",
                    "cafe",
                ]:
                    save_to_cloud_storage(
                        content, photo["filename"], bucket, userId, db
                    )

            # 次のページのtokenを取得
            next_token = photos_data.get("nextPageToken")
            if not next_token:
                break

        os.remove(model_local_path)

        # コレクションの参照
        users_ref = db.collection("users")

        # ドキュメントIDを使用して特定のドキュメントを参照
        user_doc_ref = users_ref.document(userId)  # userIdはドキュメントID

        new_state = "completed"  # 新しい状態

        # ドキュメントを更新
        user_doc_ref.update({"state": new_state})

        print("Handler function successfully completed.")

    except Exception as e:
        # エラーが発生した場合にスタックトレースをログに出力
        print("An error occurred:", str(e))
        print(traceback.format_exc())  # エラーのスタックトレースを出力

        # エラーメッセージを返す
        return {"error": str(e)}

    # 何も返さない
    return None
