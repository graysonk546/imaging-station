#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from python_qt_binding import loadUi
from fractional_spinbox import CustomDoubleSpinBox

import cv2
import sys
import threading
import time
import serial
import json
import uuid
import re

from vimba import *
import os
from datetime import datetime
from collections import OrderedDict
from rclone_python import rclone

import numpy
import torch
import torchvision.transforms.transforms as T
from utils import ModelHelper, DisplayHelper

# TODO Figure out a better way to move these around ie not globals
TOP_IMAGES_FOLDER = os.path.join(os.path.dirname(__file__), "images")
FULL_SESSION_PATH = ""
REMOTE_IMAGE_FOLDER = "gdrive_more_storage:2357 Screw Sorter/data/raw/real"
CURRENT_STAGED_IMAGE_FOLDER = ""
IMAGING_STATION_VERSION="1.0"
IMAGING_STATION_CONFIGURATION="A1"
FIRST_TIME_SETUP=True
# TODO Be able to toggle these flags in the GUI, communicate w/ bp
TOPDOWN_INCLUDED=True
SIDEON_INCLUDED=True
NUMBER_SIDEON=9

CAMERA = None

class IntroDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        # Create widgets for the dialog
        label = QtWidgets.QLabel("Enter your name:")
        self.username = QtWidgets.QLineEdit(self)
        ok_button = QtWidgets.QPushButton("OK", self)
        ok_button.clicked.connect(self.accept)

        # Create layout for the dialog
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.username)
        layout.addWidget(ok_button)

        # Set the layout for the dialog
        self.setLayout(layout)

    def getUsername(self):
        return self.username.text()

