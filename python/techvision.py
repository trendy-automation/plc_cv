#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
from capture import ImgCapture
from match import MatchCapture
from httpserver import HttpServer
# import rtspserver
# from rtspserver import GObject, Gst, GstServer
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


def subtract_background_old(nest_part, nest):
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
        # self.rtsp_server = None
        self.rtsp_video_writer = None
        self.gst_loop = None
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
        self.capture = ImgCapture(self.pipeline, rs.hole_filling_filter())
        self.is_pipeline_started = False
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

        self.stream_opt = Obj({"rtspport": config['vision']['stream']['rtspport'],
                               "httpport": config['vision']['stream']['httpport'],
                               "quality": config['vision']['stream']['quality'],
                               "local_ip": socket.gethostbyname(socket.gethostname()),
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
            if not self.is_pipeline_started:
                self.pipeline.start(self.rs_config)
                # self.capture.images.set(cv2.CAP_PROP_FRAME_WIDTH, self.stream_opt.image_width)
                # self.capture.images.set(cv2.CAP_PROP_FRAME_HEIGHT, self.stream_opt.image_height)
                # self.capture.images.set(cv2.CAP_PROP_FPS, self.stream_opt.fps)
                self.is_pipeline_started = self.capture.isOpened()
            return self.is_pipeline_started
        except Exception as error:
            self.logger.error(f"Не удалось включить камеру\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")
            return False

    def pipeline_stop(self):
        # playing
        # if rs.playback_status == 1:
        try:
            if self.is_pipeline_started:
                self.is_pipeline_started = False
                self.pipeline.stop()
        except Exception as error:
            self.logger.error(f"Не удалось выключить камеру\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

    def subtract_background(self, nest_part, nest):
        nest_mask = None

        if not (nest_part is None) and not (nest is None):
            grey_nest = cv2.cvtColor(nest, cv2.COLOR_BGR2GRAY)
            grey_nest_part = cv2.cvtColor(nest_part, cv2.COLOR_BGR2GRAY)
            diff = grey_nest_part - grey_nest
            mask = (diff > 239) & (diff < 251)
            nest_diff = np.where(mask, 255, 0).astype(dtype='uint8')
            blur = cv2.GaussianBlur(nest_diff, (3, 3), 0)
            thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            # Filter using contour area and remove small noise
            cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            for c in cnts:
                area = cv2.contourArea(c)
                if area < 5500:
                    cv2.drawContours(thresh, [c], -1, (0, 0, 0), -1)
            # Morph close and invert image
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
            close = 255 - cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            alpha_channel = close
            b_channel, g_channel, r_channel = cv2.split(nest_part)
            b_channel = cv2.bitwise_and(b_channel, b_channel, mask=alpha_channel)
            g_channel = cv2.bitwise_and(g_channel, g_channel, mask=alpha_channel)
            r_channel = cv2.bitwise_and(r_channel, r_channel, mask=alpha_channel)

            nest_mask = cv2.merge((b_channel, g_channel, r_channel, alpha_channel))
        res = not (nest_mask is None)
        return res, nest_mask

    def http_stream_on(self):
        try:
            # print('http_stream_on')
            if self.http_server is None and self.capture is not None:
                # print('HTTP server start begin')
                self.http_server = HttpServer(opt=self.stream_opt, cap=self.capture.images)
                self.http_server.start()
                # print('HTTP server start end')
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
            if self.rtsp_video_writer is None and self.capture is not None:
                # if self.rtsp_server is None and self.capture is not None:
                # RTSP: initializing the threads and running the stream on loop.
                # GObject.threads_init()
                # Gst.init(None)
                # self.rtsp_server = GstServer(opt=self.stream_opt, cap=self.capture.images)
                # self.gst_loop = GObject.MainLoop()
                # self.gst_loop.run()

                # # Define the gstreamer sink
                gst_str_rtp = f"appsrc ! videoconvert ! videoscale ! video/x-raw,format=RGBA,width={self.stream_opt.image_width}," \
                              f"height={self.stream_opt.image_height},framerate={self.stream_opt.fps}/1 ! " \
                              " videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! " \
                              f"rtph264pay ! udpsink host={self.stream_opt.local_ip} port={self.stream_opt.rtspport}"

                # gst_str_rtp = f"appsrc ! videoconvert ! videoscale ! video/x-raw,format=I420,width={self.stream_opt.image_width}," \
                #               f"height={self.stream_opt.image_height},framerate={self.stream_opt.fps}/1 ! " \
                #                " videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! " \
                #               f"rtph264pay ! udpsink host={self.stream_opt.local_ip} port={self.stream_opt.rtspport}"

                # gst_str_rtp = "appsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! " \
                #               f"rtph264pay ! udpsink host={self.stream_opt.local_ip} port={self.stream_opt.rtspport}"
                # #"appsrc ! video/x-raw, format=BGR ! queue ! videoconvert ! video/x-raw, format=BGRx ! nvvidconv ! " \
                # #"omxh264enc ! video/x-h264, stream-format=byte-stream ! h264parse ! rtph264pay pt=96 config-interval=1 ! " \
                # #f"udpsink host={self.stream_opt.local_ip} port={self.stream_opt.rtspport}"
                # # Create videowriter as a SHM sink
                self.rtsp_video_writer = cv2.VideoWriter(gst_str_rtp, cv2.CAP_GSTREAMER, 0, self.stream_opt.fps,
                                                         (self.stream_opt.image_width, self.stream_opt.image_height),
                                                         True)
                print(f'RTSP server start on rtsp://{self.stream_opt.local_ip}:{self.stream_opt.rtspport}')
                return True
        except Exception as error:
            self.logger.error(f"Не удалось включить rtsp стрим сервер\n"
                              f"Ошибка {str(error)} {traceback.format_exc()}")

    def rtsp_stream_off(self):
        try:
            # if self.rtsp_server is not None:
            #     self.rtsp_server = None
            if self.rtsp_video_writer is not None:
                self.rtsp_video_writer = None
                # if self.gst_loop is not None:
                #     self.gst_loop.stop()
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
                # (f"Получено задание {str(camera_db)}")
                try:
                    # Start streaming
                    if self.pipeline_start():
                        # print(f"camera_db {camera_db}")
                        part_type = str(camera_db.outPartTypeExpect[0])
                        part_pos_num = str(camera_db.outPartPosNumExpect[0])
                        # part_template_dir = os.path.join(self.match_opt.template_dir, part_type)
                        if camera_db.inoutRequest[0]:
                            res = False
                            if camera_db.outTrainModeOn[0]:
                                if camera_db.outPartPresentInNest[0]:
                                    if self.capture.isOpened():
                                        if os.path.exists(part_type):
                                            nest = cv2.imread(os.path.join(part_type, "nest_" + part_pos_num + ".png"))
                                            cap_readed, nest_part = self.capture.depth.read()
                                            if cap_readed:
                                                if camera_db.outHistoryOn:
                                                    part_res = cv2.imwrite(
                                                        os.path.join(part_type, "part_" + part_pos_num + ".png"),
                                                        nest_part)
                                                res, nest_mask = self.subtract_background(nest_part, nest)
                                            if res:
                                                res = cv2.imwrite(os.path.join(part_type, part_pos_num + ".png"),
                                                                  nest_mask)
                                                if not camera_db.outHistoryOn:
                                                    os.remove(os.path.join(part_type, "nest_" + part_pos_num + ".png"))
                                            else:
                                                print('Ошибка. Невозможно обучить деталь')
                                else:
                                    if self.capture.isOpened():
                                        cap_readed, part = self.capture.depth.read()
                                        if cap_readed:
                                            if not os.path.exists(part_type):
                                                os.makedirs(part_type)
                                            res = cv2.imwrite(os.path.join(part_type, "nest_" + part_pos_num + ".png"),
                                                              part)
                                    else:
                                        print('Ошибка. Невозможно обучить фон')
                                camera_db.inoutTrainOk[0] = res
                            else:
                                if self.capture.isOpened():
                                    cap_readed, part = self.capture.depth.read()
                                    if cap_readed:
                                        mc = MatchCapture(opt=self.match_opt, cap=part, templates=self.templates)
                                        result, res_list = mc.eval_match()
                                        res = len(res_list) > 0
                                camera_db.inoutPartOk[0] = res
                            camera_db.inoutResultNok[0] = not res
                        if camera_db.outStreamOn[0]:
                            res1 = self.http_stream_on()
                            res2 = self.rtsp_stream_on()
                        else:
                            # Stop streaming
                            res1 = self.http_stream_off()
                            res2 = self.rtsp_stream_off()
                            self.pipeline_stop()
                        if camera_db.outHistoryOn[0]:
                            pass
                        else:
                            pass
                    else:
                        camera_db.outStreamOn[0] = False
                except Exception as error:
                    self.logger.error(f"Не удалось обработать запрос\n"
                                      f"Ошибка {str(error)} {traceback.format_exc()}")
                finally:
                    camera_db.inoutRequest[0] = False
                    if camera_db.inoutPartOk[0] or camera_db.inoutTrainOk[0]:
                        camera_db.inPartTypeDetect[0] = camera_db.outPartTypeExpect[0]
                        camera_db.inPartPosNumDetect[0] = camera_db.outPartPosNumExpect[0]

                    self.vision_status.put(camera_db)
                    self.vision_tasks.get()
            if self.rtsp_video_writer is not None:
                # Check if cap is open
                if self.capture.isOpened():
                    # Get the frame
                    cap_readed, frame = self.capture.images.read()
                    # frame = cv2.imread("2/part4.png")
                    # cap_readed = True
                    # Check
                    if cap_readed:
                        # Flip frame
                        # frame = cv2.flip(frame, 1)
                        # Write to SHM
                        self.rtsp_video_writer.write(frame)
                    else:
                        print("Camera error.")
