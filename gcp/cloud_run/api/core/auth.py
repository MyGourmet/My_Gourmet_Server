# Standard Library
import logging
from typing import Any

# Third Party Library
from fastapi import HTTPException  # type: ignore

READY_FOR_USE = "readyForUse"


def authenticate_user(access_token: str, user_id: str) -> None:
    if not access_token:
        raise HTTPException(status_code=401, detail="AccessToken not provided")
    if not user_id:
        raise HTTPException(status_code=400, detail="userId not provided")
    logging.info(f"Processing saveImage request for user: {user_id} with accessToken: [REDACTED]")


def update_user_doc_status(user_id: str, db: Any) -> None:
    db.collection("users").document(user_id).update({"classifyPhotosStatus": READY_FOR_USE})
