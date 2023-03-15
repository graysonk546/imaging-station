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

        # Setting up camera
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')
            self.cam = cams[0]
            with self.cam as cam:
                self.setup_camera(cam)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.SLOT_query_camera)
        self._timer.setInterval(5) 

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
            self._timer.stop()
            self._is_cam_enabled = False
            self.enable_camera.setText("Enable Camera")
        else:
            self._timer.start()
            self._is_cam_enabled = True
            self.enable_camera.setText("Disable Camera")

    def convert_cv_to_pixmap(self, cv_img):
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cv_img.shape
        bytesPerLine = channel * width
        q_img = QtGui.QImage(cv_img.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(q_img)

    def shrink(self, cv_img):
        width = int(cv_img.shape[1] * 5 / 100)
        height = int(cv_img.shape[0] * 5 / 100)
        
        resized = cv2.resize(cv_img, (width, height), interpolation = cv2.INTER_AREA)
        return resized


    def SLOT_query_camera(self):
        with Vimba.get_instance() as vimba:
            with self.cam as cam:
                try:
                    frame = cam.get_frame(timeout_ms = 10000)
                    print("Frame acquired")
                except VimbaTimeout as e:
                    print("Frame acquisition timed out: " + str(e))
                    return

        print(f"Size of photo is {frame.get_height()} by {frame.get_width()}")
        resized_photo = self.shrink(frame.as_opencv_image())
        print(f"Resized photo dimensions are {resized_photo.shape}")
        pixmap = self.convert_cv_to_pixmap(resized_photo)
        self.camera_feed.setPixmap(pixmap)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myApp = My_App()
    myApp.show()
    sys.exit(app.exec_())

