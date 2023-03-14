#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from python_qt_binding import loadUi

import cv2
import sys
import threading

from vimba import *


class My_App(QtWidgets.QMainWindow):

    def __init__(self):
        super(My_App, self).__init__()
        loadUi("./data_collection.ui", self)

        self.enable_camera.clicked.connect(self.SLOT_enable_camera)
        self._is_cam_enabled = False
        self.handler = Handler()

        # Setting up camera
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')
            self.cam = cams[0]
            with self.cam as cam:
                self.setup_camera(cam)
                

    def setup_camera(self, cam: Camera):
        with cam:
            # Enable auto exposure time setting if camera supports it
            try:
                cam.ExposureAuto.set('Continuous')

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

    def SLOT_enable_camera(self):
        if self._is_cam_enabled:
            with Vimba.get_instance() as vimba:
                with self.cam as cam:
                    print("Disabling")
                    cam.stop_streaming()
            self._is_cam_enabled = False
            self.enable_camera.setText("Enable Camera")
        else:
            with Vimba.get_instance() as vimba:
                with self.cam as cam:
                    print("Enabling")
                    cam.start_streaming(handler=self.handler, buffer_count=10)
            self._is_cam_enabled = True
            self.enable_camera.setText("Disable Camera")


class Handler:
    def __init__(self):
        print("Created Handler")
        self.shutdown_event = threading.Event()

    def convert_cv_to_pixmap(self, cv_img):
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cv_img.shape
        bytesPerLine = channel * width
        q_img = QtGui.QImage(cv_img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(q_img)

    def __call__(self, cam: Camera, frame: Frame):
        print("Received frame maybe")
        ENTER_KEY_CODE = 13

        key = cv2.waitKey(1)
        if key == ENTER_KEY_CODE:
            self.shutdown_event.set()
            return

        elif frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

            pixmap = self.convert_cv_to_pixmap(frame.as_open_cv_image())
            self.camera_feed.setPixmap(pixmap)

        cam.queue_frame(frame)



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myApp = My_App()
    myApp.show()
    sys.exit(app.exec_())

