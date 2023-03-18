
from time import sleep
import serial
import json

if __name__== "__main__":

    s = serial.Serial("/dev/ttyUSB0", 115200)
    print(s.isOpen())
    sleep(5)
    print(s.write(b"start\n"))
    s.flush()
    while True:
        # wait on serial communication
        if s.in_waiting > 0:
            sleep(1)
            print(s.readline().decode("ascii"))
            # take picture if you get a message
            print("take picture")
            # send a response
            sleep(5)
            s.write(b"finished\n")
            sleep(5)
            s.flush()
