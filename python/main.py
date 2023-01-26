import plc
import yaml
config = yaml.safe_load(open("config.yml"))

def run_plc(ip):
    my_plc = plc.PLC(ip)
    my_plc.start()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run_plc(config['plc']['ip'])
