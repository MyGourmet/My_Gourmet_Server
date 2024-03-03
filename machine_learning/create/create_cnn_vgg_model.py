import gc
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Activation, Dropout, Flatten, Dense
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.applications import VGG16
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# GPU設定
gpus = tf.config.experimental.list_physical_devices("GPU")
if gpus:
    try:
        tf.config.experimental.set_visible_devices(gpus[0], "GPU")
        tf.config.experimental.set_memory_growth(gpus[0], True)
    except RuntimeError as e:
        print(e)

# デバイスのロギングを有効にする
tf.debugging.set_log_device_placement(True)

classes = ["ramen", "japanese_food", "international_cuisine", "cafe", "other"]
num_classes = len(classes)
image_size = 224


def main():
    X_train = np.load("./x_train_224.npy", allow_pickle=True)
    X_test = np.load("./x_test_224.npy", allow_pickle=True)
    y_train = np.load("./y_train_224.npy", allow_pickle=True)
    y_test = np.load("./y_test_224.npy", allow_pickle=True)

    X_train = X_train.astype("float") / 255.0
    X_test = X_test.astype("float") / 255.0
    y_train = to_categorical(y_train, num_classes)
    y_test = to_categorical(y_test, num_classes)

    model = model_train(X_train, y_train, X_test, y_test)
    model_eval(model, X_test, y_test)


classes = ["ramen", "japanese_food", "international_cuisine", "cafe", "other"]
num_classes = len(classes)
image_size = 224

# TensorFlowのメモリの成長を許可する
physical_devices = tf.config.experimental.list_physical_devices("GPU")
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)


def main():
    X_train = np.load("./x_train_224.npy", allow_pickle=True)
    X_test = np.load("./x_test_224.npy", allow_pickle=True)
    y_train = np.load("./y_train_224.npy", allow_pickle=True)
    y_test = np.load("./y_test_224.npy", allow_pickle=True)

    X_train = X_train.astype("float") / 255.0
    X_test = X_test.astype("float") / 255.0
    y_train = to_categorical(y_train, num_classes)
    y_test = to_categorical(y_test, num_classes)

    model = model_train(X_train, y_train, X_test, y_test)
    model_eval(model, X_test, y_test)

    del X_train, X_test, y_train, y_test  # クリーンアップ
    gc.collect()


def model_train(X, y, X_val, y_val):
    model = VGG16(
        weights="imagenet", include_top=False, input_shape=(image_size, image_size, 3)
    )
    top_model = Sequential()
    top_model.add(Flatten(input_shape=model.output_shape[1:]))
    top_model.add(Dense(256, activation="relu"))
    top_model.add(Dropout(0.5))
    top_model.add(Dense(num_classes, activation="softmax"))

    model = Model(inputs=model.input, outputs=top_model(model.output))

    for layer in model.layers[:15]:
        layer.trainable = False

    opt = Adam(learning_rate=0.0001)
    model.compile(loss="categorical_crossentropy", optimizer=opt, metrics=["accuracy"])
    early_stopping = EarlyStopping(monitor="val_loss", patience=10)
    checkpoint = ModelCheckpoint(
        "./gourmet_cnn_vgg_v2.h5",
        monitor="val_accuracy",
        verbose=1,
        save_best_only=True,
    )

    # バッチサイズを減らす
    model.fit(
        X,
        y,
        batch_size=8,
        epochs=100,
        validation_data=(X_val, y_val),
        callbacks=[early_stopping, checkpoint],
    )
    model.save("./gourmet_cnn_vgg.h5")

    return model


def model_eval(model, x, y):
    scores = model.evaluate(x, y, verbose=1)
    print("Test Loss:", scores[0])
    print("Test Accuracy:", scores[1])


if __name__ == "__main__":
    main()
