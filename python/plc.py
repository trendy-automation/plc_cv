#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# %%
# import logging
# from logging.handlers import RotatingFileHandler
# import time
# import logging


from queue import Queue
from obj import Obj
# from snap7.util import *
import logging
import time
import numpy as np
import snap7
import traceback
import threading
import yaml
import os


class PLC(threading.Thread):
    def __init__(self, plc_ip):
        print("plc.py")
        # init
        threading.Thread.__init__(self, args=(), name=plc_ip, kwargs=None)

        csd = os.path.dirname(os.path.abspath(__file__))
        config = yaml.safe_load(open(csd + "/config.yaml"))
        self.camera_db_num = config['plc']['camera_db_num']
        self.reconnect_timeout = config['plc']['reconnect_timeout']
        self.camera_db = Obj({
            "inoutRequest": [False, "Bool", 0, 0],
            "inoutPartOk": [False, "Bool", 0, 1],
            "inoutResultNok": [False, "Bool", 0, 2],
            "inoutTrainOk": [False, "Bool", 0, 3],
            "outTrainModeOn": [False, "Bool", 0, 4],
            "outPartPresentInNest": [False, "Bool", 0, 5],
            "outHistoryOn": [False, "Bool", 0, 6],
            "outStreamOn": [False, "Bool", 0, 7],
            "inPartTypeDetect": [0, "USInt", 1, 0],
            "inPartPosNumDetect": [0, "USInt", 2, 0],
            "outPartTypeExpect": [0, "USInt", 3, 0],
            "outPartPosNumExpect": [0, "USInt", 4, 0],
            "inCameraState": [0, "String[25]", 6, 0]
        })
        # camera_db_num = config['plc']['camera_db_num']
        # part_type_byte = config['plc']['part_type_byte']
        # part_posnum_byte = config['plc']['part_posnum_byte']
        # vision_mode_byte = config['plc']['vision_mode_byte']

        self.vision_tasks = Queue()
        # Очередь статуса храниться в модуле техзрения
        self.vision_status = None
        # IP аддрес контроллера
        self.plc_ip = plc_ip
        # объект логинга
        self.logger = logging.getLogger("_plc_.client")
        # logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        # библиотека для связи с PLC
        self.snap7client = snap7.client.Client()
        # статус подключения к контроллеру
        self.connection_ok = False
        # Время, в течении которого контроллер был недоступен
        self.unreachable_time = 0

    def get_bool(self, db_number, offsetbyte, offsetbit):
        tag_data = self.snap7client.db_read(db_number, offsetbyte, 1)
        return snap7.util.get_bool(tag_data, 0, offsetbit)

    def get_usint(self, db_number, offsetbyte):
        byte_array_read = self.snap7client.db_read(db_number, offsetbyte, 1)
        return snap7.util.get_usint(byte_array_read, 0)

    def get_string(self, db_number, offsetbyte, len_arr):
        byte_array_read = self.snap7client.db_read(db_number, offsetbyte, len_arr)
        return snap7.util.get_string(byte_array_read, 0, len_arr)

    # def get_cam_value(self, value_type, offsetbyte, offsetbit=0):
    def get_cam_value(self, tag_list: list) -> list:
        value, value_type, offsetbyte, offsetbit = tag_list
        if value_type == 'Bool':
            # return snap7.util.get_bool(self.snap7client.db_read(self.camera_db_num, offsetbyte, 1), 0, offsetbit)
            return [self.get_bool(self.camera_db_num, offsetbyte, offsetbit), value_type, offsetbyte, offsetbit]
        if value_type == 'USInt':
            # byte_array_read = self.snap7client.db_read(self.camera_db_num, offsetbyte, 1)
            # return snap7.util.get_usint(byte_array_read, 0)
            return [self.get_usint(self.camera_db_num, offsetbyte), value_type, offsetbyte, offsetbit]
        if value_type.startswith('String'):
            #byte_array_read = self.snap7client.db_read(self.camera_db_num, offsetbyte, value_type[7:-1])
            #return snap7.util.get_string(byte_array_read, 0, value_type[7:-1])
            return [self.get_string(self.camera_db_num, offsetbyte, value_type[7:-1]), value_type, offsetbyte, offsetbit]
        return None

    def set_bool(self, db_number, offsetbyte, offsetbit, tag_value):
        tag_data = self.snap7client.db_read(db_number, offsetbyte, 1)
        snap7.util.set_bool(tag_data, 0, offsetbit, bool(tag_value))
        return self.snap7client.db_write(db_number, offsetbyte, tag_data)

    def set_usint(self, db_number, offsetbyte, tag_value):
        tag_data = bytearray(1)
        snap7.util.set_usint(tag_data, 0, tag_value)
        return self.snap7client.db_write(db_number, offsetbyte, tag_data)

    def set_string(self, db_number, offsetbyte, tag_value, value_type):
        len_arr = int(value_type[7:-1])
        tag_value = f"%.{len_arr}s" % tag_value
        tag_data = bytearray(len_arr + 2)
        snap7.util.set_string(tag_data, 0, tag_value, len_arr)
        tag_data[0] = np.uint8(len(tag_data))
        tag_data[1] = np.uint8(len(tag_value))
        return self.snap7client.db_write(db_number, offsetbyte, tag_data)

    def set_cam_value(self, tag_list: list) -> bool:
        tag_value, value_type, offsetbyte, offsetbit = tag_list
        if value_type == 'Bool':
            #tag_data = self.snap7client.db_read(self.camera_db_num, offsetbyte, 1)
            #snap7.util.set_bool(tag_data, 0, offsetbit, bool(tag_value))
            #return self.snap7client.db_write(self.camera_db_num, offsetbyte, tag_data)
            return self.set_bool(self.camera_db_num, offsetbyte, tag_value)
        if value_type == 'USInt':
            #tag_data = bytearray(1)
            #snap7.util.set_usint(tag_data, 0, tag_value)
            #return self.snap7client.db_write(self.camera_db_num, offsetbyte, tag_data)
            return self.set_usint(self.camera_db_num, offsetbyte, tag_value)
        if value_type.startswith('String'):
            return self.set_string(self.camera_db_num, offsetbyte, tag_value, value_type)
        return False

    def run(self):
        self.logger.info(f"Connection with PLC {self.plc_ip} started")
        cur_thread = threading.current_thread()
        # Основной цикл
        while getattr(cur_thread, "do_run", True):
            try:
                time.sleep(0.2)
                if self.unreachable_time == 0 or (time.time() - self.unreachable_time) > self.reconnect_timeout:
                    if not self.snap7client.get_connected():
                        # Подключение к контроллеру ...
                        try:
                            self.connection_ok = False
                            self.logger.info(f"Подключение к контроллеру {self.plc_ip}...")
                            self.snap7client.connect(self.plc_ip, 0, 1)
                        except Exception as error:
                            self.logger.error(f"Не удалось подключиться к контроллеру: {self.plc_ip}\n"
                                              f"Ошибка {str(error)} {traceback.format_exc()}")
                            snap7.client.logger.disabled = True
                            self.unreachable_time = time.time()
                    else:
                        if not self.connection_ok:
                            self.connection_ok = True
                            self.unreachable_time = 0
                            self.logger.info(f"Соединение открыто {self.plc_ip}")
                            snap7.client.logger.disabled = False
                        self.process_io()
            except Exception as error:
                self.logger.error(f"Не удалось обработать цикл класса plc\n"
                                  f"Ошибка {str(error)} {traceback.format_exc()}")

    def process_io(self):
        #self.logger.info(f"process_io() self.vision_tasks.empty()={self.vision_tasks.empty()}")
        if self.vision_status.empty() and self.vision_tasks.empty():
            try:
                stream_current_state = self.camera_db.outStreamOn[0]
                history_current_state = self.camera_db.outHistoryOn[0]
                self.camera_db.inoutRequest = self.get_cam_value(self.camera_db.inoutRequest)
                #self.logger.info(f"self.get_cam_value(self.camera_db.inoutRequest) {self.camera_db.inoutRequest} {self.camera_db.inoutRequest[0]}")
                self.camera_db.outHistoryOn = self.get_cam_value(self.camera_db.outHistoryOn)
                self.camera_db.outStreamOn = self.get_cam_value(self.camera_db.outStreamOn)
            except Exception as error:
                self.logger.error(f"Не удалось считать данные из DB{self.camera_db_num}\n"
                                  f"Ошибка {str(error)} {traceback.format_exc()}")
                self.snap7client.disconnect()
            else:
                if self.camera_db.inoutRequest[0]:
                    self.logger.info(f"Строб съёмки пришёл {self.camera_db.inoutRequest[0]} считываем задание")
                    try:
                        self.camera_db.outTrainModeOn = self.get_cam_value(self.camera_db.outTrainModeOn)
                        self.camera_db.outPartPresentInNest = self.get_cam_value(self.camera_db.outPartPresentInNest)
                        self.camera_db.outPartTypeExpect = self.get_cam_value(self.camera_db.outPartTypeExpect)
                        self.camera_db.outPartPosNumExpect = self.get_cam_value(self.camera_db.outPartPosNumExpect)
                    except Exception as error:
                        self.logger.error(f"Не удалось считать данные из DB{self.camera_db_num}\n"
                                          f"Ошибка {str(error)} {traceback.format_exc()}")
                        self.snap7client.disconnect()
                    # Отправляем задание
                    self.vision_tasks.put(self.camera_db)
                    #self.logger.info(f"Очередь заданий: self.vision_tasks.empty() {self.vision_tasks.empty()}")
                else:
                    if stream_current_state != self.camera_db.outStreamOn[0] or \
                            history_current_state != self.camera_db.outHistoryOn[0]:
                        self.vision_tasks.put(self.camera_db)
        if not self.vision_status.empty():
            camera_db = self.vision_status.queue[0]
            if camera_db.outTrainModeOn[0]:
                self.logger.info(
                    f"Запись результата обучения {'детали' if camera_db.outPartPresentInNest[0] else 'фона'}: "
                    f"{camera_db.inoutTrainOk[0]}. Тип детали: {camera_db.inPartTypeDetect[0]}")
            else:
                self.logger.info(
                    f"Запись результата распознования: {camera_db.inoutPartOk[0]}. "
                    f"Тип детали: {camera_db.inPartTypeDetect[0]}")
            try:
                #save stream off if device not connected
                self.camera_db.outStreamOn[0] = camera_db.outStreamOn[0]
                res = self.set_cam_value(camera_db.inoutPartOk)
                res = self.set_cam_value(camera_db.inoutResultNok)
                res = self.set_cam_value(camera_db.inoutTrainOk)
                res = self.set_cam_value(camera_db.inPartTypeDetect)
                res = self.set_cam_value(camera_db.inPartPosNumDetect)
                res = self.set_cam_value(camera_db.inoutRequest)
                res = self.set_cam_value(camera_db.outStreamOn)

                    # self.set_usint(db_number=camera_db_num, offsetbyte=1, tag_value=part_num)
                    # self.found_part_num = 0
                self.vision_status.get()
            except Exception as error:
                self.logger.error(f"Не удалось записать результат съёмки: в DB{self.camera_db_num}\n"
                                  f"Ошибка {str(error)} {traceback.format_exc()}")
                self.snap7client.disconnect()
