#include <Arduino.h>

#include "core/serial.h"
#include "core/stepper.h"

void setup() 
{
    // make sure system is in a state where it is ready to take pictures here
    serial_init();
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
            break;
        default:
            break;
    }

    // handling serial data
    if (Serial2.available())
    {
        if (serial_handleByte(Serial2.read()))
        {
            serial_echo();
            stepper_rotate(PLANE, 15);
            char message[] = "{\"data\": \"pic\"}";
            serial_send(message);
        }
    }
}