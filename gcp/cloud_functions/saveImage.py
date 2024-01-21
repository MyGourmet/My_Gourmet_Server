import functions_framework
from datetime import datetime
import json
import uuid
import logging
import requests
from google.cloud import storage
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import firestore
import traceback

# Firebaseの初期化
firebase_admin.initialize_app()
db = firestore.client()

# ロガーの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

def get_photos_from_google_photo_api(
    access_token: str, page_size: int = 10, next_page_token: Optional[str] = None
) -> Dict[str, Any]:
    try:
        search_request_data = {"pageSize": page_size}
        if next_page_token:
            search_request_data["pageToken"] = next_page_token

        response = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={"Authorization": f"Bearer {access_token}"},
            json=search_request_data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return {}

def save_to_cloud_storage(image_url, filename, bucket, user_id, db):
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
        photo_id = str(uuid.uuid4())
        user_ref.collection("photos").document(photo_id).set(photo_data)
        return True, "Firestore update successful"

    except Exception as e:
        logging.error(f"An error occurred while saving to Firestore: {e}")
        return False, str(e)

@functions_framework.http
def handler(req):
    try:
        logging.info("Handler function started.")        
        data = json.loads(req.data)
        access_token = req.headers.get('Authorization').split(' ').pop()
        if not access_token or access_token == "Bearer":
            logging.error("Error: Access Token not provided")
            return {"error": "Access Token not provided"}, 401

        user_id = data.get("userId", "no_user_id")
        if user_id == "no_user_id":
            logging.error("User ID not provided")
            return {"error": "userId not provided"}, 400

        storage_client = storage.Client()
        bucket = storage_client.bucket("my-gourmet-160fb.appspot.com")

        next_token: Optional[str] = None
        for _ in range(1):
            photos_data = get_photos_from_google_photo_api(
                access_token, page_size=50, next_page_token=next_token
            )
            if not photos_data.get("mediaItems"):
                logging.info("No mediaItems found in the response.")
                return {"message": "No media items found"}, 200

            for photo in photos_data["mediaItems"]:
                result, message = save_to_cloud_storage(
                    photo["baseUrl"], photo["filename"], bucket, user_id, db
                )
                if not result:
                    logging.error(message)
                    return {"error": message}, 500

            next_token = photos_data.get("nextPageToken")
            if not next_token:
                break

        users_ref = db.collection("users")
        query_ref = users_ref.document(user_id)
        query_ref.update({"classifyPhotosStatus": "readyForUse"})

        logging.info("Handler function successfully completed.")
        return {"message": "Successfully processed photos"}, 200

    except Exception as e:
        logging.error("An error occurred: %s", str(e))
        logging.error("Stack Trace:", exc_info=True)
        return {"error": str(e)}, 500

    return None
