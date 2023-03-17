#include <Arduino.h>

#include "core/serial.h"
#include "core/stepper.h"

void setup() 
{
    // make sure system is in a state where it is ready to take pictures here
    serial_init(RPI);
    stepper_setSpeed(PLANE, 100);
    pinMode(PA7, OUTPUT);
    digitalWrite(PA7, LOW);
}

typedef enum
{
    ROT_ARM,
    ROT_PLANE,
    TAKE_PIC,
    RESET_STATION
} state_t;

static state_t state = ROT_ARM;

void loop() 
{
    // stepper_rotate(PLANE, 360);
    // delay(5000);

    // implement logic where the RPi and Bluepill talk back and forth, rotate 
    //  plane -> take picture -> rotate plane... until 360 degrees.




    // main control loop switch statement
    switch (state)
    {
        case ROT_ARM:
            // update arm position

            break;
        case ROT_PLANE:
            // update plane position

            break;
        case TAKE_PIC:
            // serial send take pic

            serial_send(RPI, "");

            break;
        default:
            // waiting for the RPi to send a request for data collection
            if (serial_available(RPI))
            {
                if (serial_handleByte(RPI, serial_read(RPI)))
                {
                    // check whether message is the start command
                    // if so, change the state to take pic

                    serial_echo(RPI);
                    stepper_rotate(PLANE, 360);
                    delay(5);
                    char message[] = "{\"data\": \"pic\"}";
                    serial_send(RPI, message);
                }
            }
            break;
    }

    // handling serial data

    if (serial_available(RPI))
    {
        if (serial_handleByte(RPI, serial_read(RPI)))
        {
            serial_echo(RPI);
            stepper_rotate(PLANE, 360);
            delay(5);
            char message[] = "{\"data\": \"pic\"}";
            serial_send(RPI, message);
        }
    }
}