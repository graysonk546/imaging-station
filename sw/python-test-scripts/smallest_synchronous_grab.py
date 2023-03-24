#!/usr/bin/python3
# Heavily adapted from sw/python-test-scripts/Examples_from_Vimba/synchronous_grab.py
# setup_camera() code taken from asynchronous_grab_opencv.py

import cv2
from vimba import *
import time


def setup_camera(self, cam: Camera):
    with cam:
        # Enable auto exposure time setting if camera supports it
        try:
            cam.ExposureAuto.set('Continuous')

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


if __name__ == "__main__":
    # Have to write this "with" statement before trying to use a vimba command
    with Vimba.get_instance () as vimba:
        cams = vimba.get_all_cameras ()
        # Have to write this "with statement" before trying to use a vimba camera
        with cams [0] as cam:
            while True:
                frame = cam.get_frame()
                print("Got a frame")
                # time.sleep(1)

                # Can use these 2 commands to write the obtained frame to a file
                # frame.convert_pixel_format(PixelFormat.Mono8)
                # cv2.imwrite('frame.jpg', frame.as_opencv_image ())
