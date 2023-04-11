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

import numpy
import torch
import torchvision.transforms.transforms as T
from utils import ModelHelper, DisplayHelper

FOLDER_NAME = "images/imaging_test_{date}"
REMOTE_IMAGE_FOLDER = "gdrive:2306\ Screw\ Sorter/Data/real_image_sets/"
CURRENT_STAGED_IMAGE_FOLDER = ""

CAMERA = None


class CameraWorker(QtCore.QObject):
    upload = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    change_camera_settings = QtCore.pyqtSignal(Camera, int, float, float)
    progress = QtCore.pyqtSignal(numpy.ndarray)

    def __init__(self, filename, model_helper=None, display_helper=None,feed=False):
        super(CameraWorker, self).__init__()
        self.filename = filename
        # Camera config
        self.top_down_exposure_us = 133952
        self.top_down_balance_red = 2.88
        self.top_down_balance_blue = 1.9
        self.side_view_exposure_us = 723824
        self.side_view_balance_red= 2.52
        self.side_view_balance_blue = 1.45

        self.model_helper = model_helper
        self.display_helper = display_helper
        self.feed = feed

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

        # Calibrate camera before starting camera loop
        print("before")
        self.change_camera_settings.emit(CAMERA, self.top_down_exposure_us, self.top_down_balance_red, self.top_down_balance_blue)
        side_view_exposure = False
        print("Waiting for camera settings to finish")
        # Wait 2s for the setup to finish (.emit() is multithreaded)
        time.sleep(2)
        print("Starting Loop")
        while True:
            # Change camera settings AFTER taking top-down shot
            if n == 1 and not side_view_exposure:
                print("sf")
                time.sleep(2)
                self.change_camera_settings.emit(CAMERA, 
                        self.side_view_exposure_us, self.side_view_balance_red, self.side_view_balance_blue)
                # Error occurred with repeatedly running this fcn
                # So, we set this flag immediately after
                side_view_exposure = True
                # Wait 2s for the setup to finish (.emit() is multithreaded)
                time.sleep(2)
            if n >= 10:
                break

            # wait on serial communication
            if s.in_waiting > 0:
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
                            print("Frame saved to mem")
                            
                            frame_cv2 = frame.as_opencv_image()
                            # flip image on both axes (i.e. rotate 180 deg)
                            frame_cv2 = cv2.flip(frame_cv2, -1)

                            if self.feed and n == 0:
                                print("Starting inference...")
                                frame_cv2 = self.display_helper.crop_scale(frame_cv2, scale=0.7)
                                prediction = self.model_helper.predict_single_image(frame_cv2)

                                frame_cv2 = self.display_helper.draw_prediction(frame_cv2, prediction, self.model_helper.mapping)

                            # Draw directly
                            print("Drawing")
                            self.progress.emit(frame_cv2)
                            print("Done Drawing")
                            final_filename = os.path.join(
                                f, self.filename + date + "_" + str(n) + ".tiff")
                            print(final_filename)
                            cv2.imwrite(final_filename, frame_cv2)
                            n += 1
                            # send a message to indicate a picture was saved
                            s.write(b"finished\n")
                            s.flush()

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
            raise Exception('No Cameras accessible. Abort.')
        self.cam = cams[0]
        global CAMERA
        CAMERA = self.cam
        self.setup_camera(self.cam)

        self.filename_variables = OrderedDict()
        self.filename_variables['type'] = None
        self.filename_variables['standard'] = None
        self.filename_variables['subtype'] = None
        self.filename_variables['diameter'] = None
        self.filename_variables['pitch'] = None
        self.filename_variables['length'] = None
        self.filename_variables['width'] = None
        self.filename_variables['inner_diameter'] = None
        self.filename_variables['outer_diameter'] = None
        self.filename_variables['height'] = None
        self.filename_variables['head'] = None
        self.filename_variables['drive'] = None
        self.filename_variables['direction'] = None
        self.filename_variables['material'] = None
        self.filename_variables['finish'] = None
        self.filename_variables[''] = None

        self.activate_camera_feed.clicked.connect(
            self.start_feed_thread
        )
        self.start_imaging_button.clicked.connect(
            self.start_imaging_thread)

        # Assign buttons for labeling
        button_group_dict = {}
        self.FastenerTypeGroup.buttonClicked.connect(
            self.change_fastener_stack)
        self.FastenerTypeGroup.buttonClicked.connect(
            self.reset_filename_variables_when_changing_fastener)
        button_group_dict['FastenerTypeGroup'] = self.FastenerTypeGroup
        self.NutDiameterMetricGroup.buttonClicked.connect(self.assign_diameter)
        button_group_dict['NutDiameterMetricGroup'] = self.NutDiameterMetricGroup
        self.NutFinishGroup.buttonClicked.connect(self.assign_finish)
        button_group_dict['NutFinishGroup'] = self.NutFinishGroup
        self.NutHeightMetricGroup.buttonClicked.connect(self.assign_height)
        button_group_dict['NutHeightMetricGroup'] = self.NutHeightMetricGroup
        self.NutMaterialGroup.buttonClicked.connect(self.assign_material)
        button_group_dict['NutMaterialGroup'] = self.NutMaterialGroup
        self.NutPitchMetricGroup.buttonClicked.connect(self.assign_pitch)
        button_group_dict['NutPitchMetricGroup'] = self.NutPitchMetricGroup
        self.NutStandardGroup.buttonClicked.connect(self.assign_standard)
        self.NutStandardGroup.buttonClicked.connect(
            self.change_nut_standard_stack)
        button_group_dict['NutStandardGroup'] = self.NutStandardGroup
        self.NutDirectionGroup.buttonClicked.connect(self.assign_direction)
        button_group_dict['NutDirectionGroup'] = self.NutDirectionGroup
        self.NutTypeGroup.buttonClicked.connect(self.assign_subtype)
        button_group_dict['NutTypeGroup'] = self.NutTypeGroup
        self.NutWidthMetricGroup.buttonClicked.connect(self.assign_width)
        button_group_dict['NutWidthMetricGroup'] = self.NutWidthMetricGroup

        self.ScrewDiameterMetricGroup.buttonClicked.connect(
            self.assign_diameter)
        button_group_dict['ScrewDiameterMetricGroup'] = self.ScrewDiameterMetricGroup
        self.ScrewDriveGroup.buttonClicked.connect(self.assign_drive)
        button_group_dict['ScrewDriveGroup'] = self.ScrewDriveGroup
        self.ScrewFinishGroup.buttonClicked.connect(self.assign_finish)
        button_group_dict['ScrewFinishGroup'] = self.ScrewFinishGroup
        self.ScrewHeadGroup.buttonClicked.connect(self.assign_head)
        button_group_dict['ScrewHeadGroup'] = self.ScrewHeadGroup
        self.ScrewLengthMetricGroup.buttonClicked.connect(self.assign_length)
        button_group_dict['ScrewLengthMetricGroup'] = self.ScrewLengthMetricGroup
        self.ScrewMaterialGroup.buttonClicked.connect(self.assign_material)
        button_group_dict['ScrewMaterialGroup'] = self.ScrewMaterialGroup
        self.ScrewPitchMetricGroup.buttonClicked.connect(self.assign_pitch)
        button_group_dict['ScrewPitchMetricGroup'] = self.ScrewPitchMetricGroup
        self.ScrewStandardGroup.buttonClicked.connect(self.assign_standard)
        self.ScrewStandardGroup.buttonClicked.connect(
            self.change_screw_standard_stack)
        button_group_dict['ScrewStandardGroup'] = self.ScrewStandardGroup
        self.ScrewDirectionGroup.buttonClicked.connect(self.assign_direction)
        button_group_dict['ScrewDirectionGroup'] = self.ScrewDirectionGroup

        self.WasherFinishGroup.buttonClicked.connect(self.assign_finish)
        button_group_dict['WasherFinishGroup'] = self.WasherFinishGroup
        self.WasherInnerDiameterMetricGroup.buttonClicked.connect(
            self.assign_inner_diameter)
        button_group_dict['WasherInnerDiameterMetricGroup'] = self.WasherInnerDiameterMetricGroup
        self.WasherMaterialGroup.buttonClicked.connect(self.assign_material)
        button_group_dict['WasherMaterialGroup'] = self.WasherMaterialGroup
        self.WasherOuterDiameterMetricGroup.buttonClicked.connect(
            self.assign_outer_diameter)
        button_group_dict['WasherOuterDiameterMetricGroup'] = self.WasherOuterDiameterMetricGroup
        self.WasherStandardGroup.buttonClicked.connect(self.assign_standard)
        self.WasherStandardGroup.buttonClicked.connect(
            self.change_washer_standard_stack)
        button_group_dict['WasherStandardGroup'] = self.WasherStandardGroup
        self.WasherHeightMetricGroup.buttonClicked.connect(self.assign_height)
        button_group_dict['WasherHeightMetricGroup'] = self.WasherHeightMetricGroup
        self.WasherTypeGroup.buttonClicked.connect(self.assign_subtype)
        button_group_dict['WasherTypeGroup'] = self.WasherTypeGroup

        # Mass-connecting all buttons groups to one function
        for group_name, button_group in button_group_dict.items():
            button_group.buttonClicked.connect(self.update_fastener_filename)

        self.upload_gdrive_button.clicked.connect(self.upload_to_gdrive)
        self.discard_images_button.clicked.connect(self.redo_imaging)

        self.model_helper = ModelHelper("./model_v1_m2vsm3.pt")
        self.display_helper = DisplayHelper()

    def assign_height(self,pressed_button):
        self.filename_variables['height'] = pressed_button.text()

    def assign_width(self, pressed_button):
        self.filename_variables['width'] = pressed_button.text()

    def assign_drive(self, pressed_button):
        self.filename_variables['drive'] = pressed_button.text()

    def assign_pitch(self, pressed_button):
        self.filename_variables['pitch'] = pressed_button.text()

    def change_nut_standard_stack(self, pressed_button):
        if pressed_button.text() == "Inch":
            self.nut_standard_stack.setCurrentIndex(1)
        elif pressed_button.text() == "Metric":
            self.nut_standard_stack.setCurrentIndex(2)

    def change_screw_standard_stack(self, pressed_button):
        if pressed_button.text() == "Inch":
            self.screw_standard_stack.setCurrentIndex(1)
        elif pressed_button.text() == "Metric":
            self.screw_standard_stack.setCurrentIndex(2)

    def assign_direction(self, pressed_button):
        self.filename_variables['direction'] = pressed_button.text()

    def assign_finish(self, pressed_button):
        self.filename_variables['finish'] = pressed_button.text()

    def assign_inner_diameter(self, pressed_button):
        self.filename_variables['inner_diameter'] = pressed_button.text()

    def assign_material(self, pressed_button):
        self.filename_variables['material'] = pressed_button.text()

    def assign_outer_diameter(self, pressed_button):
        self.filename_variables['outer_diameter'] = pressed_button.text()

    def assign_standard(self, pressed_button):
        self.filename_variables['standard'] = pressed_button.text()

    def change_washer_standard_stack(self, pressed_button):
        if pressed_button.text() == "Inch":
            self.washer_standard_stack.setCurrentIndex(1)
        elif pressed_button.text() == "Metric":
            self.washer_standard_stack.setCurrentIndex(2)

    def change_fastener_stack(self, pressed_button):
        if pressed_button.text() == "Screw":
            self.fastener_stack.setCurrentIndex(1)
        elif pressed_button.text() == "Washer":
            self.fastener_stack.setCurrentIndex(2)
        elif pressed_button.text() == "Nut":
            self.fastener_stack.setCurrentIndex(3)

    def assign_type(self, pressed_button):
        self.filename_variables['type'] = pressed_button.text()

    def assign_subtype(self, pressed_button):
        self.filename_variables['subtype'] = pressed_button.text()

    def assign_diameter(self, pressed_button):
        self.filename_variables['diameter'] = pressed_button.text()

    def assign_length(self, pressed_button):
        self.filename_variables['length'] = pressed_button.text()

    def assign_head(self, pressed_button):
        self.filename_variables['head'] = pressed_button.text()

    def update_fastener_filename(self):
        current_name = ""
        for key, val in self.filename_variables.items():
            if type(val) is str:
                current_name += val + "_"
        self.fastener_filename.setText(current_name)

    def reset_filename_variables_when_changing_fastener(self, pressed_button):
        text = pressed_button.text()
        if self.filename_variables['type'] == text:
            # effect of clicking on the same button
            return
        else:
            self.reset_filename_variables()
            self.filename_variables['type'] = text
            self.fastener_filename.setText(text)

    def start_feed_thread(self):
        self.start_imaging_thread(feed=True)
    
    def start_imaging_thread(self, feed=False):
        self.camera_thread = QtCore.QThread()
        self.worker = CameraWorker(self.fastener_filename.text(),
                                   model_helper = self.model_helper,
                                   display_helper = self.display_helper,
                                   feed = feed)
        self.worker.moveToThread(self.camera_thread)
        # Connect signals/slots
        self.camera_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.draw_image_on_gui)
        self.worker.change_camera_settings.connect(self.setup_camera)
        self.worker.upload.connect(self.ask_user_for_upload_decision)
        self.worker.finished.connect(self.camera_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.camera_thread.finished.connect(self.camera_thread.deleteLater)
        self.camera_thread.finished.connect(self.reset_filename_variables)
        self.camera_thread.start()

        # switch to camera tab
        self.tabWidget.setCurrentIndex(1)

    def redo_imaging(self):
        # May contain more cleanup later
        self.start_imaging_thread()

    def ask_user_for_upload_decision(self, image_directory):
        global CURRENT_STAGED_IMAGE_FOLDER
        CURRENT_STAGED_IMAGE_FOLDER = image_directory
        # draw images on the page
        images = [os.path.join(image_directory, x)
                  for x in sorted(os.listdir(image_directory))]
        print(images)
        photo_labels = [self.photo1, self.photo2, self.photo3, self.photo4,
                        self.photo5, self.photo6, self.photo7, self.photo8,
                        self.photo9]
        for img, label in zip(images, photo_labels):
            image = cv2.imread(img)
            resized_photo = self.resize_cv_photo(image, 7)
            pixmap = self.convert_cv_to_pixmap(resized_photo)
            label.setPixmap(pixmap)
        self.DriveUploadConfirmStack.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(2)

        # ribbit ribbit ribbit 
        #               _         _
        #   __   ___.--'_`.     .'_`--.___   __
        #  ( _`.'. -   'o` )   ( 'o`   - .`.'_ )
        #  _\.'_'      _.-'     `-._      `_`./_
        # ( \`. )    //\`         '/\\    ( .'/ )
        #  \_`-'`---'\\__,       ,__//`---'`-'_/
        #   \`        `-\         /-'        '/
        #    `                               '   

    def upload_to_gdrive(self):
        # Split input so the gdrive only has the imaging_test_../ folder,
        # and we don't upload the images/ parent folder too
        image_directory = CURRENT_STAGED_IMAGE_FOLDER
        lowest_level_folder = os.path.split(image_directory)[-1]
        upload_path = os.path.join(REMOTE_IMAGE_FOLDER, lowest_level_folder)
        print(f"Uploading to Drive. Path: {upload_path}")
        try:
            rclone.copy(image_directory, upload_path)
        except Exception as e:
            print("You probably need to refresh the token with rclone config.")
            print(str(e))
        print(f"Upload complete")
        self.DriveUploadConfirmStack.setCurrentIndex(1)

    def reset_filename_variables(self):
        # Reset variables for the next thread imaging suite
        for key in self.filename_variables:
            self.filename_variables[key] = None
        self.fastener_filename.setText("")
        # Unclick all buttons? No need?
        return

    def setup_camera(self, cam: Camera, exposure_us=None, balance_red=None, balance_blue=None):
        print("setup")
        with Vimba.get_instance() as vimba:
            with cam:
                # Enable auto exposure time setting if camera supports it
                try:
                    print("exposure")
                    # If exposure_us is set, manually change exposure value
                    if isinstance(exposure_us, int):
                        cam.ExposureAuto.set('Off')
                        cam.ExposureTime.set(exposure_us)
                    else:
                        cam.ExposureAuto.set('Continuous')

                except (AttributeError, VimbaFeatureError) as e:
                    print("error:" + str(e))
                    pass

                # Enable white balancing if camera supports it
                try:
                    print("balance")
                    # If balance is set, manually change white balance value
                    if isinstance(balance_red, float):
                        cam.BalanceWhiteAuto.set('Off')
                        cam.BalanceRatioSelector.set('Red')
                        cam.BalanceRatio.set(balance_red)
                    if isinstance(balance_blue, float):
                        cam.BalanceWhiteAuto.set('Off')
                        cam.BalanceRatioSelector.set('Blue')
                        cam.BalanceRatio.set(balance_blue)
                    else:
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
                        raise Exception(
                            'Camera does not support a OpenCV compatible format natively.')

    def draw_image_on_gui(self, frame):
        resized_photo = self.resize_cv_photo(frame, 20)
        pixmap = self.convert_cv_to_pixmap(resized_photo)
        self.camera_feed.setPixmap(pixmap)

    def convert_cv_to_pixmap(self, cv_img):
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cv_img.shape
        bytesPerLine = channel * width
        q_img = QtGui.QImage(cv_img.data, width, height,
                             bytesPerLine, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(q_img)

    def resize_cv_photo(self, cv_img, percentage):
        width = int(cv_img.shape[1] * percentage / 100)
        height = int(cv_img.shape[0] * percentage / 100)

        resized = cv2.resize(cv_img, (width, height),
                             interpolation=cv2.INTER_AREA)
        return resized


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myApp = My_App()
    myApp.show()
    sys.exit(app.exec_())
