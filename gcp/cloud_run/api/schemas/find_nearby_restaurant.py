# Standard Library
import logging
import uuid
from datetime import datetime
from typing import Any, List

# Third Party Library
import googlemaps
import requests  # type: ignore
from fastapi import FastAPI  # type: ignore

# First Party Library
from api.core.romaji_conversion_dict import romaji_conversion_dict

logging.basicConfig(level=logging.INFO)
# First Party Library
# logging.basicConfig(level=logging.ERROR)
from api.core.auth import update_user_doc_status
from api.core.data_class import StoreData
from api.cruds.firestore import save_store_data_to_firestore
from api.cruds.gcs import save_store_photo_to_cloud_storage

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


def get_formatted_hours(opening_hours: dict) -> dict:
    formatted_hours = format_opening_hours_by_day(opening_hours)
    hours = {
        "sunday_hours": (
            ", ".join(formatted_hours["Sunday"]) if formatted_hours["Sunday"] else "Closed"
        ),
        "monday_hours": (
            ", ".join(formatted_hours["Monday"]) if formatted_hours["Monday"] else "Closed"
        ),
        "tuesday_hours": (
            ", ".join(formatted_hours["Tuesday"]) if formatted_hours["Tuesday"] else "Closed"
        ),
        "wednesday_hours": (
            ", ".join(formatted_hours["Wednesday"]) if formatted_hours["Wednesday"] else "Closed"
        ),
        "thursday_hours": (
            ", ".join(formatted_hours["Thursday"]) if formatted_hours["Thursday"] else "Closed"
        ),
        "friday_hours": (
            ", ".join(formatted_hours["Friday"]) if formatted_hours["Friday"] else "Closed"
        ),
        "saturday_hours": (
            ", ".join(formatted_hours["Saturday"]) if formatted_hours["Saturday"] else "Closed"
        ),
    }
    return hours


def extract_address_component(address_components, component_type):
    for component in address_components:
        if component_type in component["types"]:
            return component["long_name"]
    return None


def convert_to_romaji(text):
    return romaji_conversion_dict.get(text, text)


def find_nearby_restaurants(
    lat: float, lon: float, api_key: str, user_id: str, photo_id: str, db: Any, storage_client: Any
) -> StoreData:
    gmaps = googlemaps.Client(key=api_key)
    places = gmaps.places_nearby(location=(lat, lon), radius=15, type="restaurant", language="ja")

    # 初期化
    store_data = None

    for place in places["results"]:
        details = get_place_details(place["place_id"], api_key)
        name = details.get("name")
        address = details.get("formatted_address")

        address_components = details.get("address_components", [])

        prefecture = extract_address_component(address_components, "administrative_area_level_1")
        city = extract_address_component(address_components, "locality")
        country = extract_address_component(address_components, "country")

        romaji_prefecture = convert_to_romaji(prefecture) if prefecture else ""
        romaji_city = convert_to_romaji(city) if city else ""
        romaji_country = convert_to_romaji(country) if country else ""

        phone_number = details.get("formatted_phone_number")
        website = details.get("website")
        opening_hours = details.get("opening_hours", {})

        formatted_hours = (
            get_formatted_hours(opening_hours)
            if "periods" in opening_hours
            else {
                "sunday_hours": "Unknown",
                "monday_hours": "Unknown",
                "tuesday_hours": "Unknown",
                "wednesday_hours": "Unknown",
                "thursday_hours": "Unknown",
                "friday_hours": "Unknown",
                "saturday_hours": "Unknown",
            }
        )

        image_urls: List[str] = []
        if "photos" in details:
            for photo in details["photos"]:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={api_key}"
                response = requests.get(photo_url)
                response.raise_for_status()
                image_data = response.content

                uploaded_image_url = save_store_photo_to_cloud_storage(
                    image_data, f"{uuid.uuid4()}.jpg", place["place_id"], storage_client
                )
                logging.info(f"uploaded_image_url: {uploaded_image_url}")

                image_urls.append(uploaded_image_url)

        store_data = StoreData(
            store_id=place["place_id"],
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            name=name,
            address=address,
            city=romaji_city,
            prefecture=romaji_prefecture,
            country=romaji_country,
            phoneNumber=phone_number if phone_number else "",
            website=website if website else "",
            openingHours=formatted_hours,
            imageUrls=image_urls,
        )

        save_store_data_to_firestore(store_data, photo_id, user_id, db)

    if store_data is None:
        # 初期化されていない場合のデフォルト値
        store_data = StoreData(
            store_id="",
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            name="",
            address="",
            city="",
            prefecture="",
            country="",
            phoneNumber="",
            website="",
            openingHours={},
            imageUrls=[],
        )

    return store_data


def process_image(
    lat: float, lon: float, api_key: str, user_id: str, photo_id: str, db: Any, storage_client: Any
):
    try:
        logging.info(f"lat: {lat}")
        logging.info(f"lon: {lon}")
        find_nearby_restaurants(lat, lon, api_key, user_id, photo_id, db, storage_client)

    except (AttributeError, KeyError) as e:
        logging.error(f"Could not retrieve location data for {lat},{lon}: {e}. Skipping...")


def find_nearby_restaurant(
    user_id: str,
    lat: float,
    lon: float,
    photo_id: str,
    db: Any,
    storage_client: Any,
) -> dict[str, str]:
    # 本処理
    api_key = "AIzaSyA0_ky7Sj1pl8QB_xvzbmebvo1l1JwqL5M"
    # ここはenvで持たせるように修正

    process_image(lat, lon, api_key, user_id, photo_id, db, storage_client)

    # Firestoreの更新ロジック
    update_user_doc_status(user_id, db)
    return {"message": "Successfully processed photos"}
