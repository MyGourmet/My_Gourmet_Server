import googlemaps
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def get_geotagging(exif):
    if not exif:
        raise ValueError("No EXIF metadata found")

    geotagging = {}
    for idx, tag in TAGS.items():
        if tag == "GPSInfo":
            if idx not in exif:
                raise ValueError("No EXIF geotagging found")

            for key, val in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]

    return geotagging


def get_decimal_from_dms(dms, ref):
    degrees = float(dms[0])
    minutes = float(dms[1]) / 60.0
    seconds = float(dms[2]) / 3600.0

    if ref in ["S", "W"]:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds

    return degrees + minutes + seconds


def get_lat_lon(exif):
    try:
        geotags = get_geotagging(exif)
        lat = get_decimal_from_dms(geotags["GPSLatitude"], geotags["GPSLatitudeRef"])
        lon = get_decimal_from_dms(geotags["GPSLongitude"], geotags["GPSLongitudeRef"])
        return (lat, lon)
    except KeyError as e:
        raise KeyError(f"Key error during geotag extraction: {e}")


def find_nearby_restaurants(image_name, lat, lon, api_key):
    gmaps = googlemaps.Client(key=api_key)
    places = gmaps.places_nearby(location=(lat, lon), radius=20, type="restaurant")
    print(f"Image: {image_name}")
    print("Nearby Restaurants:")
    for place in places["results"]:
        print(f"- {place['name']}")
    print("\n")  # Print a new line for better readability between image outputs


def process_image(image_path, api_key):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if exif_data:
            lat, lon = get_lat_lon(exif_data)
            find_nearby_restaurants(image_path, lat, lon, api_key)
        else:
            print(f"No EXIF data found for {image_path}. Skipping...")
    except (AttributeError, KeyError) as e:
        print(f"Could not retrieve location data for {image_path}: {e}. Skipping...")


def main():
    # ここにGoogle Maps APIキーを設定してください。
    google_maps_api_key = "AIzaSyA0_ky7Sj1pl8QB_xvzbmebvo1l1JwqL5M"

    # 現在のディレクトリ内の全画像を処理します。
    for image_name in os.listdir("."):
        if image_name.lower().endswith((".png", ".jpg", ".jpeg")):
            print(f"Processing {image_name}...")
            process_image(image_name, google_maps_api_key)


if __name__ == "__main__":
    main()
