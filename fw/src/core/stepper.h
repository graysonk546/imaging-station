

#include <Arduino.h>
#include <Stepper.h>


typedef enum {
    PLANE,
    DEPOSITER
} stepper_id_t;


typedef struct {
    uint16_t angle;
    Stepper stepper;
} stepper_t;

void stepper_rotate(stepper_id_t stepperId, uint16_t angle);

void stepper_setSpeed(stepper_id_t stepperId, uint16_t rpm);