# Standard Library
import logging
from typing import Any

# Third Party Library
from fastapi import APIRouter, Depends, Request  # type: ignore
from firebase_admin import firestore  # type: ignore
from google.cloud import storage  # type: ignore

# First Party Library
# from api.schemas.classify_photos import save_image
from api.schemas.categorize_food import categorize_food
from api.schemas.find_nearby_restaurant import find_nearby_restaurant
from api.schemas.update_user_status import update_user_status

router = APIRouter()


# Firestore クライアントの取得
def get_firestore_client() -> Any:
    return firestore.client()


def get_storage_client() -> Any:
    return storage.Client()


@router.post("/findNearbyRestaurants")
async def find_nearby_restaurants_endpoint(
    request: Request,
    db: Any = Depends(get_firestore_client),
    storage_client: Any = Depends(get_storage_client),
) -> dict[str, str]:
    body = await request.json()
    # TODO: アクセストークンではなく、
    # 特定のフィールドのIDを引数で受け取って、それが一致するかの確認処理を挟むようにする
    # userIdで良い？？
    user_id = body.get("userId")
    lat = body.get("lat")
    lon = body.get("lon")
    photo_id = body.get("photo_id")

    return find_nearby_restaurant(
        user_id=user_id,
        lat=lat,
        lon=lon,
        photo_id=photo_id,
        db=db,
        storage_client=storage_client,
    )


@router.post("/categorizeFood")
async def categorize_food_endpoint(
    request: Request,
    db: Any = Depends(get_firestore_client),
    storage_client: Any = Depends(get_storage_client),
) -> dict[str, str]:
    logging.info("categorize_food_endpoint start!!!")

    body = await request.json()

    user_id: str = body.get("userId")
    photo_id: str = body.get("photoId")
    photo: str = body.get("photo")

    return categorize_food(
        user_id=user_id,
        photo_id=photo_id,
        photo=photo,
        db=db,
        storage_client=storage_client,
    )


@router.post("/updateUserStatus")
async def update_user_status_endpoint(
    request: Request,
    db: Any = Depends(get_firestore_client),
    storage_client: Any = Depends(get_storage_client),
) -> dict[str, str]:
    body = await request.json()
    auth_header = request.headers.get("Authorization")
    access_token = (
        auth_header.split(" ")[1] if auth_header and auth_header.startswith("Bearer ") else None
    )
    user_id = body.get("userId")

    return update_user_status(user_id=user_id, access_token=access_token, db=db)
