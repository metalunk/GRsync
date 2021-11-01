import json
import logging
import socket
import os
from http.client import RemoteDisconnected
from multiprocessing import Pool
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request

from tqdm import tqdm

from exceptions import GrUrlError, GrResponseError


class Importer:
    GR_HOST = "http://192.168.0.1/"
    PHOTO_LIST_URI = "v1/photos"
    SHUTDOWN_URI = 'v1/device/finish'
    GR_PROPS = "v1/props"
    SUPPORT_DEVICE = ['RICOH GR II', 'RICOH GR III', 'GR II']
    BATTERY_LOWER_BOUND = 15
    N_POOL = 4

    def __init__(self, destination_dir: Path):
        self._device = ''
        self._destination_dir = destination_dir
        self._logger = logging.getLogger()

    def run(self):
        self._device = self._get_device_name()
        if self._device not in self.SUPPORT_DEVICE:
            print(f"Your source device '{self._device}' is unknown or not supported.")
            return

        if self._get_battery_level() < self.BATTERY_LOWER_BOUND:
            print("Your battery level is less than 15%, please charge it before sync operation.")
            return

        print(f'Downloading photos from \'{self._device}\' to \'{self._destination_dir}\'')
        self._download_photos()

    def shutdown_device(self):
        req = Request(self.GR_HOST + self.SHUTDOWN_URI)
        req.add_header('Content-Type', 'application/json')
        try:
            urlopen(req, b'{}')
        except RemoteDisconnected:
            return

    def _get_device_name(self):
        data = self._download_json(self.GR_HOST + self.GR_PROPS)
        return data['model']

    def _get_battery_level(self):
        data = self._download_json(self.GR_HOST + self.GR_PROPS)
        return data['battery']

    def _get_photo_list(self):
        data = self._download_json(self.GR_HOST + self.PHOTO_LIST_URI)

        photoList = []
        for dic in data['dirs']:
            for file in dic['files']:
                p = f'{dic["name"]}/{file}'
                if not (self._destination_dir / p).exists():
                    photoList.append(p)
        return photoList

    def _fetch_photo(self, photo_uri: str):
        if self._device == 'GR2':
            url = f'{self.GR_HOST}{photo_uri}'
        else:
            url = f'{self.GR_HOST}{self.PHOTO_LIST_URI}/{photo_uri}'

        try:
            f = urlopen(url)
        except URLError:
            self._logger.warning(f'Failed to get data from \'{url}\'')
            return

        if not (self._destination_dir / photo_uri).parent.exists():
            (self._destination_dir / photo_uri).parent.mkdir(parents=True)

        with (self._destination_dir / photo_uri).open("wb") as local_f:
            local_f.write(f.read())

    def _download_photos(self):
        print("Fetching photo list.")
        photo_lists = self._get_photo_list()

        print("Start to download photos.")
        with Pool(self.N_POOL) as p:
            for _ in tqdm(p.imap_unordered(self._fetch_photo, photo_lists), total=len(photo_lists)):
                pass

        print("All photos are downloaded.")

    @classmethod
    def _download_json(cls, uri):
        req = Request(uri)
        try:
            resp = urlopen(req)
            data = resp.read()
            data = json.loads(data)
            if data['errCode'] != 200:
                raise GrResponseError(data['errCode'], data['errMsg'])
            else:
                return data
        except URLError:
            raise GrUrlError('Failed to connect to a device')


def main():
    destination_dir = os.environ.get('DESTINATION_DIR')
    if destination_dir is None:
        destination_dir = Path('.')
    else:
        destination_dir = Path(destination_dir)

    importer = Importer(destination_dir)
    importer.run()

    print('Shutting down the device.')
    importer.shutdown_device()


if __name__ == "__main__":
    socket.setdefaulttimeout(10)

    main()
