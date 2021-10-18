import urllib2
import sys
import json
import argparse
from argparse import RawTextHelpFormatter
import socket
import re
import os


class Importer:
    # remember the ending "/"
    # eg: PHOTO_DEST_DIR = "/home/user/photos/"
    PHOTO_DEST_DIR = ""

    GR_HOST = "http://192.168.0.1/"
    PHOTO_LIST_URI = "v1/photos"
    SHUTDOWN_URI = 'v1/device/finish'
    GR_PROPS = "v1/props"
    SUPPORT_DEVICE = ['RICOH GR II', 'RICOH GR III', 'GR II']
    BATTERY_LOWER_BOUND = 15

    def __init__(self):
        self.device = ''

    def run(self, download_all: bool, start_dir: str = None, start_file: str = None):
        device = self.get_device_name()
        if device not in self.SUPPORT_DEVICE:
            print("Your source device '%s' is unknown or not supported!" % device)
            sys.exit(1)
        else:
            self.device = device

        if self.get_battery_level() < self.BATTERY_LOWER_BOUND:
            print("Your battery level is less than 15%, please charge it before sync operation!")
            sys.exit(1)

        self.download_photos(download_all, start_dir, start_file)

    def get_device_name(self):
        req = urllib2.Request(self.GR_HOST + self.GR_PROPS)
        try:
            resp = urllib2.urlopen(req)
            data = resp.read()
            props = json.loads(data)
            if props['errCode'] != 200:
                print("Error code: %d, Error message: %s" % (props['errCode'], props['errMsg']))
                sys.exit(1)
            else:
                return props['model']
        except urllib2.URLError as e:
            print("Unable to fetch device props from device")
            sys.exit(1)

    def get_battery_level(self):
        req = urllib2.Request(self.GR_HOST + self.GR_PROPS)
        try:
            resp = urllib2.urlopen(req)
            data = resp.read()
            props = json.loads(data)
            if props['errCode'] != 200:
                print("Error code: %d, Error message: %s" % (props['errCode'], props['errMsg']))
                sys.exit(1)
            else:
                return props['battery']
        except urllib2.URLError as e:
            print("Unable to fetch device props from %s" % self.device)
            sys.exit(1)

    def get_photo_list(self):
        req = urllib2.Request(self.GR_HOST + self.PHOTO_LIST_URI)
        try:
            resp = urllib2.urlopen(req)
            data = resp.read()
            photoDict = json.loads(data)
            if photoDict['errCode'] != 200:
                print("Error code: %d, Error message: %s" % (photoDict['errCode'], photoDict['errMsg']))
                sys.exit(1)
            else:
                photoList = []
                for dic in photoDict['dirs']:
                    # check if this directory already exist in local PHOTO_DEST_DIR
                    # if not, create one
                    if not os.path.isdir(self.PHOTO_DEST_DIR + dic['name']):
                        os.makedirs(self.PHOTO_DEST_DIR + dic['name'])

                    # generate the full photo list
                    for file in dic['files']:
                        photoList.append("%s/%s" % (dic['name'], file))
                return photoList
        except urllib2.URLError as e:
            print("Unable to fetch photo list from %s" % self.device)
            sys.exit(1)

    def get_local_files(self):
        fileList = []
        for (dir, _, files) in os.walk(self.PHOTO_DEST_DIR):
            for f in files:
                fileList.append(os.path.join(dir, f).replace(self.PHOTO_DEST_DIR, ""))

        return fileList

    def fetch_photo(self, photouri):
        try:
            # todo: Why only GR2?
            if self.device is 'GR2':
                f = urllib2.urlopen(self.GR_HOST + photouri)
            else:
                f = urllib2.urlopen(self.GR_HOST + self.PHOTO_LIST_URI + '/' + photouri)
            with open(self.PHOTO_DEST_DIR + photouri, "wb") as localfile:
                localfile.write(f.read())
            return True
        except urllib2.URLError:
            return False

    def shutdown_device(self):
        req = urllib2.Request(self.GR_HOST + self.SHUTDOWN_URI)
        req.add_header('Content-Type', 'application/json')
        urllib2.urlopen(req, "{}")

    def download_photos(self, download_all: bool, start_dir: str = None, start_file: str = None):
        print("Fetching photo list from %s ..." % self.device)
        photoLists = self.get_photo_list()
        localFiles = self.get_local_files()
        count = 0
        if download_all:
            totalPhoto = len(photoLists)
        else:
            start_uri = "%s/%s" % (start_dir, start_file)
            if start_uri not in photoLists:
                print("Unable to find %s in Ricoh %s" % (start_uri, self.device))
                sys.exit(1)
            else:
                while True:
                    if photoLists[0] != start_uri:
                        photoLists.pop(0)
                    else:
                        totalPhoto = len(photoLists)
                        break

        print("Start to download photos ...")
        while True:
            if not photoLists:
                print("\nAll photos are downloaded.")
                self.shutdown_device()
                break
            else:
                photouri = photoLists.pop(0)
                count += 1
                if photouri in localFiles:
                    print("(%d/%d) Skip %s, already have it on local drive!!" % (count, totalPhoto, photouri))
                else:
                    print("(%d/%d) Downloading %s now ... " % (count, totalPhoto, photouri), end=' ')
                    if self.fetch_photo(photouri):
                        print("done!!")
                    else:
                        print("*** FAILED ***")


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

    download_all = True
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
            sys.exit(1)
        match = re.match(r"^R0\d{6}\.JPG$", options.file)
        if match:
            start_file = options.file
        else:
            print("Incorrect file name. It should be something like R0999999.JPG. (all in CAPITAL)")
            sys.exit(1)
        download_all = False
    else:
        parser.print_help()

    importer = Importer()
    importer.run(download_all, start_dir, start_file)


if __name__ == "__main__":
    # set connection timeout to 2 seconds
    socket.setdefaulttimeout(2)

    main()
