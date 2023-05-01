from plc import PLC
import yaml
import os
csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd+"/config.yaml"))
plc_ip = config['plc']['ip']
def run_plc(ip):
    my_plc = PLC(ip)
    my_plc.start()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run_plc(plc_ip)
