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
import yaml
import os
from capture import ImgCapture
from match import MatchCapture
from webserver import WebServer

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))

resolution_x = config['vision']['pipline']['resolution_x']
resolution_y = config['vision']['pipline']['resolution_y']
fps = config['vision']['pipline']['fps']
# Папка для образцов
templateDir = config['vision']['match_template']['templateDir']
save_history = config['vision']['match_template']['save_history']


def vision_start(mode):
    if mode == 'test':
        pass
    elif mode == 'train_part':
        pass
    elif mode == 'train_nest':
        pass
    elif mode == 'debug':
        pass
    elif mode == 'train':
        pass
    elif mode == 'train':
        pass
    else:
        pass
    list_dir = os.listdir(templateDir)
    parts = [f for f in list_dir if os.path.isdir(templateDir + '/' + f)]
    templates = {str(p): [f for f in os.listdir(templateDir + '/' + p)
                          if os.path.isfile(templateDir + '/' + p + '/' + f) and f.endswith('.png')]
                 for p in parts}


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

    try:
        # Start streaming
        pipeline.start(rs_config)

        cap_images = ImgCapture(pipeline, rs.hole_filling_filter())
        mc = MatchCapture(cap_images['depth'], templates)
        res = mc.eval_match()

        ws = WebServer(cap_images['cap'])
        ws.start()
        print('Server continue')
        ws.shutdown()
        print('Server shutdown')

        #while True:
        #    cv2.waitKey(1)

    finally:
        # Stop streaming
        ws.shutdown()
        pipeline.stop()
