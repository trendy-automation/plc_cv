import plc
plc_ip = '192.168.0.10'

def run_plc(ip):
    my_plc = plc.PLC(ip)
    my_plc.start()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run_plc(plc_ip)
