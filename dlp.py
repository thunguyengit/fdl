#
# Created on Thu Apr 21 2022
#
# 2022 (c) levandat
#
# dlp.py <File URL> [File Password]

import requests, configparser, json, sys, urllib, os
from function import *
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor
import os


def bytes_to_gb(bytes):
    return bytes / (1024 ** 3)

def getlink(link, password):

    ps = myParser()
    cf = toDict(ps)

    # get data from config
    FILE_DL_API_URL = cf['API']['file_dl_api_url']
    USER_AGENT = cf['Auth']['user_agent']
    APP_KEY = cf['Auth']['app_key']
    SESSION_ID = cf['Login']['session_id']
    TOKEN = cf['Login']['token']

    if(SESSION_ID == '' or TOKEN == ''):
        exit("-> Please login first!")

    header = {"Content-Type": "application/json", "accept": "application/json", "User-Agent": USER_AGENT, "Cookie": "session_id=" + SESSION_ID}
    Data = {
      "url": link,
      "password": password,
      "token": TOKEN,
      "zipflag": 0
    }

    r = rq_fshare(URL = FILE_DL_API_URL, header = header, Data = Data)

    if r.status_code != 200:
        exit(errorInfo(r.status_code))

    j = requestToJson(r)

    return j['location']


def getcode(link):
    y = link.split('?token')[0].split('/')
    if y[-1] == '':
      code = y[len(y)-2]
    else:
      code = y[-1]
    return code


def getfolder(code, page):
    url = "https://www.fshare.vn/api/v3/files/folder?linkcode=" + code + "&sort=type,name&page=" + str(page)
    headers = {
      "accept": "application/json, text/plain, */*",
      "accept-language": "vi-VN,vi",
      "priority": "u=1, i",
      "sec-ch-ua": "\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": "\"macOS\"",
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "cors",
      "sec-fetch-site": "same-origin"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:

        data = response.json()

        last = int(data['_links']['last'].split('page=')[1].split('&')[0])

        for item in data['items']:
            size = bytes_to_gb(int(item['size']))
            if item['type'] == 0:
                getfolder(item['linkcode'], 1)
            else:

                linkcode = item['linkcode']
                url = "https://www.fshare.vn/file/" + linkcode
                name = item['name']
                size = bytes_to_gb(int(item['size']))
                print(f"{url} : {name} ({size:.1f}GB)")
                log = f'Log {code}.txt'
                with open(log, 'a') as f:
                    f.write(url + '\n')

            if page < last:
                page = page + 1
                getfolder(code, page)

    else:
        print("Request failed with status code:", response.status_code)

def multi_download(urls):
  with ThreadPoolExecutor(max_workers=4) as executor:

    futures = []
    for url in urls:

      future = executor.submit(rclone_upload, url, '')
      futures.append(future)

      try:
        while len(futures) >= 4:
          completed = [f for f in futures if f.done()]
          for f in completed:
              f.result()
              futures.remove(f)

      except KeyboardInterrupt:
        print("\n> Bạn vừa Ctrl+C, quá trình bị hủy...")
        exiting_event.set()
        break


def rclone_upload(url, password):

    DL_URL = getlink(url.strip(), password)
    rclone = f'rclone copyurl "{DL_URL}" drive:Downloads -a'
    print(rclone)

    with os.popen(rclone) as f:
        print(f.readlines())



FILE_URL = sys.argv[1]
FILE_PASSWORD = ''

if len(sys.argv) == 1:
    exit("-> Please include file URL")
elif len(sys.argv) == 3:
    FILE_PASSWORD == sys.argv[2]


if 'folder' in FILE_URL:
    code = getcode(FILE_URL)
    log = f'Log {code}.txt'
    getfolder(code, 1)

    with open(log, 'r') as f:
        lines = f.readlines()
    multi_download(lines)
else:
    rclone_upload(FILE_URL, FILE_PASSWORD)
