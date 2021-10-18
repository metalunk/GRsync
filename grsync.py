import json
import argparse
import socket
import re
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, Request
from argparse import RawTextHelpFormatter

from exceptions import GrUrlError, GrResponseError


class Importer:
    GR_HOST = "http://192.168.0.1/"
    PHOTO_LIST_URI = "v1/photos"
    SHUTDOWN_URI = 'v1/device/finish'
    GR_PROPS = "v1/props"
    SUPPORT_DEVICE = ['RICOH GR II', 'RICOH GR III', 'GR II']
    BATTERY_LOWER_BOUND = 15

    def __init__(self, destination_dir: Path):
        self.device = ''
        self.destination_dir = destination_dir

    def run(self, download_all: bool, start_dir: str = None, start_file: str = None):
        device = self.get_device_name()
        if device not in self.SUPPORT_DEVICE:
            print("Your source device '%s' is unknown or not supported." % device)
            return
        else:
            self.device = device

        if self.get_battery_level() < self.BATTERY_LOWER_BOUND:
            print("Your battery level is less than 15%, please charge it before sync operation.")
            return

        print(f'Downloading photos from {device} to {self.destination_dir}')

        self.download_photos(download_all, start_dir, start_file)

    def get_device_name(self):
        data = self._download_json(self.GR_HOST + self.GR_PROPS)
        return data['model']

    def get_battery_level(self):
        data = self._download_json(self.GR_HOST + self.GR_PROPS)
        return data['battery']

    def get_photo_list(self):
        data = self._download_json(self.GR_HOST + self.PHOTO_LIST_URI)

        photoList = []
        for dic in data['dirs']:
            # todo: Not to create dirs here
            if not (self.destination_dir / dic['name']).is_dir():
                (self.destination_dir / dic['name']).mkdir()

            for file in dic['files']:
                p = f'{dic["name"]}/{file}'
                if not (self.destination_dir / p).exists():
                    photoList.append(p)
        return photoList

    def fetch_photo(self, photo_uri):
        try:
            if self.device == 'GR2':
                f = urlopen(self.GR_HOST + photo_uri)
            else:
                f = urlopen(self.GR_HOST + self.PHOTO_LIST_URI + '/' + photo_uri)

            with (self.destination_dir / photo_uri).open("wb") as local_f:
                local_f.write(f.read())
            return True
        except URLError:
            return False

    def shutdown_device(self):
        req = Request(self.GR_HOST + self.SHUTDOWN_URI)
        req.add_header('Content-Type', 'application/json')
        urlopen(req, "{}")  # todo: This can be None?

    def download_photos(self, download_all: bool, start_dir: str = None, start_file: str = None):
        print("Fetching photo list from %s" % self.device)
        photo_lists = self.get_photo_list()
        count = 0
        if download_all:
            total_photo = len(photo_lists)
        else:
            start_uri = "%s/%s" % (start_dir, start_file)
            if start_uri not in photo_lists:
                print("Unable to find %s in Ricoh %s" % (start_uri, self.device))
                return
            else:
                while True:
                    if photo_lists[0] != start_uri:
                        photo_lists.pop(0)
                    else:
                        total_photo = len(photo_lists)
                        break

        print("Start to download photos")
        while True:
            if not photo_lists:
                print("\nAll photos are downloaded.")
                self.shutdown_device()
                break
            else:
                photo_uri = photo_lists.pop(0)
                count += 1

                print("(%d/%d) Downloading %s now ... " % (count, total_photo, photo_uri), end=' ')
                # todo: MultiThread?
                if self.fetch_photo(photo_uri):
                    print("done!!")
                else:
                    print("*** FAILED ***")

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
    # setting up argument parser
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description='''
GRsync is a handy Python script, which allows you to sync photos from Ricoh GR
II or III via Wifi. It has been tested on Mac OS X and Ubuntu. It should be able to
run on any platform that has a Python environment.

It automatically checks if photos already exists in your local drive. Duplicated
photos will be skipped and only sync needed photos for you.

Simple usage - Download ALL photos from Ricoh GR II or III:

    ./GRsync -a

Advanced usage - Download photos after specific directory and file:

    ./GRsync -d 100RICOH -f R0000005.JPG
    
    All photos after 100RICOH/R0000005.JPG will be downloaded, including all
    following directories (eg. 101RICOH, 102RICOH)

''')
    parser.add_argument("-a", "--all", action="store_true", help="Download all photos")
    parser.add_argument("-d", "--dir", help="Assign directory (eg. -d 100RICOH). MUST use with -f")
    parser.add_argument("-f", "--file",
                        help="Start to download photos from specific file \n(eg. -f R0000005.JPG). MUST use with -d")
    options = parser.parse_args()

    destination_dir = os.environ.get('DESTINATION_DIR')
    if destination_dir is None:
        destination_dir = Path('.')
    else:
        destination_dir = Path(destination_dir)

    download_all = False
    start_dir = None
    start_file = None

    if options.all is True and options.dir is None and options.file is None:
        download_all = True
    elif not (options.dir is None) and (options.file is not None) and options.all is False:
        match = re.match(r"^[1-9]\d\dRICOH$", options.dir)
        if match:
            start_dir = options.dir
        else:
            print("Incorrect directory name. It should be something like 100RICOH")
            return
        match = re.match(r"^R0\d{6}\.JPG$", options.file)
        if match:
            start_file = options.file
        else:
            print("Incorrect file name. It should be something like R0999999.JPG. (all in CAPITAL)")
            return
    else:
        parser.print_help()
        return

    importer = Importer(destination_dir)
    importer.run(download_all, start_dir, start_file)


if __name__ == "__main__":
    # set connection timeout to 2 seconds
    socket.setdefaulttimeout(2)

    main()
