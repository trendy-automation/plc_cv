"""
# separate file - configurations of parts and settings
tolerance = 0.05


parts = [dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ А', h=212, w=89, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ B', h=208, w=87, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ C', h=208, w=80.6, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ D', h=208, w=80, Zavg=400),
         dict(code='8АТ-1250-11', part_name='Корпус маятника', step_name='Установ E', h=528, w=268, Zavg=400),
         dict(code='17115.2900.77', part_name='Переходник', step_name='Установ А', h=273, w=206, Zavg=400),
         dict(code='17115.2900.77', part_name='Переходник', step_name='Установ B', h=209.03, w=206, Zavg=400)]
"""
import pyrealsense2 as rs
import numpy as np
import pyshine as ps
import socket
import cv2
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))

scaleAbs_alpha = config['vision']['scaleAbs_alpha']
templateThreshold = config['vision']['templateThreshold']
maxShiftPix = config['vision']['maxShiftPix']
templateDir = config['vision']['templateDir']
resolution_x = config['vision']['configStream']['resolution_x']
resolution_y = config['vision']['configStream']['resolution_y']
fps = config['vision']['configStream']['fps']


class ImgCapture:
    def __init__(self, pipeline, templates):
        self.frames = None
        self.pipeline = pipeline
        self.templates = templates

    def read(self):

        # Wait for a coherent pair of frames: depth and color
        self.frames = self.pipeline.wait_for_frames()
        depth_frame = self.frames.get_depth_frame()
        color_frame = self.frames.get_color_frame()
        """
        # Convert images to numpy arrays
        #depth_image = np.asanyarray(depth_frame.get_data())
        frames = []
        for x in range(15):
            frameset = pipeline.wait_for_frames()
            frames.append(frameset.get_depth_frame())

        hole_filling = rs.hole_filling_filter()
        for x in range(15):
            frame = hole_filling.process(frames[x])
            frames[x] = np.asanyarray(frame.get_data())
        depth_image = np.min(frames, axis=0)        
        """
        hole_filling = rs.hole_filling_filter()
        depth_frame = hole_filling.process(depth_frame)
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=scaleAbs_alpha), cv2.COLORMAP_JET)
        depth_colormap_dim = depth_colormap.shape
        color_colormap_dim = color_image.shape

        # print (f"templates loop for {templates}")
        for part, pics in self.templates.items():
            # print (f"look for part {part}")
            for file in pics:
                # print (f"look for template {template}")
                template = cv2.imread(f"{templateDir}/{part}/{file}")
                h, w = template.shape[:2]
                if h == resolution_x and w == resolution_y:
                    methods = [cv2.TM_SQDIFF_NORMED, cv2.TM_CCORR_NORMED, cv2.TM_CCOEFF_NORMED]
                    res = cv2.matchTemplate(depth_colormap, template, methods[1])
                    loc = np.where(
                        res >= templateThreshold)  # Coordinates y, x where the matching degree is greater than threshold
                    # print("loc", loc)
                    # for pt in zip(*loc[::-1]):  # * Indicates optional parameters
                    if len(loc[0]) > 0:
                        print(f"Part {part} found")
                        pt = list(zip(*loc[::-1]))[0]
                        right_bottom = (pt[0] + w, pt[1] + h)
                        cv2.rectangle(depth_colormap, pt, right_bottom, (0, 0, 255), 1)
                        continue

        # If depth and color resolutions are different, resize color image to match depth image for display
        if depth_colormap_dim != color_colormap_dim:
            color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]),
                                     interpolation=cv2.INTER_AREA)
        images = np.hstack((depth_colormap, color_image))

        if images is not None:
            ret = True
        return (ret, images)

    def isOpened(self):
        ret, _, _ = self.rs.get_frame_stream()
        return (ret)


def vision_start():
    # resolution_x, resolution_y = 640, 480
    # resolution_x, resolution_y = 848, 480
    # resolution_x,
    # resolution_y = 1280,720
    # fps = 5

    # Папка для образцов
    # templateDir = 'templates'
    lstdr = os.listdir(templateDir)
    parts = [f for f in lstdr if os.path.isdir(templateDir + '/' + f)]
    templates = {str(p): [f for f in os.listdir(templateDir + '/' + p)
                          if os.path.isfile(templateDir + '/' + p + '/' + f) and f.endswith('.png')]
                 for p in parts}

    HTML = f"""
    <html>
    <body>
    <center><img src="stream.mjpg" width='{resolution_x * 2}' height='{resolution_y}' autoplay playsinline></center>
    </body>
    </html>
    """

    stream_props = ps.StreamProps
    stream_props.set_Page(stream_props, HTML)
    address = (socket.gethostbyname(socket.gethostname()), 9001)  # Enter your IP address

    # Configure depth and color streams
    pipeline = rs.pipeline()
    rs_config = rs.config()

    # Get device product line for setting a supporting resolution
    pipeline_wrapper = rs.pipeline_wrapper(pipeline)
    pipeline_profile = rs_config.resolve(pipeline_wrapper)
    device = pipeline_profile.get_device()
    # depth_sensor = device.first_depth_sensor()
    device_product_line = str(device.get_info(rs.camera_info.product_line))
    print('device_product_line', device_product_line)

    found_rgb = False
    for s in device.sensors:
        if s.get_info(rs.camera_info.name) == 'RGB Camera':
            found_rgb = True
            break
    if not found_rgb:
        print("The demo requires Depth camera with Color sensor")
        exit(0)
    align = rs.align(rs.stream.depth)
    rs_config.enable_stream(rs.stream.depth, resolution_x, resolution_y, rs.format.z16, fps)
    rs_config.enable_stream(rs.stream.color, resolution_x, resolution_y, rs.format.bgr8, fps)

    # Start streaming
    pipeline.start(rs_config)
    try:
        stream_props.set_Mode(stream_props, 'cv2')
        cap_images = ImgCapture(pipeline, templates)
        stream_props.set_Capture(stream_props, cap_images)
        stream_props.set_Quality(stream_props, 90)
        server = ps.Streamer(address, stream_props)
        print('Server started at', 'http://' + address[0] + ':' + str(address[1]))
        server.serve_forever()
        while True:
            cv2.waitKey(1)

    finally:
        # Stop streaming
        pipeline.stop()
