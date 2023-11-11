
#include <Arduino.h>

// rotate the servo to a specific angle
void cli_servoRotateTo(uint8_t argNumber, char* args[]);

// update the brightness of the lights
void cli_lightUpdate(uint8_t argNumber, char* args[]);

// set the speed of rotation of the stepper
void cli_stepperSetSpeed(uint8_t argNumber, char* args[]);

// rotate a particular angle, a particular number of times
void cli_stepperRotate(uint8_t argNumber,char* args[]);

#define CLI_COMMANDS                                                             \
    {cli_servoRotateTo, "servo-rotate", "angle", "rotates servo to angle", 1, 1},\
    {cli_lightUpdate,   "light-update", "light brightness", "changes brightness", 2, 2},\
    {cli_stepperRotate, "stepper-rotate", "angle iterations", "rotates plan number of times", 2, 2},\
    {cli_stepperSetSpeed, "stepper-set", "speed", "sets speed of stepper", 1, 1},\
