from plc import PLC
import yaml
import os
import logging
from logging import handlers
import sys
from techvision import TechVision

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd+"/config.yaml"))
plc_ip = config['plc']['ip']
#logger
logger_level = config['logger']['level']
logger_debug_file = config['logger']['debug_file']
logger_format = config['logger']['format']



def run_plc(ip):
    logging.basicConfig(level=logger_level,
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.handlers.RotatingFileHandler(logger_debug_file,
                                                                       maxBytes=(1048576 * 5),
                                                                       backupCount=7)],
                        format=logger_format)
    my_plc = PLC(ip)
    techvision = TechVision()
    techvision.vision_tasks = my_plc.vision_tasks
    my_plc.vision_status = techvision.vision_status
    my_plc.vision_tasks.put({"mode": "to_train_nest", "type": 1, "pos_num": 1})
    techvision.start()
    my_plc.start()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run_plc(plc_ip)