class CameraWorker(QtCore.QObject):
    upload = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    change_camera_settings = QtCore.pyqtSignal(Camera, int, float, float)
    progress = QtCore.pyqtSignal(numpy.ndarray)

    def __init__(self, filename, model_helper=None, display_helper=None,feed=False, app=None):
        super(CameraWorker, self).__init__()
        self.filename = filename
        # Camera config
        self.top_down_exposure_us = 133952
        self.top_down_balance_red = 2.88
        self.top_down_balance_blue = 1.9
        self.side_view_exposure_us = 723824
        self.side_view_balance_red= 2.52
        self.side_view_balance_blue = 1.45

        self.app = app
        self.model_helper = model_helper
        self.display_helper = display_helper
        self.feed = feed

        # Create UUID corresponding to this specific run of fasteners.
        self.fastener_uuid = uuid.uuid4()
        self.fastener_directory = self.setup_fastener_directory(self.fastener_uuid)

    def create_label_json(self, unique_id):
        """Creates json label for specific imaging run. any variables not entered into the GUI will be `None`."""

        if self.app.filename_variables["standard"].lower() == "metric":
            dia_units = "mm"
            len_units = "mm"
            pitch_units = "mm"
            ht_units = "mm"
            wd_units = "mm"
        elif self.app.filename_variables["standard"].lower() == "inch":
            # todo refactor dia_units when we introduce (larger) bolts that don't use ANSI
            dia_units = "ANSI #"
            len_units = "in"
            pitch_units = "TPI"
            ht_units = "in"
            wd_units = "in"
            
        label_json = {
            "uuid": str(unique_id),
            "status": "ok",
            "world": "real",
            "platform_version": IMAGING_STATION_VERSION,
            "platform_configuration": IMAGING_STATION_CONFIGURATION,
            "time": datetime.now().strftime("%s"),
            "fastener_type": self.app.filename_variables["type"].lower(),
            "measurement_system": self.app.filename_variables["standard"].lower(),
            "topdown_included": TOPDOWN_INCLUDED,
            "sideon_included": SIDEON_INCLUDED,
            "number_sideon": NUMBER_SIDEON,
            "attributes":{}
        }
        if label_json["fastener_type"] == "screw":
            attributes = {
                "length": str(self.app.filename_variables["length"]) + " " + len_units,
                "diameter": str(self.app.filename_variables["diameter"]) + " " + dia_units,
                "pitch": str(self.app.filename_variables["pitch"]) + " " + pitch_units,
                "head": self.app.filename_variables["head"].lower(),
                "drive": self.app.filename_variables["drive"].lower(),
                "direction": self.app.filename_variables["direction"].lower(),
                "finish": self.app.filename_variables["finish"].lower()
            }
        elif label_json["fastener_type"] == "washer":
            attributes = {
                "height": str(self.app.filename_variables["height"]) + " " + ht_units,
                "inner_diameter": str(self.app.filename_variables["inner_diameter"]) + " " + dia_units,
                "outer_diameter": str(self.app.filename_variables["outer_diameter"]) + " " + dia_units,
                "finish": self.app.filename_variables["finish"].lower(),
                "subtype": self.app.filename_variables["subtype"].lower()
            }
        elif label_json["fastener_type"] == "nut":
            attributes = {
                "width":str(self.app.filename_variables["width"]) + " " + wd_units,
                "height": str(self.app.filename_variables["height"]) + " " + ht_units,
                "diameter": str(self.app.filename_variables["diameter"]) + " " + dia_units,
                "pitch": str(self.app.filename_variables["pitch"]) + " " + pitch_units,
                "direction": self.app.filename_variables["direction"].lower(),
                "finish": self.app.filename_variables["finish"].lower(),
                "subtype": self.app.filename_variables["subtype"].lower()
            }
        label_json["attributes"] = attributes

        for k, v in label_json.items():
            if not v:
                print(f"{k} not selected properly")

        return label_json

    def setup_fastener_directory(self, fastener_uuid):
        """Create directory and JSON for a single imaging run.
        This directory is created within the session directory -- each imaging run within the session has its own
        folder, which is generated in this function."""
        assert(FULL_SESSION_PATH != "")
        fastener_directory = os.path.join(FULL_SESSION_PATH, "real_" + self.filename + "_" + str(fastener_uuid))
        os.mkdir(fastener_directory)

        label_json = self.create_label_json(fastener_uuid)
        label_json_path = os.path.join(fastener_directory, f"{str(fastener_uuid)}.json")

        with open(label_json_path, "w") as file_obj:
            json.dump(label_json, file_obj)
        return fastener_directory

    def run(self):
        # Calibrate camera before starting camera loop
        print("before")
        self.change_camera_settings.emit(CAMERA, self.top_down_exposure_us, self.top_down_balance_red, self.top_down_balance_blue)
        side_view_exposure = False
        print("Waiting for camera settings to finish")
        # Wait 2s for the setup to finish (.emit() is multithreaded)
        time.sleep(2)

        print("Starting Loop")
        n = 0
        # establish serial communication with Bluepill
        s = serial.Serial("/dev/ttyUSB0", 115200)
        # commence the imaging session with the "start" command
        time.sleep(1)
        print(s.write(b"start\n"))
        s.flush()
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
            # to get around serial comms (ie test w/o bluepill), swap this if-statement with "if True"
            # and replace "message" with "picture\r\n"
            # if True:
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

                            # Draw directly
                            print("Drawing")
                            self.progress.emit(frame_cv2)
                            print("Done Drawing")
                            final_filename = os.path.join(
                                self.fastener_directory, f"{n}_{self.fastener_uuid}.tiff")
                            print(final_filename)
                            cv2.imwrite(final_filename, frame_cv2)
                            n += 1
                            # send a message to indicate a picture was saved
                            s.write(b"finished\n")
                            s.flush()

                elif message == "finished-imaging\r\n":
                    # exit the control loop
                    break

        self.upload.emit(self.fastener_directory)
        self.finished.emit()


