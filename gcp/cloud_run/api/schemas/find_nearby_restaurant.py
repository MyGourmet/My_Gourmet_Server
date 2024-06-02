# Standard Library
import logging
from datetime import datetime
from typing import Any

# Third Party Library
import googlemaps  # type: ignore
from fastapi import FastAPI, HTTPException  # type: ignore

logging.basicConfig(level=logging.INFO)
# First Party Library
# logging.basicConfig(level=logging.ERROR)
from api.core.auth import authenticate_user, update_user_doc_status
from api.core.data_class import StoreData
from api.cruds.firestore import save_to_firestore

app = FastAPI()


def get_place_details(place_id, api_key):
    gmaps = googlemaps.Client(key=api_key)
    details = gmaps.place(place_id=place_id, language="ja")
    return details["result"]


def find_nearby_restaurants(lat, lon, api_key, user_id, photo_id, db) -> StoreData:
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
        photo_urls = []

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
                photo_urls.append(photo_url)
                # 下記の処理を後ほど追加
                # image_url = save_to_cloud_storage(content, f"{uuid.uuid4()}.jpg", bucket, user_id)

        logging.info("\n")  # Print a new line for better readability between image outputs

        store_data = StoreData(
            store_id=place["place_id"],
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            name=name,
            phoneNumber=phone_number if phone_number else "",
            website=website if website else "",
            openingHours="; ".join(opening_hours),
            imageUrls=photo_urls,
        )

        # dataClassに値をセット
        save_to_firestore(
            store_data,
            photo_id,
            user_id,
            db,
        )


def process_image(lat, lon, api_key, user_id, photo_id, db):
    try:
        logging.info("lat", lat)
        logging.info("lon", lon)
        find_nearby_restaurants(lat, lon, api_key, user_id, photo_id, db)

    except (AttributeError, KeyError) as e:
        logging.error(f"Could not retrieve location data for {lat},{lon}: {e}. Skipping...")


def handler(
    user_id: str, access_token: str, lat: float, lon: float, photo_id: str, db: Any
) -> dict[str, str]:
    authenticate_user(access_token, user_id)

    # 本処理
    api_key = "AIzaSyA0_ky7Sj1pl8QB_xvzbmebvo1l1JwqL5M"
    logging.info("lat: %s", lat)
    logging.info("lon: %s", lon)
    logging.info("photo_id: %s", photo_id)
    process_image(lat, lon, api_key, user_id, photo_id, db)

    # Firestoreの更新ロジック
    update_user_doc_status(user_id, db)
    return {"message": "Successfully processed photos"}
