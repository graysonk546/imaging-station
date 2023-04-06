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
from collections import OrderedDict
from rclone_python import rclone

FOLDER_NAME = "images/imaging_test_{date}"
REMOTE_IMAGE_FOLDER = "gdrive:2306\ Screw\ Sorter/Data/real_image_sets/"

CAMERA = None

class CameraWorker(QtCore.QObject):
    upload = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    progress = QtCore.pyqtSignal(Frame)

    def __init__(self, filename):
        super(CameraWorker, self).__init__()
        self.filename = filename

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
        if not os.path.exists("images"):
            os.mkdir("images")
        os.mkdir(f)
        n = 0
        print("Starting Loop")
        while True:
            # wait on serial communication
            if s.in_waiting > 0 or True:
                time.sleep(1)
                message = "picture\r\n"
                # message = s.readline().decode("ascii")
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
                            final_filename = os.path.join(f, self.filename + str(n) + ".tiff")
                            print(final_filename)
                            frame.convert_pixel_format(PixelFormat.Mono8)
                            cv2.imwrite(final_filename,
                                        frame.as_opencv_image())
                            n += 1
                            # send a message to indicate a picture was saved
                            s.write(b"finished\n")
                            s.flush()
                    
                if n == 2:
                    break

                elif message == "finished-imaging\r\n":
                    # exit the control loop
                    break
        self.upload.emit(f)
        self.finished.emit()

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

        self.filename_variables = OrderedDict()

        self.filename_variables['type'] = None
        self.filename_variables['diameter'] = None
        self.filename_variables['length'] = None
        self.filename_variables['head'] = None

        self.start_imaging_button.clicked.connect(
            self.start_imaging_thread)

        # Assign buttons for labeling
        self.FastenerTypeGroup.buttonClicked.connect(self.assign_fastener_type)
        self.FastenerTypeGroup.buttonClicked.connect(self.update_fastener_filename)
        self.MetricSizeGroup.buttonClicked.connect(self.assign_fastener_diameter)
        self.MetricSizeGroup.buttonClicked.connect(self.update_fastener_filename)
        self.MetricLengthGroup.buttonClicked.connect(self.assign_fastener_length)
        self.MetricLengthGroup.buttonClicked.connect(self.update_fastener_filename)
        self.HeadTypeGroup.buttonClicked.connect(self.assign_fastener_head)
        self.HeadTypeGroup.buttonClicked.connect(self.update_fastener_filename)

    def assign_fastener_type(self, pressed_button):
        self.filename_variables['type'] = pressed_button.text()

    def assign_fastener_diameter(self, pressed_button):
        self.filename_variables['diameter'] = pressed_button.text()

    def assign_fastener_length(self, pressed_button):
        self.filename_variables['length'] = pressed_button.text()

    def assign_fastener_head(self, pressed_button):
        self.filename_variables['head'] = pressed_button.text()

    def update_fastener_filename(self):
        current_name = ""
        for key, val in self.filename_variables.items():
            if type(val) is str:
                current_name += val + "_"
        self.fastener_filename.setText(current_name)
    
    def start_imaging_thread(self):
        self.camera_thread = QtCore.QThread()
        self.worker = CameraWorker(self.fastener_filename.text())
        self.worker.moveToThread(self.camera_thread)
        # Connect signals/slots
        self.camera_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.draw_image_on_gui)
        self.worker.upload.connect(self.upload_to_gdrive)
        self.worker.finished.connect(self.camera_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.camera_thread.finished.connect(self.camera_thread.deleteLater)
        self.camera_thread.finished.connect(self.clean_up_between_runs)
        self.camera_thread.start()

        # switch to camera tab
        self.tabWidget.setCurrentIndex(1)

    def upload_to_gdrive(self, image_directory):
        # Split input so the gdrive only has the imaging_test_../ folder,
        # and we don't upload the images/ parent folder too
        lowest_level_folder = os.path.split(image_directory)[-1]
        upload_path = os.path.join(REMOTE_IMAGE_FOLDER, lowest_level_folder)
        print(f"Uploading to Drive. Path: {upload_path}")
        rclone.copy(image_directory, upload_path)
        print(f"Upload complete")

    def clean_up_between_runs(self):
        # Reset variables for the next thread imaging suite
        for key in self.filename_variables:
            self.filename_variables[key] = None
        self.fastener_filename.setText("")
        # Unclick all buttons? No need?
        return

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
        width = int(cv_img.shape[1] * 20 / 100)
        height = int(cv_img.shape[0] * 20 / 100)

        resized = cv2.resize(cv_img, (width, height),
                             interpolation=cv2.INTER_AREA)
        return resized


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myApp = My_App()
    myApp.show()
    sys.exit(app.exec_())
