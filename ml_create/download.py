from flickrapi import FlickrAPI
from urllib.request import urlretrieve
from pprint import pprint
import os, time, sys
from PIL import Image

# APIキーの情報
key = "db4f7f9fa073dacdf28bb32714d39603"
secret = "1aedb7b28b2b1d72"
wait_time = 1

# 保存フォルダの指定
animalname = sys.argv[1]
savedir = "./" + animalname
if not os.path.exists(savedir):
    os.makedirs(savedir)

def resize_and_pad(img, size, pad_color=255):
    # アスペクト比を保持したまま画像をリサイズ
    img.thumbnail((size, size), Image.BICUBIC)
    
    # 新しい画像のキャンバスを生成
    new_img = Image.new("RGB", (size, size), pad_color)
    
    # キャンバス上に元の画像を中央に配置
    new_img.paste(img, ((size - img.size[0]) // 2, (size - img.size[1]) // 2))
    
    return new_img

flickr = FlickrAPI(key, secret, format="parsed-json")
result = flickr.photos.search(
    text=animalname,
    per_page=400,
    media="photos",
    sort="relevance",
    safe_search=1,
    extras="url_c,license",
)

photos = result["photos"]
# pprint(photos)

for i, photo in enumerate(photos["photo"]):
    url_c = photo.get("url_c")
    if url_c:
        filepath = savedir + "/" + photo["id"] + ".jpg"
        if os.path.exists(filepath):
            continue
        urlretrieve(url_c, filepath)
        
        # 画像をリサイズ・整形
        img = Image.open(filepath)
        img = resize_and_pad(img, 224)
        img.save(filepath)
        
        time.sleep(wait_time)
