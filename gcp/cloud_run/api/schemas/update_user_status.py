# Standard Library
import logging

# Third Party Library
from fastapi import FastAPI, HTTPException  # type: ignore

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.ERROR)


app = FastAPI()


def update_user_status(user_id: str, access_token: str, db):
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="アクセストークンが提供されていないか無効です",
        )

    if not user_id:
        raise HTTPException(
            status_code=400, detail="userIdが提供されていません"
        )

    # Firestoreの更新ロジック
    users_ref = db.collection("users")
    logging.info(f"users_ref={users_ref}")

    user_doc_ref = users_ref.document(user_id)
    logging.info(f"user_doc_ref={user_doc_ref}")

    new_state = "ready_for_use"
    user_doc_ref.update({"classifyPhotosStatus": new_state})
    return {"message": "Successfully processed photos"}
