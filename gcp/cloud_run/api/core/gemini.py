# Standard Library
import logging
import os
from io import BytesIO
from typing import Any

# Third Party Library
import google.generativeai as genai
from PIL import Image


def categorize_from_gemini_api(
    photo_data: bytes,
) -> str:
    logging.info(f"Preparing to categorize from gemini api")

    GOOGLE_API_KEY = "AIzaSyCM1p4Ep_eYimLBX0kpJUeyvu7sE-y42VA"

    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel("gemini-1.5-flash")

    # バイトデータをBytesIOオブジェクトに変換
    img_data = BytesIO(photo_data)
    img = Image.open(img_data)

    response = model.generate_content(
        [
            "画像の飲食物は、ラーメン/カフェ/和食/洋食/エスニック/飲食物ではない のいずれに当てはまるか単語で答えよ",
            img,
        ],
        stream=True,
    )
    response.resolve()

    logging.info(f"response.text: , {response.text}")

    return response.text
