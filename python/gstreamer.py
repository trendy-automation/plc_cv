#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from obj import Obj
import cv2
import logging


gst_str = ('v4l2src device=/dev/video{} ! '
    'video/x-raw, width=(int){}, height=(int){} ! '
    'videoconvert ! appsink').format(dev, width, height)
  return cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)