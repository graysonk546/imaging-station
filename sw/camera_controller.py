
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
        # Enable auto exposure time setting if camera supports it
        try:
            # cam.ExposureAuto.set('Continuous')
            cam.ExposureTime.set(8999999)

            # Uncomment these commands to set a custom exposure, its range is around 10 to 1e7 us
            # Can run script sw/python-test-scripts/Examples_from_Vimba/list_features.py
            # to see all features on a camera and its values
            # cam.ExposureTime.set(100)
            # cam.ExposureAuto.set('Off')

        except (AttributeError, VimbaFeatureError):
            pass

        # Enable white balancing if camera supports it
        try:
            cam.BalanceWhiteAuto.set('Continuous')

        except (AttributeError, VimbaFeatureError):
            pass

        # Try to adjust GeV packet size. This Feature is only available for GigE - Cameras.
        try:
            cam.GVSPAdjustPacketSize.run()

            while not cam.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VimbaFeatureError):
            pass

        # Query available, open_cv compatible pixel formats
        # prefer color formats over monochrome formats
        cv_fmts = intersect_pixel_formats(cam.get_pixel_formats(), OPENCV_PIXEL_FORMATS)
        color_fmts = intersect_pixel_formats(cv_fmts, COLOR_PIXEL_FORMATS)

        if color_fmts:
            cam.set_pixel_format(color_fmts[0])

        else:
            mono_fmts = intersect_pixel_formats(cv_fmts, MONO_PIXEL_FORMATS)

            if mono_fmts:
                cam.set_pixel_format(mono_fmts[0])

            else:
                abort('Camera does not support a OpenCV compatible format natively. Abort.')



if __name__== "__main__":
    # establish serial communication with Bluepill
    s = serial.Serial("/dev/ttyUSB0", 115200)
    print(s.isOpen())
    sleep(5)
    print(s.write(b"start\n"))
    s.flush()
    # make a directory for the sample images
    date = datetime.now().strftime("%d_%m_%Y|%H_%M_%S")
    f = FOLDER_NAME.format(date=date)
    os.mkdir(f)
    n = 0

    while True:
        # wait on serial communication
        if s.in_waiting > 0:
            sleep(1)
            if s.readline().decode("ascii") == "picture\r\n":
                print("here")
                with Vimba.get_instance () as vimba:
                    cams = vimba.get_all_cameras ()
                    # Have to write this "with statement" before trying to use a vimba camera
                    with cams [0] as cam:
                        frame = cam.get_frame(timeout_ms=1000000)
                        print("Got a frame")
                        time.sleep(1)
                        frame.convert_pixel_format(PixelFormat.Mono8)
                        cv2.imwrite(f+FILE_NAME.format(n=n), frame.as_opencv_image ())
                        n+=1
                        # indicate that a picture was taken
                        print("take picture")
                        # send a response
                        s.write(b"finished\n")
                        s.flush()
