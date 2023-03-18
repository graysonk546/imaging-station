// #include <Arduino.h>
// #include <Servo.h>

// static Servo servo;
// static int pos;


// void setup() {
//   servo.attach(PB1);
//   pinMode(LED_BUILTIN, OUTPUT);
//   pos = 11;
// }

// void loop() {
//   for (int i = 0; i < 78; i++)
//   {
//     pos = pos + 2;
//     servo.write(pos);
//     delay(50);
//   }

//   delay(10000);

//   for (int i = 0; i < 78; i++)
//   {
//     pos = pos - 2;
//     servo.write(pos);
//     delay(100);
//   }  

//   delay(10000);
// }

#include "core/serial.h"
#include "core/stepper.h"
#include "core/servo.h"

void setup() 
{
    // make sure system is in a state where it is ready to take pictures here
    serial_init(COMPUTER);
    serial_init(RPI);

    // initilize the servo and stepper motor
    servo_init(ARM, PB1);
    stepper_setSpeed(PLANE, 100);

    // enable pin of stepper
    pinMode(PA7, OUTPUT);
    digitalWrite(PA7, LOW);
}

// void loop()
// {
//     servo_rotateTo(ARM,5);
//     delay(5000);
//     servo_rotateTo(ARM, 156);
//     delay(5000);
// }


typedef enum
{
    ROT_ARM,
    ROT_PLANE,
    WAIT_ON_PIC,
    TAKE_PIC,
    WAIT_ON_RPI
} state_t;

static state_t state = WAIT_ON_RPI;

static char picMessage[] = "picture";

void loop() 
{
    // main control loop switch statement
    switch (state)
    {
        case ROT_ARM:
            serial_send(COMPUTER, "rotating arm down");
            // rotate arm update arm position
            servo_rotateTo(ARM, 156);
            state = TAKE_PIC;
            break;

        case ROT_PLANE:
            serial_send(COMPUTER, "rotating plane");
            // rotate plane update plane position
            if (stepper_getAngle(PLANE) >= 360)
            {
                state = WAIT_ON_RPI;
                stepper_reset(PLANE);
                servo_rotateTo(ARM, 5);
            }
            else
            {
                stepper_rotate(PLANE, 360);
                state = TAKE_PIC;
            }
            break;

        case WAIT_ON_PIC:
            // wait until there is response from the RPi
            serial_send(COMPUTER, "waiting on finished pic");
            if (serial_available(RPI))
            {
                if (serial_handleByte(RPI, serial_read(RPI)))
                {
                    // check whether message is the finished command
                    // if so, determine which state to change to
                    if (strcmp("finished", serial_getMessage(RPI)) == 0)
                    {
                        // state determination
                        if (servo_getAngle(ARM) == 5)
                        {
                            state = ROT_ARM;
                        }
                        else if (stepper_getAngle(PLANE) <= 360)
                        {
                            state = ROT_PLANE;
                        }
                        else
                        {
                            // reset arm to top position
                            state = WAIT_ON_RPI;
                        }
                    }
                }
            }           
            break;

        case TAKE_PIC:
            // serial send take pic
            serial_send(COMPUTER, "requesting picture from rpi");
            serial_send(RPI, picMessage);
            state = WAIT_ON_PIC;
            break;

        case WAIT_ON_RPI:
            // waiting for the RPi to send a request for data collection
            if (serial_available(RPI))
            {
                if (serial_handleByte(RPI, serial_read(RPI)))
                {
                    // check whether message is the start command
                    // if so, change the state to take pic
                    if (strcmp("start", serial_getMessage(RPI)) == 0)
                    {
                        serial_send(COMPUTER, "starting control loop");
                        state = TAKE_PIC;
                    }
                }
            }
            break;
    }
}