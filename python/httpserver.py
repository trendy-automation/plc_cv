import pyshine as ps
import logging
import threading


class HttpServer(threading.Thread):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger("vision.httpserver")
        threading.Thread.__init__(self, args=(), name='httpserver', kwargs=kwargs)
        self.cap = kwargs['cap']
        self.server = None

    def run(self):
        opt = self._kwargs['opt']
        HTML = f"""
        <html>
        <body>
        <center><img src="stream.mjpg" width='{opt.image_width}' height='{opt.image_height}' autoplay playsinline></center>
        </body>
        </html>
        """
        stream_props = ps.StreamProps
        stream_props.set_Page(stream_props, HTML)
        address = (opt.local_ip, opt.httpport)
        stream_props.set_Mode(stream_props, 'cv2')
        stream_props.set_Capture(stream_props, self.cap)
        stream_props.set_Quality(stream_props, 100)
        self.server = ps.Streamer(address, stream_props)
        print('Server started at', 'http://' + address[0] + ':' + str(address[1]))
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
