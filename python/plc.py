# %%
import snap7
import sys
import logging
from logging import handlers
from logging.handlers import RotatingFileHandler
import traceback
import time
import threading
from snap7.util import *
import yaml
config = yaml.safe_load(open("config.yml"))

# TODO found_part_num
#found_part_num = 0
camera_db_num = 8
reconnect_timeout = 60

class PLC(threading.Thread):
    def __init__(self, plc_ip):
        #init
        threading.Thread.__init__(self, args=(), name=plc_ip, kwargs=None)
        self.plc_ip = plc_ip
        self.found_part_num = 0
        self.snapshotReq = False
        self.plc_ip = plc_ip
        self.logger = logging.getLogger("_plc_.client")
        #logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        logging.basicConfig(level=config['logger']['level'],
                            handlers=config['logger']['handlers'],
                            format=config['logger']['format'])
        self.snap7client = snap7.client.Client()
        self.connection_ok = False
        self.unreachable_time = 0
        self.connect_postpone = False

    def get_bool(self, db_number, offsetbyte, offsetbit):
        return snap7.util.get_bool(self.db_read(db_number, offsetbyte, 1), 0, offsetbit)

    def set_usint(self, db_number, offsetbyte, tag_value):
        tag_data = bytearray(1)
        snap7.util.set_usint(tag_data, 0, tag_value)
        self.snap7client.db_write(db_number, offsetbyte, tag_data)
        return True

    def db_read(self, db_number, offsetbyte, len_arr):
        return self.snap7client.db_read(db_number, offsetbyte, len_arr)

    def db_write(self, db_number, offsetbyte, tag_data):
        return self.snap7client.db_write(db_number, offsetbyte, tag_data)

    def run(self):
        self.logger.info(f"Connection with PLC {self.plc_ip} started")
        cur_thread = threading.current_thread()
        # Основной цикл
        while getattr(cur_thread, "do_run", True):
            try:
                time.sleep(1.2)
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
                        try:
                            if not self.snapshotReq:
                                self.snapshotReq = self.get_bool(db_number=camera_db_num, offsetbyte=0, offsetbit=0)
                                if self.snapshotReq:
                                    self.logger.info(f"Строб съёмки пришёл {self.snapshotReq}")
                        except Exception as error:
                            self.logger.error(f"Не удалось считать строб съёмки: DB{camera_db_num}.DBX0.0\n"
                                              f"Ошибка {str(error)} {traceback.format_exc()}")
                            self.snap7client.disconnect()


                        if self.snapshotReq:
                            if self.found_part_num > 0:
                               self.logger.info(f"Запись результата распознования - номер найденной детали - {self.found_part_num}")
                               try:
                                   self.set_usint(db_number=camera_db_num, offsetbyte=1, tag_value=self.found_part_num)
                                   self.found_part_num = 0
                               except Exception as error:
                                   self.logger.error(f"Не удалось записать результат съёмки: DB{camera_db_num}.DBB1\n"
                                                     f"Ошибка {str(error)} {traceback.format_exc()}")
                                   self.snap7client.disconnect()
            except Exception as error:
                self.logger.error(f"Не удалось обработать цикл класса plc\n"
                                  f"Ошибка {str(error)} {traceback.format_exc()}")
