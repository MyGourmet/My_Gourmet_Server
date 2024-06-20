# Standard Library
import logging
import uuid
from datetime import datetime
from typing import Any, List

# Third Party Library
import googlemaps
import requests  # type: ignore
from fastapi import FastAPI, HTTPException  # type: ignore

logging.basicConfig(level=logging.INFO)
# First Party Library
# logging.basicConfig(level=logging.ERROR)
from api.core.auth import authenticate_user, update_user_doc_status
from api.core.data_class import StoreData
from api.cruds.firestore import save_to_firestore
from api.cruds.gcs import save_to_cloud_storage

app = FastAPI()


def get_place_details(place_id: str, api_key: str):
    gmaps = googlemaps.Client(key=api_key)
    details = gmaps.place(place_id=place_id, language="ja")
    return details["result"]


def find_nearby_restaurants(
    lat: float, lon: float, api_key: str, user_id: str, photo_id: str, db: Any, storage_client: Any
) -> StoreData:
    gmaps = googlemaps.Client(key=api_key)
    places = gmaps.places_nearby(location=(lat, lon), radius=15, type="restaurant", language="ja")
    print("Nearby Restaurants and Details:")
    for place in places["results"]:
        details = get_place_details(place["place_id"], api_key)
        name = details.get("name")
        address = details.get("formatted_address")
        phone_number = details.get("formatted_phone_number")
        website = details.get("website")
        rating = details.get("rating")
        opening_hours = details.get("opening_hours", {}).get("weekday_text", [])
        image_urls: List[str] = []

        logging.info(f"- {name}")
        logging.info(f"  Address: {address}")
        logging.info(f"  Phone Number: {phone_number}")
        logging.info(f"  Website: {website}")
        logging.info(f"  Rating: {rating}")
        logging.info(f"  Opening Hours: {'; '.join(opening_hours)}")

        # dataClassに値をセット
        if "photos" in details:
            for photo in details["photos"]:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={api_key}"
                logging.info(f"  Image URL: {photo_url}")

                response = requests.get(photo_url)
                response.raise_for_status()
                # 画像データを取得
                image_data = response.content

                uploaded_image_url = save_to_cloud_storage(
                    image_data, f"{uuid.uuid4()}.jpg", place["place_id"], storage_client
                )
                logging.info("uploaded_image_url", uploaded_image_url)

                # 公開URLを保存
                image_urls.append(uploaded_image_url)

        store_data = StoreData(
            store_id=place["place_id"],
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            name=name,
            phoneNumber=phone_number if phone_number else "",
            website=website if website else "",
            openingHours="; ".join(opening_hours),
            imageUrls=image_urls,
        )

        # dataClassに値をセット
        save_to_firestore(
            store_data,
            photo_id,
            user_id,
            db,
        )


def process_image(
    lat: float, lon: float, api_key: str, user_id: str, photo_id: str, db: Any, storage_client: Any
):
    try:
        logging.info("lat", lat)
        logging.info("lon", lon)
        find_nearby_restaurants(lat, lon, api_key, user_id, photo_id, db, storage_client)

    except (AttributeError, KeyError) as e:
        logging.error(f"Could not retrieve location data for {lat},{lon}: {e}. Skipping...")


def handler(
    user_id: str,
    access_token: str,
    lat: float,
    lon: float,
    photo_id: str,
    db: Any,
    storage_client: Any,
) -> dict[str, str]:
    authenticate_user(access_token, user_id)

    # 本処理
    api_key = "AIzaSyA0_ky7Sj1pl8QB_xvzbmebvo1l1JwqL5M"
    # ここはenvで持たせるように修正

    process_image(lat, lon, api_key, user_id, photo_id, db, storage_client)

    # Firestoreの更新ロジック
    update_user_doc_status(user_id, db)
    return {"message": "Successfully processed photos"}
