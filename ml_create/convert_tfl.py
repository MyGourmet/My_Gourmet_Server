import tensorflow as tf

# Load the model.
model = tf.keras.models.load_model("gourmet_cnn_vgg_final.h5")

# Convert the model.
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Save the model.
with open("gourmet_cnn_vgg_final.tflite", "wb") as f:
    f.write(tflite_model)
