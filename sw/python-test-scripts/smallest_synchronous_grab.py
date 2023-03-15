#!/usr/bin/python3

import cv2
from vimba import *
import time

with Vimba.get_instance () as vimba:
    cams = vimba.get_all_cameras ()
    with cams [0] as cam:
        cam.ExposureTime.set(100)
        cam.ExposureAuto.set('Off')
        while True:
            frame = cam.get_frame()
            print("Got a frame")
            # time.sleep(1)
            # frame.convert_pixel_format(PixelFormat.Mono8)
            # cv2.imwrite('frame.jpg', frame.as_opencv_image ())
