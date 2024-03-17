# Standard Library
from typing import Any

# Third Party Library
from fastapi import APIRouter, Depends, Request  # type: ignore
from firebase_admin import firestore  # type: ignore
from google.cloud import storage

# First Party Library
from api.schemas.classify_photos import save_image
from api.schemas.update_user_status import update_user_status

router = APIRouter()


# Firestore クライアントの取得
def get_firestore_client() -> Any:
    return firestore.client()


def get_storage_client() -> Any:
    return storage.Client()


@router.post("/classifyPhotos")
async def save_image_endpoint(
    request: Request,
    db: Any = Depends(get_firestore_client),
    storage_client: Any = Depends(get_storage_client),
) -> dict[str, str]:
    body = await request.json()
    auth_header = request.headers.get("Authorization")
    access_token: str = (
        auth_header.split(" ")[1] if auth_header and auth_header.startswith("Bearer ") else None
    )
    user_id: str = body.get("userId")

    return save_image(
        user_id=user_id,
        access_token=access_token,
        db=db,
        storage_client=storage_client,
    )


@router.post("/updateUserStatus")
async def update_user_status_endpoint(
    request: Request,
    db: Any = Depends(get_firestore_client),
    storage_client: Any = Depends(get_storage_client),
) -> dict[str, str]:
    # リクエストからデータを抽出
    body = await request.json()
    auth_header = request.headers.get("Authorization")
    access_token = (
        auth_header.split(" ")[1] if auth_header and auth_header.startswith("Bearer ") else None
    )
    user_id = body.get("userId")

    return update_user_status(user_id=user_id, access_token=access_token, db=db)