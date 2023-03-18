

#include "servo.h"

static servo_periph_t servo_arr[] = 
{
    {
        .servo = Servo(),
        .angle = 11
    }
};

void servo_init(servo_id_t servoId, uint8_t pin)
{
    servo_arr[servoId].servo.attach(pin);
    servo_arr[servoId].servo.write(servo_arr[servoId].angle);
}

void servo_rotateTo(servo_id_t servoId, uint8_t angle)
{
    if (servo_arr[servoId].angle > angle)
    {
        for (int i=servo_arr[servoId].angle; i > angle; i-=2)
        {
            servo_arr[servoId].servo.write(i);
            delay(50);
        }
    }
    else
    {
        for (int i=servo_arr[servoId].angle; i < angle; i+=2)
        {
            servo_arr[servoId].servo.write(i);
            delay(50);
        }
    }
    servo_arr[servoId].angle = angle;
}

uint8_t servo_getAngle(servo_id_t servoId)
{
    return servo_arr[servoId].angle;
}



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
