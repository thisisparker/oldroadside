import csv
import random
import requests
import os
import sys
import yaml

from PIL import Image
from io import BytesIO
from mastodon import Mastodon
from twython import Twython

def get_item_list(itemspath):
    with open(itemspath) as f:
        reader = csv.DictReader(f)
        items = [row for row in reader]
    return items

def get_nogos_list(nogospath):
    with open(nogospath) as f:
        nogos = [int(index) for index in f.readlines()]
    return nogos

def main():
    fullpath = os.path.dirname(os.path.realpath(__file__))

    configpath = os.path.join(fullpath, 'config.yaml')
    orderpath = os.path.join(fullpath, 'order.txt')
    itemspath = os.path.join(fullpath, 'mrg_info.csv')
    nogospath = os.path.join(fullpath, 'nogo.txt')

    items = get_item_list(itemspath)
    nogos = get_nogos_list(nogospath)

    if os.path.exists(orderpath):
        with open(orderpath) as f:
            order = [int(i) for i in f.readlines() if int(i) not in nogos]
    else:
        order = []

    if not order:
        order = [i for i in list(range(len(items))) if i not in nogos]
        random.shuffle(order)

    next_index = order.pop(0)

    with open(orderpath, 'w') as f:
        f.write('\n'.join([str(index) for index in order]))

    row = items[next_index]

    row['image_url'] = row['image_url'].replace('service','master').replace('v.jpg','u.tif')

    status = '{}, {}'.format(row['title'], row['date']).lower()
    res = requests.get(row['image_url'])

    img = Image.open(BytesIO(res.content))
    factor = 2400/max(img.size)

    new_size = (int(img.size[0] * factor), int(img.size[1] * factor))

    img = img.resize(new_size)

    image_io = BytesIO()

    img.save(image_io, format='jpeg')

    if '-d' in sys.argv[1:]:
        print(status, row['image_url'])
        img.save('test.jpg')
        sys.exit()

    with open(configpath) as f:
        config = yaml.safe_load(f)

    appkey = config['app_key']
    appsecret = config['app_secret']
    token = config['oauth_token']
    tokensecret = config['oauth_secret']

    twitter = Twython(appkey, appsecret, token, tokensecret)

    mastodonkey = config['mastodon_key']
    mastodonsecret = config['mastodon_secret']
    mastodontoken = config['mastodon_token']

    mastodon = Mastodon(client_id=mastodonkey, client_secret=mastodonsecret,
                        access_token=mastodontoken, api_base_url='https://botsin.space')

    image_io.seek(0)

    response = twitter.upload_media(media=image_io)
    twitter.update_status(status=status, media_ids = [response['media_id']])

    image_io.seek(0)

    mast_media = mastodon.media_post(image_io, mime_type='image/jpeg')
    mastodon.status_post(status=status, media_ids = [mast_media['id']])

if __name__ == '__main__':
    main()
