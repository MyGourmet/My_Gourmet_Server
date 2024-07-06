# Standard Library
import logging
import uuid
from datetime import datetime
from typing import Any, List

# Third Party Library
import googlemaps
import requests  # type: ignore
from fastapi import FastAPI  # type: ignore

logging.basicConfig(level=logging.INFO)
# First Party Library
# logging.basicConfig(level=logging.ERROR)
from api.core.auth import update_user_doc_status
from api.core.data_class import OpeningHours, StoreData
from api.cruds.firestore import save_to_firestore
from api.cruds.gcs import save_to_cloud_storage

app = FastAPI()


def get_place_details(place_id: str, api_key: str):
    gmaps = googlemaps.Client(key=api_key)
    details = gmaps.place(place_id=place_id, language="ja")
    return details["result"]


def format_time(time_str):
    return f"{time_str[:2]}:{time_str[2:]}"


def format_opening_hours_by_day(opening_hours):
    days = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]
    day_periods = {day: [] for day in days}

    if "periods" in opening_hours:
        for period in opening_hours["periods"]:
            open_day = period["open"]["day"]
            close_day = period["close"]["day"]
            open_time = format_time(period["open"]["time"])
            close_time = format_time(period["close"]["time"])

            if open_day == close_day:
                if open_time != "00:00" or close_time != "00:00":
                    day_periods[days[open_day]].append(f"{open_time}-{close_time}")
            else:
                if open_time != "00:00":
                    day_periods[days[open_day]].append(f"{open_time}-24:00")
                if close_time != "00:00":
                    day_periods[days[close_day]].append(f"00:00-{close_time}")

    return day_periods


def find_nearby_restaurants(
    lat: float, lon: float, api_key: str, user_id: str, photo_id: str, db: Any, storage_client: Any
) -> StoreData:
    gmaps = googlemaps.Client(key=api_key)
    places = gmaps.places_nearby(location=(lat, lon), radius=15, type="restaurant", language="ja")
    # logging.info("Nearby Restaurants and Details:")
    for place in places["results"]:
        details = get_place_details(place["place_id"], api_key)
        name = details.get("name")
        address = details.get("formatted_address")
        phone_number = details.get("formatted_phone_number")
        website = details.get("website")
        opening_hours = details.get("opening_hours", {})

        # logging.info(f"- {name}")
        # logging.info(f"  Address: {address}")
        # logging.info(f"  Phone Number: {phone_number}")
        # logging.info(f"  Website: {website}")
        # logging.info(f"  Rating: {rating}")

        if "periods" in opening_hours:
            formatted_hours = format_opening_hours_by_day(opening_hours)
            sunday_hours = (
                ", ".join(formatted_hours["Sunday"]) if formatted_hours["Sunday"] else "Closed"
            )
            monday_hours = (
                ", ".join(formatted_hours["Monday"]) if formatted_hours["Monday"] else "Closed"
            )
            tuesday_hours = (
                ", ".join(formatted_hours["Tuesday"]) if formatted_hours["Tuesday"] else "Closed"
            )
            wednesday_hours = (
                ", ".join(formatted_hours["Wednesday"])
                if formatted_hours["Wednesday"]
                else "Closed"
            )
            thursday_hours = (
                ", ".join(formatted_hours["Thursday"]) if formatted_hours["Thursday"] else "Closed"
            )
            friday_hours = (
                ", ".join(formatted_hours["Friday"]) if formatted_hours["Friday"] else "Closed"
            )
            saturday_hours = (
                ", ".join(formatted_hours["Saturday"]) if formatted_hours["Saturday"] else "Closed"
            )
        else:
            sunday_hours = "Closed"
            monday_hours = "Closed"
            tuesday_hours = "Closed"
            wednesday_hours = "Closed"
            thursday_hours = "Closed"
            friday_hours = "Closed"
            saturday_hours = "Closed"

        image_urls: List[str] = []
        if "photos" in details:
            for photo in details["photos"]:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={api_key}"
                # logging.info(f"  Image URL: {photo_url}")

                response = requests.get(photo_url)
                response.raise_for_status()
                image_data = response.content

                uploaded_image_url = save_to_cloud_storage(
                    image_data, f"{uuid.uuid4()}.jpg", place["place_id"], storage_client
                )
                logging.info("uploaded_image_url", uploaded_image_url)

                image_urls.append(uploaded_image_url)

        opening_hours = OpeningHours(
            mondayHours=monday_hours,
            tuesdayHours=tuesday_hours,
            wednesdayHours=wednesday_hours,
            thursdayHours=thursday_hours,
            fridayHours=friday_hours,
            saturdayHours=saturday_hours,
            sundayHours=sunday_hours,
        )

        store_data = StoreData(
            store_id=place["place_id"],
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            name=name,
            address=address,
            phoneNumber=phone_number if phone_number else "",
            website=website if website else "",
            openingHours=opening_hours,
            imageUrls=image_urls,
        )

        save_to_firestore(store_data, photo_id, user_id, db)

    return store_data


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
    # access_token: str,
    lat: float,
    lon: float,
    photo_id: str,
    db: Any,
    storage_client: Any,
) -> dict[str, str]:
    # authenticate_user(access_token, user_id)

    # 本処理
    api_key = "AIzaSyA0_ky7Sj1pl8QB_xvzbmebvo1l1JwqL5M"
    # ここはenvで持たせるように修正

    process_image(lat, lon, api_key, user_id, photo_id, db, storage_client)

    # Firestoreの更新ロジック
    update_user_doc_status(user_id, db)
    return {"message": "Successfully processed photos"}
