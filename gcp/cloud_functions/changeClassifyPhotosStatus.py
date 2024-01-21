import functions_framework
from datetime import datetime
import json
import uuid
import requests
from google.cloud import storage
import tempfile
import tensorflow as tf
import os
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np
from firebase_functions import https_fn
from firebase_admin import firestore, initialize_app
import traceback

app = initialize_app()

db = firestore.client()

@functions_framework.http
def handler(req):
    try:
        print("Handler function started.")

        data = json.loads(req.data)
        access_token = req.headers.get('Authorization').split(' ').pop()
        if not access_token or access_token == "Bearer":
            print("Error: Access Token not provided")
            return {"error": "Access Token not provided"}, 401

        userId = data.get("userId", "no_user_id")
        if userId == "no_user_id":
            print("Error: userId not provided")
            return {"error": "userId not provided"}, 400

        print("userId")
        print(userId)

        users_ref = db.collection("users")
        user_doc_ref = users_ref.document(userId)
        new_state = "readyForUser"
        user_doc_ref.update({"classifyPhotosStatus": new_state})

        print("Handler function successfully completed.")
        return {"message": "Successfully updated"}, 200

    except Exception as e:
        print("An error occurred:", str(e))
        print(traceback.format_exc())
        return {"error": str(e)}, 500

    return None
