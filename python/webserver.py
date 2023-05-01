import pyshine as ps
import socket
import threading
import yaml
import os

csd = os.path.dirname(os.path.abspath(__file__))
config = yaml.safe_load(open(csd + "/config.yaml"))
resolution_x = config['vision']['pipline']['resolution_x']
resolution_y = config['vision']['pipline']['resolution_y']


class WebServer(threading.Thread):
    def __init__(self,cap_images):
        self.cap_images = cap_images
        self.server = None

    def run(self):
        HTML = f"""
        <html>
        <body>
        <center><img src="stream.mjpg" width='{resolution_x * 2}' height='{resolution_y}' autoplay playsinline></center>
        </body>
        </html>
        """
        stream_props = ps.StreamProps
        stream_props.set_Page(stream_props, HTML)
        address = (socket.gethostbyname(socket.gethostname()), 9001)  # Enter your IP address
        stream_props.set_Mode(stream_props, 'cv2')
        stream_props.set_Capture(stream_props, self.cap_images)
        stream_props.set_Quality(stream_props, 100)
        self.server = ps.Streamer(address, stream_props)
        print('Server started at', 'http://' + address[0] + ':' + str(address[1]))
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
