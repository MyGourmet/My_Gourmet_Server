import functions_framework


@functions_framework.http
def classify_photos(request):
    try:
        """HTTP Cloud Function.
        Args:
            request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
        Returns:
            The response text, or any set of values that can be turned into a
            Response object using `make_response`
            <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
        """
        print("Handler function started.")
        access_token = req.data.get("accessToken", "no_access_token")
        if access_token == "no_access_token":
            print("Error: Access Token not provided")
            return {"error": "Access Token not provided"}
        print("access_token: ")
        print(access_token)

        userId = req.data.get("userId", "no_user_id")
        if userId == "no_user_id":
            print("Error: userId not provided")
            return {"error": "userId not provided"}
        print("userId")
        print(userId)

        # コレクションの参照
        users_ref = db.collection("users")

        # ドキュメントIDを使用して特定のドキュメントを参照
        user_doc_ref = users_ref.document(userId)  # userIdはドキュメントID

        new_state = "readyForUser"

        # ドキュメントを更新
        user_doc_ref.update({"state": new_state})

        print("Handler function successfully completed.")

        return "Hello {}!".format(name)

    except Exception as e:
        # エラーが発生した場合にスタックトレースをログに出力
        print("An error occurred:", str(e))
        print(traceback.format_exc())  # エラーのスタックトレースを出力

        # エラーメッセージを返す
        return {"error": str(e)}

    # 何も返さない
    return None
