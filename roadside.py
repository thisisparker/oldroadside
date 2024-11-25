import atproto
import csv
import random
import requests
import os
import shlex
import subprocess
import sys
import yaml

from datetime import datetime, timezone
from io import BytesIO
from mastodon import Mastodon

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

    cmd = shlex.split('convert -auto-gamma -contrast-stretch 2%x0.5% '
                      '-resize 1500x1500 - jpg:-')
    print('running', cmd)
    proc = subprocess.run(cmd, input=res.content, capture_output=True)
    print(proc.stderr)

    if '-d' in sys.argv[1:]:
        print(status, row['image_url'])
        with open('test.jpg', 'wb') as f:
            f.write(proc.stdout)
        sys.exit()

    image_io = BytesIO(proc.stdout)

    with open(configpath) as f:
        config = yaml.safe_load(f)

    try:
        image_io.seek(0)

        mastodonkey = config['mastodon_key']
        mastodonsecret = config['mastodon_secret']
        mastodontoken = config['mastodon_token']
        mastodonurl = config['mastodon_url']

        mastodon = Mastodon(client_id=mastodonkey, client_secret=mastodonsecret,
                            access_token=mastodontoken, api_base_url=mastodonurl)

        mast_media = mastodon.media_post(image_io, mime_type='image/jpeg')
        mastodon.status_post(status=status, media_ids = [mast_media['id']])

    except:
        print('Mastodon upload failed')

    try:
        image_io.seek(0)

        bsky_client = atproto.Client()
        bsky_client.login(config['bluesky_username'], config['bluesky_password'])

        bsky_client.send_image(text=status, image=image_io, image_alt=status)

    except:
        print('Bluesky upload failed')

if __name__ == '__main__':
    main()
