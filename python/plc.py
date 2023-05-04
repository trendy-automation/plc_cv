# %%
# import logging
# from logging.handlers import RotatingFileHandler
# import time
# import logging

import snap7
import traceback
import threading
from queue import Queue
from snap7.util import *
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))

camera_db_num = config['plc']['camera_db_num']
reconnect_timeout = config['plc']['reconnect_timeout']
part_type_byte = config['plc']['part_type_byte']
part_posnum_byte = config['plc']['part_posnum_byte']
vision_mode_byte = config['plc']['vision_mode_byte']


class PLC(threading.Thread):
    def __init__(self, plc_ip):
        print("plc.py")
        # init
        threading.Thread.__init__(self, args=(), name=plc_ip, kwargs=None)
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
        return snap7.util.get_bool(self.db_read(db_number, offsetbyte, 1), 0, offsetbit)

    def get_usint(self, db_number, offsetbyte):
        tag_data = bytearray(1)
        byte_array_read = self.snap7client.db_read(db_number, offsetbyte, tag_data)
        return snap7.util.get_usint(byte_array_read, 0)

    def get_string(self, db_number, offsetbyte, len_arr):
        byte_array_read = self.db_read(db_number, offsetbyte, len_arr)
        return snap7.util.get_string(byte_array_read, 0, len_arr)

    def set_usint(self, db_number, offsetbyte, tag_value):
        tag_data = bytearray(1)
        snap7.util.set_usint(tag_data, 0, tag_value)
        self.snap7client.db_write(db_number, offsetbyte, tag_data)
        return True

    def run(self):
        self.logger.info(f"Connection with PLC {self.plc_ip} started")
        cur_thread = threading.current_thread()
        # Основной цикл
        while getattr(cur_thread, "do_run", True):
            try:
                time.sleep(0.2)
                if self.unreachable_time == 0 or (time.time() - self.unreachable_time) > reconnect_timeout:
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
        # try:
        # except Exception as error:
        #    self.logger.error(f"Не удалось обработать чтение/запись IO plc\n"
        #                          f"Ошибка {str(error)} {traceback.format_exc()}")

        if self.vision_tasks.empty():
            try:
                snapshot_req = self.get_bool(db_number=camera_db_num, offsetbyte=0, offsetbit=0)
            except Exception as error:
                self.logger.error(f"Не удалось считать строб съёмки: DB{camera_db_num}.DBX0.0\n"
                                  f"Ошибка {str(error)} {traceback.format_exc()}")
                self.snap7client.disconnect()
            else:
                if snapshot_req:
                    self.logger.info(f"Строб съёмки пришёл {snapshot_req} считываем задание")
                    part_type = self.get_usint(db_number=camera_db_num, offsetbyte=part_type_byte)
                    part_pos_num = self.get_usint(db_number=camera_db_num, offsetbyte=part_posnum_byte)
                    vision_mode = self.get_string(db_number=camera_db_num, offsetbyte=vision_mode_byte)
                    # Отправляем задание
                    self.vision_tasks.put({"mode": vision_mode, "type": part_type, "pos_num": part_pos_num})

        if not self.vision_status.empty():
            self.vision_tasks.get()
            if self.vision_status.queue[0].part_num > 0:
                self.logger.info(
                    f"Запись результата распознования - номер найденной детали - {self.found_part_num}")
                try:
                    self.set_usint(db_number=camera_db_num, offsetbyte=1, tag_value=self.found_part_num)
                    self.found_part_num = 0
                except Exception as error:
                    self.logger.error(f"Не удалось записать результат съёмки: DB{camera_db_num}.DBB1\n"
                                      f"Ошибка {str(error)} {traceback.format_exc()}")
                    self.snap7client.disconnect()
