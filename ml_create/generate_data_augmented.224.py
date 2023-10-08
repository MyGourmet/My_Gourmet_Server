from PIL import Image,ImageOps
import os, glob
import numpy as np
from sklearn import model_selection
import random
import time
import gc

classes = ["ramen", "japanese_food", "international_cuisine", "cafe", "other"]
num_classes = len(classes)
image_size = 224
num_testdata = 100
batch_size = 50  # 例として100枚ごとに処理します

X_train = []
Y_train = []
X_test = []
Y_test = []

base_dir = '/content/drive/MyDrive/Japan'

def resize_with_padding(img, target_size):
    # アスペクト比を維持したままリサイズ
    img = img.resize((target_size[0], int((target_size[0]/img.width)*img.height)))
    if img.height < target_size[1]:
        img = img.resize((int((target_size[1]/img.height)*img.width), target_size[1]))

    # 余白の追加
    delta_w = target_size[0] - img.width
    delta_h = target_size[1] - img.height
    padding = (delta_w//2, delta_h//2, delta_w-(delta_w//2), delta_h-(delta_h//2))
    return ImageOps.expand(img, padding, fill="red")  # fillで指定した背景色で埋める。必要に応じて変更してください。

def process_batch(files, index):
    x_train_batch = []
    y_train_batch = []
    x_test_batch = []
    y_test_batch = []

    test_ratio = 0.2  # テストデータの割合を10%とする
    split_index = int(len(files) * test_ratio)

    for i, file in enumerate(files):
        try:
            image = Image.open(file)
            image = image.convert("RGB")
            image = resize_with_padding(image, (image_size, image_size))
            data = np.asarray(image)

            if i < split_index:
                x_test_batch.append(data)
                y_test_batch.append(index)
            else:
                x_train_batch.append(data)
                y_train_batch.append(index)

                # データ拡張: 回転
                for angle in range(-20, 20, 10):
                    img_r = image.rotate(angle)
                    data = np.asarray(img_r)
                    x_train_batch.append(data)
                    y_train_batch.append(index)

                # データ拡張: フリップ
                img_trans = image.transpose(Image.FLIP_LEFT_RIGHT)
                data = np.asarray(img_trans)
                x_train_batch.append(data)
                y_train_batch.append(index)
        except Exception as e:
            print(f"Error processing file {file}: {e}")

    return x_train_batch, y_train_batch, x_test_batch, y_test_batch

for index, cls in enumerate(classes):
    print(f"classes: {classes}")
    photos_dir = os.path.join(base_dir, cls)
    files = glob.glob(photos_dir + "/*.jpg")
    random.shuffle(files)
    files = files[:1000]

    for i in range(0, len(files), batch_size):
        x_train_b, y_train_b, x_test_b, y_test_b = process_batch(files[i:i+batch_size], index)
        X_train.extend(x_train_b)
        Y_train.extend(y_train_b)
        X_test.extend(x_test_b)
        Y_test.extend(y_test_b)
        del x_train_b, y_train_b, x_test_b, y_test_b
        gc.collect()

X_train = np.array(X_train).astype(np.float32)
X_test = np.array(X_test).astype(np.float32)
Y_train = np.array(Y_train)
Y_test = np.array(Y_test)

np.save("./x_train_224.npy", X_train)
time.sleep(10)  # 10秒待機
np.save("./y_train_224.npy", Y_train)
time.sleep(10)  # 10秒待機
np.save("./x_test_224.npy", X_test)
time.sleep(10)  # 10秒待機
np.save("./y_test_224.npy", Y_test)

print(f"X_train length: {len(X_train)}")
print(f"Y_train length: {len(Y_train)}")
print(f"X_test length: {len(X_test)}")
print(f"Y_test length: {len(Y_test)}")