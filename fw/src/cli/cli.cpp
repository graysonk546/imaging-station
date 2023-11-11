#include "cli.h"

#include "core/serial.h"
#include "core/servo.h"
#include "core/stepper.h"
#include "core/light.h"

// rotate the servo to a specific angle
void cli_servoRotateTo(uint8_t argNumber, char* args[])
{
    uint8_t angle = (uint8_t) strtol((const char*) args[0], NULL, 0);

    if (angle > 170 || angle < 15)
    {
        serial_send(COMPUTER, "invalid angle");
    }
    else
    {
        servo_rotateTo(ARM, angle);
    }
}

// update the brightness of the lights
void cli_lightUpdate(uint8_t argNumber, char* args[])
{

    light_id_t light = (light_id_t) strtol((const char*) args[0], NULL, 0);
    uint8_t duty = (uint8_t) strtol((const char*) args[1], NULL, 0);

    if (light == BACK && duty > 80)
    {
        serial_send(COMPUTER, "invalid brightness");
    }
    else if (light == DOME && duty < 20)
    {
        serial_send(COMPUTER, "invalid brightness");
    }
    else
    {
        light_update(light, (brightness_map_t) duty);
    }
}

// set the speed of rotation of the stepper
void cli_stepperSetSpeed(uint8_t argNumber, char* args[])
{
    uint8_t rpm = (uint8_t) strtol((const char*) args[0], NULL, 0);
    if (rpm > 150 || rpm < 50)
    {
        serial_send(COMPUTER, "invalid speed");
    }
    else
    {
        stepper_setSpeed(PLANE, rpm);
    }
}

// steps : plane angle
// 1440  : 360
// 180   : 45


// rotate plane angle degrees count times
void cli_stepperRotate(uint8_t argNumber,char* args[])
{
    uint16_t angle = (uint8_t) strtol((const char*) args[0], NULL, 0);
    uint8_t count = (uint8_t) strtol((const char*) args[1], NULL, 0);

    for (int i=0; i < count; i++)
    {
        stepper_rotate(PLANE, angle / 360.0 * 1440);
        delay(1000);
    }
}
