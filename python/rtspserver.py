#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# sudo apt-get install libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio
# sudo apt-get install libglib2.0-dev libgstrtspserver-1.0-dev gstreamer1.0-rtsp
# https://github.com/wingtk/gvsbuild

import gi
from gi.repository import Gst, GstRtspServer, GObject
from obj import Obj
# import cv2
import logging
#import socket
#import yaml
#import os

#csd = os.path.dirname(os.path.abspath(__file__))
#config = yaml.safe_load(open(csd + "/config.yaml"))



# import required library like Gstreamer and GstreamerRtspServer
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')


# Sensor Factory class which inherits the GstRtspServer base class and add
# kwargs to it.
class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, **kwargs):
        super(SensorFactory, self).__init__(**kwargs)
        opt = kwargs['opt']
        self.logger = logging.getLogger("vision.webserver")
        # threading.Thread.__init__(self, args=(), name='webserver', kwargs=None)
        self.cap = kwargs['cap']
        # self.cap = cv2.VideoCapture(opt.device_id)
        self.number_frames = 0
        self.fps = opt.fps
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        self.launch_string = f'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME ' \
                             'caps=video/x-raw,format=BGR,width={opt.image_width},height={opt.image_height}, ' \
                             'framerate={self.fps}/1 ' \
                             '! videoconvert ! video/x-raw,format=I420 ' \
                             '! x264enc speed-preset=ultrafast tune=zerolatency ' \
                             '! rtph264pay config-interval=1 name=pay0 pt=96'

    # method to capture the video feed from the camera and push it to the
    # streaming buffer.
    def on_need_data(self, src, length):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                ## It is better to change the resolution of the camera
                ## instead of changing the image shape as it affects the image quality.
                #frame = cv2.resize(frame, (opt.image_width, opt.image_height),
                #                   interpolation=cv2.INTER_LINEAR)
                data = frame.tostring()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)
                buf.duration = self.duration
                timestamp = self.number_frames * self.duration
                buf.pts = buf.dts = int(timestamp)
                buf.offset = timestamp
                self.number_frames += 1
                retval = src.emit('push-buffer', buf)
                print('pushed buffer, frame {}, duration {} ns, durations {} s'.format(self.number_frames,
                                                                                       self.duration,
                                                                                       self.duration / Gst.SECOND))
                if retval != Gst.FlowReturn.OK:
                    print(retval)

    # attach the launch string to the override method
    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)

    # attaching the source element to the rtsp media
    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)


# Rtsp server implementation where we attach the factory sensor with the stream uri
class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, **kwargs):
        super(GstServer, self).__init__(**kwargs)
        opt = kwargs['opt']
        self.logger = logging.getLogger("vision.rstpserver")
        self.factory = SensorFactory(**kwargs)
        self.factory.set_shared(True)
        self.set_service(str(opt.rstpport))
        self.get_mount_points().add_factory(opt.stream_uri, self.factory)
        self.attach(None)
        print('Server started at', 'rtsp://' + opt.local_ip + ':' + str(opt.rstpport))



