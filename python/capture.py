import cv2
import numpy as np
import logging
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))
scaleAbs_alpha = config['vision']['capture']['scaleAbs_alpha']
#logger
logger_level = config['logger']['level']
logger_debug_file = config['logger']['debug_file']
logger_format = config['logger']['format']


class ImgCapture:
    def __init__(self, pipeline, hole_filling):
        self.logger = logging.getLogger("vision.capture")
        self.frames = None
        self.pipeline = pipeline
        self.hole_filling = hole_filling

    def read(self):

        # Wait for a coherent pair of frames: depth and color
        self.frames = self.pipeline.wait_for_frames()
        depth_frame = self.frames.get_depth_frame()
        color_frame = self.frames.get_color_frame()

        #hole_filling = rs.hole_filling_filter()
        depth_frame = self.hole_filling.process(depth_frame)
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=scaleAbs_alpha), cv2.COLORMAP_JET)
        depth_colormap_dim = depth_colormap.shape
        color_colormap_dim = color_image.shape

        # If depth and color resolutions are different, resize color image to match depth image for display
        if depth_colormap_dim != color_colormap_dim:
            color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                                     interpolation=cv2.INTER_AREA)
        images = np.hstack((depth_colormap, color_image))

        if images is not None:
            ret = True
        return {'cap': (ret, images), 'depth': depth_colormap}

    def isOpened(self):
        ret, _, _ = self.rs.get_frame_stream()
        return (ret)
