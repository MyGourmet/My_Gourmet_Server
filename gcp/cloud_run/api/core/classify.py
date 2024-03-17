# Standard Library
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# Third Party Library
import numpy as np  # type: ignore
import requests  # type: ignore
import tensorflow as tf  # type: ignore
from fastapi import HTTPException  # type: ignore
from tensorflow.keras.preprocessing.image import img_to_array, load_img  # type: ignore

# Constants
MODEL_BUCKET_NAME = os.getenv(
    "MODEL_BUCKET_NAME", "model-jp-my-gourmet-image-classification-2023-08"
)
PROJECT = os.getenv("GCP_PROJECT", "default-project")


# 画像分類の初期化
def initialize_classifier(
    storage_client: Any,
) -> Tuple[Any, Any, List[Dict[str, Any]], List[Dict[str, Any]]]:
    bucket = storage_client.bucket(PROJECT)
    model_bucket = storage_client.bucket(MODEL_BUCKET_NAME)
    _, model_local_path = tempfile.mkstemp()
    blob_model = model_bucket.blob("gourmet_cnn_vgg_final.tflite")
    blob_model.download_to_filename(model_local_path)
    interpreter = tf.lite.Interpreter(model_path=model_local_path)
    interpreter.allocate_tensors()
    return (
        bucket,
        interpreter,
        interpreter.get_input_details(),
        interpreter.get_output_details(),
    )


def classify_image(
    url: str,
    interpreter: tf.lite.Interpreter,
    input_details: Any,
    output_details: Any,
) -> Tuple[Optional[int], Optional[bytes]]:
    logging.info(f"Starting classification for image: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Error fetching image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching image: {e}",
        )

    try:
        _, temp_local_path = tempfile.mkstemp()
        with open(temp_local_path, "wb") as f:
            f.write(response.content)

        img = load_img(temp_local_path, target_size=(224, 224))
        x = img_to_array(img)
        x /= 255.0
        x = np.expand_dims(x, axis=0)

        interpreter.set_tensor(input_details[0]["index"], x)
        interpreter.invoke()

        result = interpreter.get_tensor(output_details[0]["index"])
        predicted = result.argmax()

        return predicted, response.content

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error processing image: {e}",
        )

    finally:
        if os.path.exists(temp_local_path):
            os.remove(temp_local_path)
