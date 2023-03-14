import cv2
from vimba import *
import threading

class Handler:
    def __init__(self):
        print("Created Handler")
        self.shutdown_event = threading.Event()

    def __call__(self, cam: Camera, frame: Frame):
        print("Received frame maybe")
        ENTER_KEY_CODE = 13

        key = cv2.waitKey(1)
        if key == ENTER_KEY_CODE:
            self.shutdown_event.set()
            return

        elif frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

        cam.queue_frame(frame)

def setup_camera(cam:Camera):
    with cam:
        try:
            cam.ExposureTime.set(100)
            cam.ExposureAuto.set('Off')

        except (AttributeError, VimbaFeatureError):
            pass

        # Enable white balancing if camera supports it
        try:
            cam.BalanceWhiteAuto.set('Once')

        except (AttributeError, VimbaFeatureError):
            pass

def streamer(input_cam):
    with Vimba.get_instance() as vimba:
        with input_cam as cam:
            print("--gotcha--")
            setup_camera(camera)

            cam.start_streaming(handler=image_handler, buffer_count=10)
            image_handler.shutdown_event.wait()
            cam.stop_streaming()

if __name__ == "__main__":
    image_handler = Handler()
    with Vimba.get_instance() as vimba:
        cams = vimba.get_all_cameras()
        camera = cams[0]
        # setup_camera(camera)

    
        streamer(camera)

    
