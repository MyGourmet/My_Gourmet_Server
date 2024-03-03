# Standard Library
import logging

# Third Party Library
from firebase_admin import auth, exceptions, initialize_app  # type: ignore;
from firebase_functions import https_fn  # type: ignore

app = initialize_app()

# db = firestore.client()

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.ERROR)


@https_fn.on_call()
def delete_user_account(req: https_fn.CallableRequest):
    try:
        # IDトークンを検証
        userId = req.data.get("userId", "no_userId")
        logging.info("userId: %s", userId)

        # UIDの存在を確認
        if not userId:
            return {"error": "Invalid token: userId not found"}, 403

        # 指定されたユーザーIDのアカウントを削除
        auth.delete_user(userId)
        logging.info("Successfully deleted user")
        return {"message": "User account successfully deleted."}
    except ValueError as e:
        # トークンの検証でエラー（トークンが無効な場合）
        logging.error("ValueError: %s", e)
        return {"error": "Invalid userId"}, 400
    except exceptions.FirebaseError as e:
        # Firebase Auth関連のエラー
        logging.error("FirebaseError: %s", e)
        return {"error": "Error deleting user"}, 500
