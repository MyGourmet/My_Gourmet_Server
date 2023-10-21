import firebase_admin
from firebase_admin import firestore
import time  # time モジュールをインポート
from firebase_functions import https_fn
from firebase_admin import initialize_app

# 初期化（特定の資格情報なし）
firebase_admin.initialize_app()

# Firestore クライアントの初期化
db = firestore.client()


@https_fn.on_call()
def update_classify_log_by_user_id(req: https_fn.CallableRequest):
    # def update_classify_log_by_user_id(request):
    access_token = req.data.get("name", "no_access_token")
    if access_token == "no_access_token":
        print("Error: Access Token not provided")
        return {"error": "Access Token not provided"}
    print("access_token")
    print(access_token)

    userId = req.data.get("userId", "no_access_token")
    if userId == "no_access_token":
        print("Error: Access Token not provided")
        return {"error": "Access Token not provided"}
    print("userId")
    print(userId)

    time.sleep(5)  # 5秒待つ

    # コレクションの参照
    classify_logs_ref = db.collection("classifylogs")

    # userId が access_token であるドキュメントを探す
    query_ref = classify_logs_ref.where("userId", "==", userId)

    # クエリを実行
    query_results = query_ref.stream()

    new_state = "completed"  # 新しい状態

    for doc in query_results:
        # ドキュメントを更新
        doc.reference.update({"state": new_state})

    # 何も返さない
    return None

    # return f"State fields for userId xtyspsWTPyUSDb92km3DKs8q6Qf2 updated to: {new_state}"
