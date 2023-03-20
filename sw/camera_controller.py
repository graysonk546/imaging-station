
from time import sleep
import serial
import json
import os

import cv2
from vimba import *
import time
from datetime import datetime

FOLDER_NAME = "imaging_test_{date}"
FILE_NAME =   "/pic_{n}.tiff"

def setup_camera(self, cam: Camera):
    with cam:
        # set the camera exposure
        try:
            cam.ExposureTime.set(8999999)
        except (AttributeError, VimbaFeatureError):
            pass
        # set the camera white balance
        try:
            cam.BalanceWhiteAuto.set('Continuous')
        except (AttributeError, VimbaFeatureError):
            pass
        # only for GigE cams, try removing this
        try:
            cam.GVSPAdjustPacketSize.run()
            while not cam.GVSPAdjustPacketSize.is_done():
                pass
        except (AttributeError, VimbaFeatureError):
            pass

        # Query available, open_cv compatible pixel formats
        # prefer color formats over monochrome formats
        cv_fmts = intersect_pixel_formats(cam.get_pixel_formats(), \
                                          OPENCV_PIXEL_FORMATS)
        color_fmts = intersect_pixel_formats(cv_fmts, COLOR_PIXEL_FORMATS)

        if color_fmts:
            cam.set_pixel_format(color_fmts[0])
        else:
            mono_fmts = intersect_pixel_formats(cv_fmts, MONO_PIXEL_FORMATS)
            if mono_fmts:
                cam.set_pixel_format(mono_fmts[0])
            else:
                abort('Camera does not support a OpenCV compatible format')

if __name__== "__main__":
    # establish serial communication with Bluepill
    s = serial.Serial("/dev/ttyUSB0", 115200)
    
    # commence the imaging session with the "start" command
    sleep(1)
    print(s.write(b"start\n"))
    s.flush()

    # make a directory to temporarily store the images
    date = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    f = FOLDER_NAME.format(date=date)
    os.mkdir(f)
    n = 0

    while True:
        # wait on serial communication
        if s.in_waiting > 0:
            # sleep(1)
            message = s.readline().decode("ascii")
            if message == "picture\r\n":
                # requirement that Vimba instance is opened using "with"
                with Vimba.get_instance () as vimba:
                    cams = vimba.get_all_cameras ()
                    with cams [0] as cam:
                        # set frame capture timeout at max exposure time
                        frame = cam.get_frame(timeout_ms=1000000)
                        print("Got a frame")
                        # time.sleep(1)
                        print("Frame saved to mem")
                        frame.convert_pixel_format(PixelFormat.Mono8)
                        cv2.imwrite(f+FILE_NAME.format(n=n), \
                                    frame.as_opencv_image())
                        n+=1
                        # send a message to indicate a picture was saved
                        s.write(b"finished\n")
                        s.flush()
                        
            elif message == "finished-imaging\r\n":
                # exit the control loop
                break