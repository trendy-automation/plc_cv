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
from capture import ImgCapture
from match import MatchCapture
from webserver import WebServer
import logging
import threading
import time
import cv2
import pyrealsense2 as rs
from queue import Queue
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))

resolution_x = config['vision']['pipline']['resolution_x']
resolution_y = config['vision']['pipline']['resolution_y']
fps = config['vision']['pipline']['fps']
# Папка для образцов
templateDir = config['vision']['match_template']['templateDir']
save_history = config['vision']['match_template']['save_history']
# logger
logger_level = config['logger']['level']
logger_debug_file = config['logger']['debug_file']
logger_format = config['logger']['format']


class TechVision(threading.Thread):
    def __init__(self, plc_vision_tasks):
        self.logger = logging.getLogger("vision.main")
        threading.Thread.__init__(self, args=(), name='techvision', kwargs=None)
        self.vision_tasks = None
        self.vision_status = Queue()

    def run(self):
        self.logger.info(f"Techvision started")
        cur_thread = threading.current_thread()
        list_dir = os.listdir(templateDir)
        parts = [f for f in list_dir if os.path.isdir(templateDir + '/' + f)]
        templates = {str(p): [f for f in os.listdir(templateDir + '/' + p)
                              if os.path.isfile(templateDir + '/' + p + '/' + f)
                              and f.endswith('.png')
                              and not f.startswith('nest_')]
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

        align = rs.align(rs.stream.depth)
        rs_config.enable_stream(rs.stream.depth, resolution_x, resolution_y, rs.format.z16, fps)
        rs_config.enable_stream(rs.stream.color, resolution_x, resolution_y, rs.format.bgr8, fps)
        while getattr(cur_thread, "do_run", True):
            time.sleep(0.2)
            if not self.vision_tasks.isEmpty():
                try:
                    # Start streaming
                    pipeline.start(rs_config)
                    # Get capture
                    cap_images = ImgCapture(pipeline, rs.hole_filling_filter())

                    task = self.vision_tasks.queue[0]
                    mode = task['mode']
                    if mode == 'test':
                        mc = MatchCapture(cap_images['depth'], templates)
                        res = mc.eval_match()
                    elif mode == 'to_train_part':
                        nest = cv2.imread(os.path.join(templateDir, task['type'], "nest_" + task['pos_num'] + ".png"))
                        nest_part = cap_images['depth']
                        nest_diff = cv2.compare(nest_part, nest, cv2.CMP_NE)
                        alpha_channel = cv2.cvtColor(nest_diff, cv2.COLOR_BGR2GRAY)
                        b_channel, g_channel, r_channel = cv2.split(nest_part)
                        b_channel = cv2.bitwise_and(b_channel, b_channel, mask=alpha_channel)
                        g_channel = cv2.bitwise_and(g_channel, g_channel, mask=alpha_channel)
                        r_channel = cv2.bitwise_and(r_channel, r_channel, mask=alpha_channel)
                        nest_mask = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
                        cv2.imwrite(os.path.join(templateDir, task['type'],  task['pos_num'] + ".png"), nest_mask)
                        os.remove(os.path.join(templateDir, task['type'], "nest_" + task['pos_num'] + ".png"))
                    elif mode == 'to_train_nest':
                        cv2.imwrite(os.path.join(templateDir, task['type'], "nest_" + task['pos_num'] + ".png"),
                                    cap_images['depth'])
                    elif mode == 'debug':
                        pass
                    elif mode == 'stream':
                        ws = WebServer(cap_images['cap'])
                        ws.start()
                    else:
                        pass
                finally:
                    # Stop streaming?
                    # ws.shutdown()
                    # pipeline.stop()
                    pass
            else:
                if ws:
                    print('Server shutdown')
                    ws.shutdown()
