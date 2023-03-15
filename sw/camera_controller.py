

from serial import Serial
import json

if __name__== "__main__":

    s = Serial("/dev/ttyUSB0", 115200)
    s.open()

    while True:
        # wait on serial communication
        if s.in_waiting() > 0:
            # take picture if you get a message
            print("take picture")
            # send a response
            s.write(b"finished")
            

