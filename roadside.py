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
from twython import Twython

BLUESKY_BASE_URL = "https://bsky.social/xrpc"

def get_item_list(itemspath):
    with open(itemspath) as f:
        reader = csv.DictReader(f)
        items = [row for row in reader]
    return items

def get_nogos_list(nogospath):
    with open(nogospath) as f:
        nogos = [int(index) for index in f.readlines()]
    return nogos

def authenticate_bluesky(username, password):
    resp = requests.post(
        BLUESKY_BASE_URL + "/com.atproto.server.createSession",
        json={"identifier": username, "password": password},
    )
    resp_data = resp.json()
    jwt = resp_data["accessJwt"]
    did = resp_data["did"]
    return jwt, did

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
                      '-resize 2000x2000 - jpg:-')
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

    (bsky_jwt, bsky_did) = authenticate_bluesky(config['bluesky_username'],
                                                config['bluesky_password'])

    try:
        image_io.seek(0)

        response = twitter.upload_media(media=image_io)
        twitter.update_status(status=status, media_ids = [response['media_id']])

    except:
        print('Twitter upload failed')

    try:
        image_io.seek(0)

        mast_media = mastodon.media_post(image_io, mime_type='image/jpeg')
        mastodon.status_post(status=status, media_ids = [mast_media['id']])

    except:
        print('Mastodon upload failed')

    image_io.seek(0)

    headers = {"Authorization": "Bearer " + bsky_jwt}

    bsky_media_resp = requests.post(
            BLUESKY_BASE_URL + "/com.atproto.repo.uploadBlob",
            data=image_io,
            headers={**headers, "Content-Type": "image/jpg"})

    img_blob = bsky_media_resp.json().get("blob")

    iso_timestamp = datetime.now(timezone.utc).isoformat()
    iso_timestamp = (
        iso_timestamp[:-6] + 'Z'
    )

    post_data = {
        "repo": bsky_did,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": status,
            "createdAt": iso_timestamp,
            "embed": {"$type": "app.bsky.embed.images", "images":
                [{"image": img_blob,
                  "alt":status}]},
        }
    }

    resp = requests.post(BLUESKY_BASE_URL + "/com.atproto.repo.createRecord",
                            json=post_data,
                            headers=headers)

if __name__ == '__main__':
    main()
