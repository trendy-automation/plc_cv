import plc

def run_plc(ip):
    my_plc = plc.PLC(ip)
    my_plc.start()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # common variables
    found_part_num = 0
    run_plc('192.168.1.101')
