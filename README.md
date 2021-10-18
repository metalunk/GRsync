# GRsync

## Background

This is forked from https://github.com/clyang/GRsync (Thanks clyang for publishing the library!)
I converted the environment from Python2 to Python3, and by using thread pool, made the downloading (network and file IO) faster.

By my rough experiment, it's about 50% faster.
For downloading 10 images (7 L-size JPEGs and 3 raw images), this takes 1m49s while python2 version takes 3m35s.

## What's GRsync

GRsync is a handy Python script, which allows you to sync photos from Ricoh GR II, III or IIIx via WiFi. It should be able to run on any platform that has a Python environment.

It automatically checks if photos already exists in your local device. Duplicated photos will be skipped and only sync needed photos for you.

**NOTE: Ricoh GR II only supports 20MHz 802.11n. The max transfer speed I can get is 65Mbps**

## Installation

```bash
$ git clone git@github.com:metalunk/GRsync.git
$ cd GRsync
$ pip install -r requirements.txt
```

## Usage

1. Connect your computer to Ricoh GR's WiFi network. (SSID: RICOH_XXXXX)
2. Download ALL photos from Ricoh GR via WiFi

```bash
python grsync.py
```

You can change the destination directory by setting an environment variable `DESTINATION_DIR`.
`DESTINATION_DIR=/tmp python grsync.py` creates files like `/tmp/100RICOH/R0000001.JPEG`.