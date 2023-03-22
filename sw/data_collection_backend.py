#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from python_qt_binding import loadUi

import cv2
import sys
import threading
import time
import serial

from vimba import *
import os
from datetime import datetime

FOLDER_NAME = "imaging_test_{date}"
FILE_NAME = "/pic_{n}.tiff"
CAMERA = None

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(Frame)

    def run(self):
        # establish serial communication with Bluepill
        s = serial.Serial("/dev/ttyUSB0", 115200)

        # commence the imaging session with the "start" command
        time.sleep(1)
        print(s.write(b"start\n"))
        s.flush()

        # make a directory to temporarily store the images
        date = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        f = FOLDER_NAME.format(date=date)
        os.mkdir(f)
        n = 0
        print("Starting Loop")
        while True:
            # wait on serial communication
            if s.in_waiting > 0 or True:
                time.sleep(1)
                # message = "picture\r\n"
                message = s.readline().decode("ascii")
                if message == "picture\r\n":
                    print("Obtaining Frame")
                    # requirement that Vimba instance is opened using "with"
                    with Vimba.get_instance() as vimba:
                        with CAMERA as cam:
                            # set frame capture timeout at max exposure time
                            try:
                                frame = cam.get_frame(timeout_ms=1000000)
                            except VimbaTimeout as e:
                                print("Frame acquisition timed out: " + str(e))
                                continue
                            print("Got a frame")
                            time.sleep(1)
                            print("Frame saved to mem")
                            
                            # Draw directly
                            print("Drawing")
                            self.progress.emit(frame)
                            print("Done Drawing")
                            frame.convert_pixel_format(PixelFormat.Mono8)
                            cv2.imwrite(f+FILE_NAME.format(n=n),
                                        frame.as_opencv_image())
                            n += 1
                            # send a message to indicate a picture was saved
                            s.write(b"finished\n")
                            s.flush()

                elif message == "finished-imaging\r\n":
                    # exit the control loop
                    break

class My_App(QtWidgets.QMainWindow):

    def __init__(self):
        super(My_App, self).__init__()
        loadUi("./data_collection.ui", self)

        # Obtaining camera and applying default settings
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')
            self.cam = cams[0]
            global CAMERA
            CAMERA = self.cam
            with self.cam as cam:
                self.setup_camera(cam)

        self.start_imaging_button.clicked.connect(
            self.start_imaging_thread)
        
    def start_imaging_thread(self):
        self.camera_thread = QtCore.QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.camera_thread)
        # Connect signals/slots
        self.camera_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.camera_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.camera_thread.finished.connect(self.camera_thread.deleteLater)
        self.worker.progress.connect(self.draw_image_on_gui)

        self.camera_thread.start()

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
            cv_fmts = intersect_pixel_formats(
                cam.get_pixel_formats(), OPENCV_PIXEL_FORMATS)
            color_fmts = intersect_pixel_formats(cv_fmts, COLOR_PIXEL_FORMATS)

            if color_fmts:
                cam.set_pixel_format(color_fmts[0])

            else:
                mono_fmts = intersect_pixel_formats(
                    cv_fmts, MONO_PIXEL_FORMATS)

                if mono_fmts:
                    cam.set_pixel_format(mono_fmts[0])

                else:
                    abort(
                        'Camera does not support a OpenCV compatible format natively. Abort.')        

    def draw_image_on_gui(self, frame: Frame):
        resized_photo = self.shrink(frame.as_opencv_image())
        pixmap = self.convert_cv_to_pixmap(resized_photo)
        self.camera_feed.setPixmap(pixmap)

    def convert_cv_to_pixmap(self, cv_img):
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cv_img.shape
        bytesPerLine = channel * width
        q_img = QtGui.QImage(cv_img.data, width, height,
                             bytesPerLine, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(q_img)

    def shrink(self, cv_img):
        width = int(cv_img.shape[1] * 5 / 100)
        height = int(cv_img.shape[0] * 5 / 100)

        resized = cv2.resize(cv_img, (width, height),
                             interpolation=cv2.INTER_AREA)
        return resized


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myApp = My_App()
    myApp.show()
    sys.exit(app.exec_())
