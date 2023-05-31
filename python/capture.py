#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import logging
import yaml
import os
import traceback
import time


class ImgCapture:
    def __init__(self, pipeline, hole_filling):
        self.logger = logging.getLogger("vision.capture")
        self.frames = None
        self.pipeline = pipeline
        self.hole_filling = hole_filling
        csd = os.path.dirname(os.path.abspath(__file__))
        config = yaml.safe_load(open(csd + "/config.yaml"))
        self.scaleAbs_alpha = config['vision']['capture']['scaleAbs_alpha']
        self.depth = ImgDepth(self)
        self.color = ImgColor(self)
        self.images = ImgImages(self)

    def read(self):
        try:

            #align_to = rs.stream.depth
            #align = rs.align(align_to)
            #self.frames = self.pipeline.wait_for_frames()
            #aligned_frames = align.process(self.frames)
            #aligned_depth_frame = aligned_frames.get_depth_frame()
            #color_frame = aligned_frames.get_color_frame()

            self.frames = self.pipeline.wait_for_frames()
            depth_frame = self.frames.get_depth_frame()
            color_frame = self.frames.get_color_frame()
            if not depth_frame or not color_frame:
                self.logger.error(f"Нет изображения с камеры")
                return False, None, None, None
            # hole_filling = rs.hole_filling_filter()
            depth_frame = self.hole_filling.process(depth_frame)
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=self.scaleAbs_alpha),
                                               cv2.COLORMAP_JET)
            depth_colormap_dim = depth_colormap.shape
            color_colormap_dim = color_image.shape

            # If depth and color resolutions are different, resize color image to match depth image for display
            if depth_colormap_dim != color_colormap_dim:
                color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                                         interpolation=cv2.INTER_AREA)
            images = np.hstack((depth_colormap, color_image))
            ret = images is not None
            return ret, color_image, depth_colormap, images
        except Exception as error:
            self.logger.error(f"Не удалось считать изображение\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")
            return False, None, None, None

    def isOpened(self):
        #cap_readed, _, _, _ = self.read()
        cap_readed = True
        return cap_readed


class ImgImages():
    def __init__(self, cap):
        self.capture = cap
        pass

    def read(self):
        ret, color_frame, depth_colormap, images = self.capture.read()
        return ret, images

    def isOpened(self):
        # ret, color_image, depth_colormap, images = self.capture.read()
        # return ret
        return self.capture.isOpened()


class ImgDepth():
    def __init__(self, cap):
        self.capture = cap
        pass

    def read(self):
        ret, color_frame, depth_colormap, images = self.capture.read()
        return ret, depth_colormap

    def isOpened(self):
        # ret, color_image, depth_colormap, images = self.capture.read()
        # return ret
        return self.capture.isOpened()



class ImgColor():
    def __init__(self, cap):
        self.capture = cap
        pass

    def read(self):
        ret, color_image, depth_colormap, images = self.capture.read()
        return ret, color_image

    def isOpened(self):
        # ret, color_image, depth_colormap, images = self.capture.read()
        # return ret
        return self.capture.isOpened()

