#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from capture import ImgCapture
from match import MatchCapture
from httpserver import HttpServer
from rtspserver import GObject, Gst, GstServer
from obj import Obj
import logging
import traceback
import socket
import threading
import time
import cv2
import pyrealsense2 as rs
from queue import Queue
import yaml
import os


class TechVision(threading.Thread):
    def __init__(self):
        self.logger = logging.getLogger("vision.main")
        print("techvision.py")
        threading.Thread.__init__(self, args=(), name='techvision', kwargs=None)
        self.stream_opt = None
        self.match_opt = None
        self.read_config()

        self.vision_tasks = None
        self.http_server = None
        self.rtsp_server = None
        self.gst_loop = None
        self.capture = None
        self.vision_status = Queue()

        os.chdir(self.match_opt.template_dir + '/')
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
        self.rs_config.enable_stream(rs.stream.depth, self.stream_opt.resolution_x, self.stream_opt.resolution_y,
                                     rs.format.z16, self.stream_opt.fps)
        self.rs_config.enable_stream(rs.stream.color, self.stream_opt.resolution_x, self.stream_opt.resolution_y,
                                     rs.format.bgr8, self.stream_opt.fps)

    def read_config(self):
        csd = os.path.dirname(os.path.abspath(__file__))
        config = yaml.safe_load(open(csd + "/config.yaml"))

        # Папка для образцов
        # save_history = config['vision']['match_template']['save_history']

        self.stream_opt = Obj({"rstpport": config['vision']['stream']['rstpport'],
                               "httpport": config['vision']['stream']['httpport'],
                               "quality": config['vision']['stream']['quality'],
                               # "local_ip": socket.gethostbyname(socket.gethostname()),
                               "local_ip": "192.168.0.67",
                               "stream_uri": "",
                               "image_width": 2 * config['vision']['pipline']['resolution_x'],
                               "image_height": config['vision']['pipline']['resolution_y'],
                               "resolution_x": config['vision']['pipline']['resolution_x'],
                               "resolution_y": config['vision']['pipline']['resolution_y'],
                               "fps": config['vision']['pipline']['fps']})

        self.match_opt = Obj({"offset_pix": config['vision']['match_template']['limits']['offset_pix'],
                              "match_threshold": config['vision']['match_template']['limits']['match_threshold'],
                              "delta_angle": config['vision']['match_template']['limits']['delta_angle'],
                              "delta_scale": config['vision']['match_template']['limits']['delta_scale'],
                              "template_dir": config['vision']['match_template']['template_dir']})

    def pipeline_start(self):
        # stopped
        # if rs.playback_status == 3:
        # Start streaming
        try:
            #self.pipeline.stop()
            self.pipeline.start(self.rs_config)
            # Get capture
            self.capture = ImgCapture(self.pipeline, rs.hole_filling_filter())
            return self.capture is not None
        except Exception as error:
            self.logger.error(f"Не удалось включить камеру\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")
            return False

    def pipeline_stop(self):
        # playing
        # if rs.playback_status == 1:
        try:
            self.pipeline.stop()
        except Exception as error:
            self.logger.error(f"Не удалось выключить камеру\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

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
        try:
            #print('http_stream_on')
            if self.http_server is None and self.capture is not None:
                #print('HTTP server start begin')
                self.http_server = HttpServer(opt=self.stream_opt, cap=self.capture.images)
                self.http_server.start()
                #print('HTTP server start end')
                return True
        except Exception as error:
            self.logger.error(f"Не удалось включить http стрим сервер\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

    def http_stream_off(self):
        try:
            if not self.http_server is None:
                self.http_server.shutdown()
                self.http_server = None
                print('Http server shutdown')
                return True
        except Exception as error:
            self.logger.error(f"Не удалось выключить http стрим сервер\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

    def rtsp_stream_on(self):
        try:
            if self.rtsp_server is None and self.capture is not None:
                print('RTSP server start')
                # RTSP: initializing the threads and running the stream on loop.
                GObject.threads_init()
                Gst.init(None)
                self.rtsp_server = GstServer(opt=self.stream_opt, cap=self.capture.images)
                self.gst_loop = GObject.MainLoop()
                self.gst_loop.run()
                return True
        except Exception as error:
            self.logger.error(f"Не удалось включить rtsp стрим сервер\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

    def rtsp_stream_off(self):
        try:
            if not (self.http_server is None):
                #pass
                self.rtsp_server = None
            if not (self.gst_loop is None):
                self.gst_loop.stop()
                print('Rtsp server shutdown')
            return True
        except Exception as error:
            self.logger.error(f"Не удалось выключить rtsp стрим сервер\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

    def run(self):
        self.logger.info(f"Techvision started")
        cur_thread = threading.current_thread()
        while getattr(cur_thread, "do_run", True):
            time.sleep(0.2)
            if not self.vision_tasks.empty():
                camera_db = self.vision_tasks.queue[0]
                try:
                    # Start streaming
                    if self.pipeline_start():
                        # print(f"camera_db {camera_db}")
                        part_type = str(camera_db.outPartTypeExpect)
                        part_pos_num = str(camera_db.outPartPosNumExpect)
                        # part_template_dir = os.path.join(self.match_opt.template_dir, part_type)
                        if camera_db.outTrainModeOn:
                            res = False
                            if camera_db.outPartPresentInNest:
                                if self.capture is not None:
                                    nest = cv2.imread(os.path.join(part_type, "nest_" + part_pos_num + ".png"))
                                    nest_part = self.capture.depth.read()
                                    res, nest_mask = self.subtract_background(nest_part, nest)
                                    if res:
                                        res = cv2.imwrite(os.path.join(part_type, part_pos_num + ".png"),
                                                          nest_mask)
                                        os.remove(os.path.join(part_type, "nest_" + part_pos_num + ".png"))
                                    else:
                                        print('Ошибка. Невозможно обучить деталь')
                            else:
                                if self.capture is not None:
                                    res = cv2.imwrite(os.path.join(part_type, "nest_" + part_pos_num + ".png"),
                                                      self.capture.depth.read())
                                else:
                                    print('Ошибка. Невозможно обучить фон')
                            camera_db.inoutTrainOk = res
                            camera_db.inoutResultNok = not res
                        else:
                            if self.capture is not None:
                                mc = MatchCapture(opt=self.match_opt, cap=self.capture.depth.read(),
                                                  templates=self.templates)
                                match_res = mc.eval_match()
                                camera_db.inoutPartOk = len(match_res) > 0
                                camera_db.inoutResultNok = len(match_res) == 0
                        if camera_db.outStreamOn:
                            res1 = self.http_stream_on()
                            res2 = self.rtsp_stream_on()
                        else:
                            res1 = self.http_stream_off()
                            res2 = self.rtsp_stream_off()
                        if camera_db.outHistoryOn:
                            pass
                        else:
                            pass
                finally:
                    # Stop streaming
                    #self.pipeline_stop()
                    camera_db.inPartTypeDetect = camera_db.outPartTypeExpect
                    camera_db.inPartPosNumDetect = camera_db.outPartPosNumExpect
                    self.vision_status.put(camera_db)
                    self.vision_tasks.get()
