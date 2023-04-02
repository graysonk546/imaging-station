
#include "stepper.h"

#define STEPS 400
#define STEP_ANGLE 0.9

static stepper_t stepper_arr[] = 
{
    {
        .angle = 0,
        .stepper = Stepper(STEPS, PA5 /*dir*/, PA6 /*step*/)
    }
};

// static Stepper plane = Stepper(STEPS, PA5, PA6);

void stepper_rotate(stepper_id_t stepperId, uint16_t angle)
{
    stepper_arr[stepperId].stepper.step((int16_t) angle * 6 / STEP_ANGLE);
    stepper_arr[stepperId].angle += angle;
}

uint16_t stepper_getAngle(stepper_id_t stepperId) 
{
    return stepper_arr[stepperId].angle;
}

void stepper_setSpeed(stepper_id_t stepperId, uint16_t rpm)
{
    stepper_arr[stepperId].stepper.setSpeed(rpm);
}


void stepper_reset(stepper_id_t stepperId)
{
    stepper_arr[stepperId].angle = 0;
}