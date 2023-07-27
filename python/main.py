#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from plc import PLC
from techvision import TechVision
import yaml
import os
import logging
from logging import handlers
import sys
import socket


def read_config():
    csd = os.path.dirname(os.path.abspath(__file__))
    config = yaml.safe_load(open(csd + "/config.yaml"))
    plc_ip = config['plc']['ip']
    logger_level = config['logger']['level']
    logger_debug_file = config['logger']['debug_file']
    logger_format = config['logger']['format']
    return plc_ip, logger_level, logger_debug_file, logger_format


def start_logging(logger_level, logger_debug_file, logger_format):
    # logger
    logging.basicConfig(level=logger_level,
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.handlers.RotatingFileHandler(logger_debug_file,
                                                                       maxBytes=(1048576 * 5),
                                                                       backupCount=7)],
                        format=logger_format)


def run_plc(ip):
    print(f"run_plc('{ip}')")
    my_plc = PLC(ip)
    my_techvision = TechVision()
    my_techvision.vision_tasks = my_plc.vision_tasks
    my_plc.vision_status = my_techvision.vision_status
    my_techvision.start()
    my_plc.start()
    return my_plc, my_techvision


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print("запуск main.py")
    plc_ip, logger_level, logger_debug_file, logger_format = read_config()
    start_logging(logger_level, logger_debug_file, logger_format)
    main_plc, main_techvision = run_plc(plc_ip)
    if socket.gethostbyname(socket.gethostname()) != '192.168.1.12':
        #test
        print("test main.py")
        main_plc.do_run = False
        from obj import Obj
        main_plc.vision_tasks.put(

            Obj({
            "inoutRequest": [False, "Bool", 0, 0],
            "inoutPartOk": [False, "Bool", 0, 1],
            "inoutResultNok": [False, "Bool", 0, 2],
            "inoutTrainOk": [False, "Bool", 0, 3],
            "outTrainModeOn": [False, "Bool", 0, 4],
            "outPartPresentInNest": [False, "Bool", 0, 5],
            "outHistoryOn": [False, "Bool", 0, 6],
            "outStreamOn": [True, "Bool", 0, 7],
            "inPartTypeDetect": [0, "USInt", 1, 0],
            "inPartPosNumDetect": [0, "USInt", 2, 0],
            "outPartTypeExpect": [0, "USInt", 3, 0],
            "outPartPosNumExpect": [0, "USInt", 4, 0],
            "inCameraState": [0, "String[25]", 6, 0]
            })
        )