class My_App(QtWidgets.QMainWindow):
    def __init__(self, operator_name):
        super(My_App, self).__init__()
        loadUi("./data_collection.ui", self)

        # Dynamically create certain custom widgets and add it to layout (PyQtDesigner can't put it in natively)
        self.screw_length_imperial_double = CustomDoubleSpinBox()
        self.horizontalLayout_25.addWidget(self.screw_length_imperial_double)

        # Set the date for this session
        self.session_date = datetime.now()
        self.operator_name = operator_name
        if self.operator_name == "":
            QMessageBox.warning(self, "Missing Operator Name", "Please fill out the operator name before you begin imaging.")
            raise Exception("Operator name string is empty. Please fill out the box with alphabetical letters before continuing.")
        self.setup_imaging_directory(self.session_date, operator_name)
        self.fastener_record = []

        # Setup quit function. Note this function should be declared after session_date and imaging_directory is made.
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.cleanupFunction)

        # Obtaining camera and applying default settings
        with Vimba.get_instance() as vimba:
            cams = vimba.get_all_cameras()
        if not cams:
            raise Exception("No Cameras accessible. Abort.")
        self.cam = cams[0]
        global CAMERA
        CAMERA = self.cam
        self.setup_camera(self.cam)

        # The order of fields put in here determines the order in the filename.
        self.filename_variables = OrderedDict()
        self.filename_variables["type"] = None
        self.filename_variables["standard"] = None
        self.filename_variables["subtype"] = None
        self.filename_variables["diameter"] = None
        self.filename_variables["pitch"] = None
        self.filename_variables["length"] = None
        self.filename_variables["width"] = None
        self.filename_variables["inner_diameter"] = None
        self.filename_variables["outer_diameter"] = None
        self.filename_variables["height"] = None
        self.filename_variables["head"] = None
        self.filename_variables["drive"] = None
        self.filename_variables["direction"] = None
        self.filename_variables["finish"] = None
        self.filename_variables[""] = None

        self.activate_camera_feed.clicked.connect(
            self.start_feed_thread
        )
        self.start_imaging_button.clicked.connect(
            self.start_imaging_thread)

        # Assign buttons for labeling
        self.FastenerTypeGroup.buttonClicked.connect(
            self.change_fastener_stack)
        self.FastenerTypeGroup.buttonClicked.connect(
            self.reset_filename_variables_when_changing_fastener)
        self.FastenerTypeGroup.buttonClicked.connect(
            self.assign_fastener_type)
        self.NutDiameterMetricGroup.buttonClicked.connect(self.assign_diameter)
        self.NutDiameterImperialGroup.buttonClicked.connect(self.assign_diameter)
        self.NutFinishGroup.buttonClicked.connect(self.assign_finish)
        self.NutPitchMetricGroup.buttonClicked.connect(self.assign_pitch)
        self.NutPitchImperialGroup.buttonClicked.connect(self.assign_pitch)
        self.NutStandardGroup.buttonClicked.connect(
            self.change_nut_standard_stack)
        self.NutDirectionGroup.buttonClicked.connect(self.assign_direction)
        self.NutTypeGroup.buttonClicked.connect(self.assign_subtype)
        self.nut_height_metric_double.textChanged.connect(self.assign_height)
        self.nut_width_metric_double.textChanged.connect(self.assign_width)
        self.nut_height_imperial_double.textChanged.connect(self.assign_height)
        self.nut_width_imperial_double.textChanged.connect(self.assign_width)


        self.ScrewDiameterMetricGroup.buttonClicked.connect(
            self.assign_diameter)
        self.ScrewDiameterImperialGroup.buttonClicked.connect(
            self.assign_diameter)
        self.ScrewDriveGroup.buttonClicked.connect(self.assign_drive)
        self.ScrewFinishGroup.buttonClicked.connect(self.assign_finish)
        self.ScrewHeadGroup.buttonClicked.connect(self.assign_head)
        self.screw_length_imperial_double.textChanged.connect(self.assign_length)
        self.screw_length_metric_double.textChanged.connect(self.assign_length)
        self.ScrewPitchMetricGroup.buttonClicked.connect(self.assign_pitch)
        self.ScrewPitchImperialGroup.buttonClicked.connect(self.assign_pitch)
        self.ScrewStandardGroup.buttonClicked.connect(
            self.change_screw_standard_stack)
        self.ScrewDirectionGroup.buttonClicked.connect(self.assign_direction)

        self.WasherFinishGroup.buttonClicked.connect(self.assign_finish)
        self.washer_inner_diameter_metric_double.textChanged.connect(self.assign_inner_diameter)
        self.washer_inner_diameter_imperial_double.textChanged.connect(self.assign_inner_diameter)
        self.washer_outer_diameter_metric_double.textChanged.connect(self.assign_outer_diameter)
        self.washer_outer_diameter_imperial_double.textChanged.connect(self.assign_outer_diameter)
        self.WasherStandardGroup.buttonClicked.connect(
            self.change_washer_standard_stack)
        self.washer_height_metric_double.textChanged.connect(self.assign_height)
        self.washer_height_imperial_double.textChanged.connect(self.assign_height)
        self.WasherTypeGroup.buttonClicked.connect(self.assign_subtype)

        self.upload_single_fastener_gdrive_button.clicked.connect(self.upload_single_fastener_to_gdrive)
        self.upload_all_sessions_gdrive_button.clicked.connect(self.upload_all_sessions_to_gdrive)
        self.discard_images_button.clicked.connect(self.redo_imaging)

        self.model_helper = None
        self.display_helper = None

    def assign_height(self, height_text):
        self.filename_variables["height"] = height_text
        self.update_fastener_filename()

    def assign_width(self, width_text):
        self.filename_variables["width"] = width_text
        self.update_fastener_filename()

    def assign_drive(self, pressed_button):
        self.filename_variables["drive"] = pressed_button.text()
        self.update_fastener_filename()

    def assign_pitch(self, pressed_button):
        self.filename_variables["pitch"] = pressed_button.text()
        self.update_fastener_filename()

    def change_nut_standard_stack(self, pressed_button):
        # Update GUI appearance
        changed_index = False
        if pressed_button.text() == "Inch":
            if self.nut_standard_stack.currentIndex() != 1:
                self.nut_standard_stack.setCurrentIndex(1)
                changed_index = True
        elif pressed_button.text() == "Metric":
            if self.nut_standard_stack.currentIndex() != 2:
                self.nut_standard_stack.setCurrentIndex(2)
                changed_index = True

        self.filename_variables["standard"] = pressed_button.text()
       # Clear data fields of stack
        if changed_index:
            self.filename_variables["width"] = None
            self.filename_variables["height"] = None
            self.filename_variables["diameter"] = None
            self.filename_variables["pitch"] = None

        self.update_fastener_filename()

    def change_screw_standard_stack(self, pressed_button):
        # Update GUI appearance
        changed_index = False
        if pressed_button.text() == "Inch":
            if self.screw_standard_stack.currentIndex() != 1:
                self.screw_standard_stack.setCurrentIndex(1)
                changed_index = True
        elif pressed_button.text() == "Metric":
            if self.screw_standard_stack.currentIndex() != 2:
                self.screw_standard_stack.setCurrentIndex(2)
                changed_index = True
        
        self.filename_variables["standard"] = pressed_button.text()
        # Clear data fields of stack
        if changed_index:
            self.filename_variables["length"] = None
            self.filename_variables["diameter"] = None
            self.filename_variables["pitch"] = None

        self.update_fastener_filename()

    def assign_direction(self, pressed_button):
        self.filename_variables["direction"] = pressed_button.text()
        self.update_fastener_filename()

    def assign_finish(self, pressed_button):
        self.filename_variables["finish"] = pressed_button.text()
        self.update_fastener_filename()

    def assign_inner_diameter(self, inner_diameter_text):
        self.filename_variables["inner_diameter"] = inner_diameter_text
        self.update_fastener_filename()

    def assign_outer_diameter(self, outer_diameter_text):
        self.filename_variables["outer_diameter"] = outer_diameter_text
        self.update_fastener_filename()

    def change_washer_standard_stack(self, pressed_button):
        # Update GUI appearance
        changed_index = False
        if pressed_button.text() == "Inch":
            if self.washer_standard_stack.currentIndex() != 1:
                self.washer_standard_stack.setCurrentIndex(1)
                changed_index = True
        elif pressed_button.text() == "Metric":
            if self.washer_standard_stack.currentIndex() != 2:
                self.washer_standard_stack.setCurrentIndex(2)
                changed_index = True

        self.filename_variables["standard"] = pressed_button.text()
        # Clear data fields of stack
        if changed_index:
            self.filename_variables["inner_diameter"] = None
            self.filename_variables["outer_diameter"] = None
            self.filename_variables["height"] = None

        self.update_fastener_filename()

    def change_fastener_stack(self, pressed_button):
        if pressed_button.text() == "Screw":
            self.fastener_stack.setCurrentIndex(1)
        elif pressed_button.text() == "Washer":
            self.fastener_stack.setCurrentIndex(2)
        elif pressed_button.text() == "Nut":
            self.fastener_stack.setCurrentIndex(3)
        self.update_fastener_filename()

    def assign_fastener_type(self, pressed_button):
        self.filename_variables["type"] = pressed_button.text()
        self.update_fastener_filename()

    def assign_subtype(self, pressed_button):
        self.filename_variables["subtype"] = pressed_button.text()
        self.update_fastener_filename()

    def assign_diameter(self, pressed_button):
        self.filename_variables["diameter"] = pressed_button.text()
        self.update_fastener_filename()

    def assign_length(self, length_text):
        self.filename_variables["length"] = length_text
        self.update_fastener_filename()

    def assign_head(self, pressed_button):
        self.filename_variables["head"] = pressed_button.text()
        self.update_fastener_filename()

    def cleanupFunction(self):
        print("Performing cleanup operations...")
        ending_time = datetime.now()
        self.create_report_md(ending_time)

    def setup_imaging_directory(self, creation_date, operator_name):
        if not os.path.exists(TOP_IMAGES_FOLDER):
            os.mkdir(TOP_IMAGES_FOLDER)

        date = creation_date.strftime("%y_%m_%d_%H_%M_%S")
        # replace all potential bad filename characters with underscores

        session_name = f"real_img_ses_v{IMAGING_STATION_VERSION}_c{IMAGING_STATION_CONFIGURATION}_{date}_{operator_name}"
        global FULL_SESSION_PATH
        FULL_SESSION_PATH = os.path.join(TOP_IMAGES_FOLDER, session_name)
        os.mkdir(FULL_SESSION_PATH)

    def sanitize_filename(self, filename):
        # Define a regular expression pattern to match invalid filename characters
        invalid_chars = r'[\/:*?"<>|]'

        # Replace invalid characters with underscores
        sanitized_filename = re.sub(invalid_chars, '_', filename)

        return sanitized_filename
 
    def create_report_md(self, end_time):
        """This function is run once upon exit, giving a summary of what was done in the session."""
        report_name = "report.md"
        session_notes = self.session_notes.toPlainText()
        report_string = f"""# Imaging Session Report
# ===
# Imaging Station Version: 1.0
# Imaging Station Configuration: 0
# Date: {self.session_date.isoformat(sep=" ", timespec="milliseconds")}
# Start Time: {self.session_date.isoformat(sep=" ", timespec="milliseconds")}
# End Time: {end_time.isoformat(sep=" ", timespec="milliseconds")}
# Operator: {self.operator_name}
# Operator Notes:
{session_notes}
# Fasteners Imaged This Session:
{self.fastener_record}
"""
        with open(os.path.join(FULL_SESSION_PATH, report_name), "a") as f:
            f.write(report_string)

    def update_fastener_filename(self):
        current_name = ""
        for key, val in self.filename_variables.items():
            if val is not None:
                # attempt conversion to string
                try:
                    str_val = str(val)
                    # strip out slash from fraction
                    str_val = str_val.replace("/", "_")
                    current_name += str_val + "_"
                except TypeError:
                    pass
        self.fastener_filename.setText(current_name)

    def reset_filename_variables_when_changing_fastener(self, pressed_button):
        text = pressed_button.text()
        if self.filename_variables["type"] == text:
            # effect of clicking on the same button
            return
        else:
            self.reset_filename_variables()
            self.filename_variables["type"] = text
            self.fastener_filename.setText(text)

    def start_feed_thread(self):
        self.start_imaging_thread(feed=True)
    
    def start_imaging_thread(self, feed=False):
        self.feed = feed
        print(f"{feed=}")
        self.camera_thread = QtCore.QThread()
        self.worker = CameraWorker(self.fastener_filename.text(),
                                   model_helper = self.model_helper,
                                   display_helper = self.display_helper,
                                   feed = feed, app=self)
        self.fastener_record.append(os.path.basename(self.worker.fastener_directory))
        self.worker.moveToThread(self.camera_thread)
        # Connect signals/slots
        self.camera_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.draw_image_on_gui)
        self.worker.change_camera_settings.connect(self.setup_camera)
        self.worker.upload.connect(self.ask_user_for_upload_decision)
        self.worker.finished.connect(self.camera_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.camera_thread.finished.connect(self.camera_thread.deleteLater)
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
                  for x in sorted(os.listdir(image_directory))
                  if x.endswith(".tiff")]
        print(images)
        # photo_labels corresponds to squares within the GUI
        photo_labels = [self.photo1, self.photo2, self.photo3, self.photo4,
                        self.photo5, self.photo6, self.photo7, self.photo8,
                        self.photo9]
        for img, label in zip(images, photo_labels):
            image = cv2.imread(img)
            resized_photo = self.resize_cv_photo(image, 7)
            pixmap = self.convert_cv_to_pixmap(resized_photo)
            label.setPixmap(pixmap)

        if self.feed:
            image = cv2.imread(images[0])
            print("Starting inference...")
            frame_cv2 = self.display_helper.crop_scale(image, scale=0.7)
            prediction = self.model_helper.predict_single_image(frame_cv2, score_threshold=0.5)

            frame_cv2 = self.display_helper.draw_prediction(frame_cv2, prediction, self.model_helper.mapping)
            resized_photo = self.resize_cv_photo(frame_cv2, 20)
            pixmap = self.convert_cv_to_pixmap(resized_photo)
            self.camera_feed.setPixmap(pixmap)

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

    def upload_all_sessions_to_gdrive(self):
        # TODO Multithread this
        # do an upload of all sessions. Will only push files that have changed compared to what's in the cloud.
        image_directory = TOP_IMAGES_FOLDER
        upload_path = os.path.join(REMOTE_IMAGE_FOLDER)
        print(f"Uploading to Drive. Path: {upload_path}")
        print(f"On-device path: {image_directory}")
        try:
            rclone.copy(image_directory, upload_path)
        except UnicodeDecodeError as uni_e:
            print(str(uni_e))
            print("Error. Wait a few seconds and click 'Upload to Google Drive' again. Consult code for Kenneth commentary.")
            print("If upload continues to fail after multiple retries, try typing this into your command line:")
            print(f"rclone copy {image_directory} {upload_path}")
            return
            # Kenneth commentary: I think it's something to do with the image data not getting flushed to the file, so the copy() function finds files that are empty.
            # I find that it always works after I retry a few times, so it's not a high-prio bug.
        except Exception as e:
            print(str(e))
            print("You probably need to refresh the token with rclone config. Consult the README for a guide on how to do so.")
            return
        print(f"Upload complete")
        self.DriveUploadConfirmStack.setCurrentIndex(1)

    def upload_single_fastener_to_gdrive(self):
        # TODO multithread this.
        # Split input so the gdrive only has the imaging_test_../ folder,
        # and we don't upload the images/ parent folder too
        image_directory = CURRENT_STAGED_IMAGE_FOLDER
        session_folder = os.path.split(FULL_SESSION_PATH)[-1]
        lowest_level_folder = os.path.split(image_directory)[-1]
        upload_path = os.path.join(REMOTE_IMAGE_FOLDER, session_folder, lowest_level_folder)
        print(f"Uploading to Drive. Path: {upload_path}")
        print(f"On-device path: {image_directory}")
        try:
            rclone.copy(image_directory, upload_path)
        except UnicodeDecodeError as uni_e:
            print(str(uni_e))
            print("Error. Wait a few seconds and click 'Upload to Google Drive' again. Consult code for Kenneth commentary.")
            print("If upload continues to fail after multiple retries, try typing this into your command line:")
            print(f"rclone copy {image_directory} {upload_path}")
            return
            # Kenneth commentary: I think it's something to do with the image data not getting flushed to the file, so the copy() function finds files that are empty.
            # I find that it always works after I retry a few times, so it's not a high-prio bug.
        except Exception as e:
            print(str(e))
            print("You probably need to refresh the token with rclone config. Consult the README for a guide on how to do so.")
            return
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
                        cam.ExposureAuto.set("Off")
                        cam.ExposureTime.set(exposure_us)
                    else:
                        cam.ExposureAuto.set("Continuous")

                except (AttributeError, VimbaFeatureError) as e:
                    print("error:" + str(e))
                    pass

                # Enable white balancing if camera supports it
                try:
                    print("balance")
                    # If balance is set, manually change white balance value
                    if isinstance(balance_red, float):
                        cam.BalanceWhiteAuto.set("Off")
                        cam.BalanceRatioSelector.set("Red")
                        cam.BalanceRatio.set(balance_red)
                    if isinstance(balance_blue, float):
                        cam.BalanceWhiteAuto.set("Off")
                        cam.BalanceRatioSelector.set("Blue")
                        cam.BalanceRatio.set(balance_blue)
                    else:
                        cam.BalanceWhiteAuto.set("Continuous")

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
                            "Camera does not support a OpenCV compatible format natively.")

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

    intro_dialog = IntroDialog()
    result = intro_dialog.exec_()

    if result == QtWidgets.QDialog.Accepted:
        operator_name = intro_dialog.getUsername()
        myApp = My_App(operator_name)
        myApp.show()

    sys.exit(app.exec_())
