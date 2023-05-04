from capture import ImgCapture
from match import MatchCapture
from httpserver import HttpServer
from rtspserver import GObject, Gst, GstServer
from obj import Obj
import logging
import socket
import threading
import time
import cv2
import pyrealsense2 as rs
from queue import Queue
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))

# Папка для образцов
templateDir = config['vision']['match_template']['templateDir']
save_history = config['vision']['match_template']['save_history']

stream_opt = Obj({"rstpport": 8554,
                  "httpport": 9001,
                  "local_ip": socket.gethostbyname(socket.gethostname()),
                  "stream_uri": "",
                  "image_width": 2 * config['vision']['pipline']['resolution_x'],
                  "image_height": config['vision']['pipline']['resolution_y'],
                  "resolution_x": config['vision']['pipline']['resolution_x'],
                  "resolution_y": config['vision']['pipline']['resolution_y'],
                  "fps": config['vision']['pipline']['fps']})

match_opt = Obj({"offset_pix": config['vision']['match_template']['limits']['offset_pix'],
                 "match_threshold": config['vision']['match_template']['limits']['match_threshold'],
                 "delta_angle": config['vision']['match_template']['limits']['delta_angle'],
                 "delta_scale": config['vision']['match_template']['limits']['delta_scale'],
                 "template_dir": config['vision']['match_template']['template_dir']})


class TechVision(threading.Thread):
    def __init__(self, plc_vision_tasks):
        self.logger = logging.getLogger("vision.main")
        threading.Thread.__init__(self, args=(), name='techvision', kwargs=None)
        self.vision_tasks = None
        self.http_server = None
        self.rtsp_server = None
        self.gst_loop = None
        self.cap_images = None
        self.vision_status = Queue()

        os.chdir(match_opt.templateDir + '/')
        list_dir = os.listdir()
        parts = [f for f in list_dir if os.path.isdir(f)]
        self.templates = {str(p): [f for f in os.listdir(p)
                                   if os.path.isfile(os.path.join(p, f))
                                   and f.endswith('.png')
                                   and not f.startswith('nest_')]
                          for p in parts}

        # Configure depth and color streams
        self.pipeline = rs.pipeline()
        self.rs_config = rs.config()

        ## Get device product line for setting a supporting resolution
        # pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        # pipeline_profile = rs_config.resolve(pipeline_wrapper)
        # device = pipeline_profile.get_device()
        ## depth_sensor = device.first_depth_sensor()
        # device_product_line = str(device.get_info(rs.camera_info.product_line))
        # print('device_product_line', device_product_line)

        res = rs.align(rs.stream.depth)
        self.rs_config.enable_stream(rs.stream.depth, stream_opt.resolution_x, stream_opt.resolution_y, rs.format.z16,
                                     stream_opt.fps)
        self.rs_config.enable_stream(rs.stream.color, stream_opt.resolution_x, stream_opt.resolution_y, rs.format.bgr8,
                                     stream_opt.fps)
        self.pipeline_start()
        self.http_stream_on()
        self.rtsp_stream_on()
        #self.pipeline_stop()



    def pipeline_start(self):
        # stopped
        if rs.playback_status == 3:
            # Start streaming
            self.pipeline.start(self.rs_config)
            # Get capture
            self.cap_images = ImgCapture(self.pipeline, rs.hole_filling_filter())

    def pipeline_stop(self):
        # playing
        if rs.playback_status == 1:
            self.pipeline.stop()

    def subtract_background(self, nest_part, nest):
        nest_mask = None
        if not (nest_part is None) and not (nest is None):
            nest_diff = cv2.compare(nest_part, nest, cv2.CMP_NE)
            alpha_channel = cv2.cvtColor(nest_diff, cv2.COLOR_BGR2GRAY)
            b_channel, g_channel, r_channel = cv2.split(nest_part)
            b_channel = cv2.bitwise_and(b_channel, b_channel, mask=alpha_channel)
            g_channel = cv2.bitwise_and(g_channel, g_channel, mask=alpha_channel)
            r_channel = cv2.bitwise_and(r_channel, r_channel, mask=alpha_channel)
            nest_mask = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
        res = not (nest_mask is None)
        return res, nest_mask

    def http_stream_on(self):
        if self.http_server is None and not (self.cap_images is None):
            self.http_server = HttpServer(opt=stream_opt, cap=self.cap_images['cap'])
            self.http_server.start()

    def http_stream_off(self):
        if not self.http_server is None:
            self.http_server.shutdown()
            self.http_server = None
            print('Http server shutdown')

    def rtsp_stream_on(self):
        if self.rtsp_server is None and not (self.cap_images is None):
            # RTSP: initializing the threads and running the stream on loop.
            GObject.threads_init()
            Gst.init(None)
            self.rtsp_server = GstServer(opt=stream_opt, cap=self.cap_images['cap'])
            self.gst_loop = GObject.MainLoop()
            self.gst_loop.run()

    def rtsp_stream_off(self):
        if not (self.http_server is None):
            self.rtsp_server = None
        if not (self.gst_loop is None):
            self.gst_loop.stop()
            print('Rtsp server shutdown')

    def run(self):
        self.logger.info(f"Techvision started")
        cur_thread = threading.current_thread()
        while getattr(cur_thread, "do_run", True):
            time.sleep(0.2)
            if not self.vision_tasks.isEmpty():
                try:
                    # Start streaming
                    self.pipeline_start()
                    task = self.vision_tasks.queue[0]
                    mode = task['mode']
                    match mode:
                        case 'test':
                            mc = MatchCapture(opt=match_opt, cap=self.cap_images['depth'], templates=self.templates)
                            res = mc.eval_match()
                        case 'to_train_part':
                            part_template_dir = os.path.join(part_template_dir)
                            nest = cv2.imread(os.path.join(part_template_dir, "nest_" + task['pos_num'] + ".png"))
                            nest_part = self.cap_images['depth']
                            res, nest_mask = self.subtract_background(nest_part, nest)
                            if res:
                                cv2.imwrite(os.path.join(part_template_dir, task['pos_num'] + ".png"), nest_mask)
                                os.remove(os.path.join(part_template_dir, "nest_" + task['pos_num'] + ".png"))
                            else:
                                print('Ошибка. Невозможно обучить деталь')
                        case 'to_train_nest':
                            cv2.imwrite(os.path.join(part_template_dir, "nest_" + task['pos_num'] + ".png"),
                                        self.cap_images['depth'])
                        case 'debug':
                            pass
                        case 'http_stream_on':
                            self.http_stream_on()
                        case 'http_stream_off':
                            self.http_stream_off()
                        case 'rtsp_stream_on':
                            self.rtsp_stream_on()
                        case 'rtsp_stream_off':
                            self.rtsp_stream_off()
                        case _:
                            pass
                finally:
                    # Stop streaming
                    self.pipeline_stop()
                    pass
            else:
                pass
