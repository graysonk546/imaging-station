
#include "servo.h"
#include "serial.h"
#include <stdio.h>

static servo_periph_t servo_arr[] = 
{
    {
        .servo = Servo(),
        .angle = 15
    }
};

float _angle_to_duty(uint8_t angle)
{
    // return 2.0 + angle / 180.0 * 10.0;
    return 1310.0 + angle / 180.0 * 6553;
}

void servo_init(servo_id_t servoId, uint8_t pin)
{
    pinMode(PB1, OUTPUT);
    pwm_start(PB_1, 50, _angle_to_duty(15), TimerCompareFormat_t::RESOLUTION_16B_COMPARE_FORMAT);
}

// void servo_init(servo_id_t servoId, uint8_t pin)
// {
//     servo_arr[servoId].servo.attach(pin);
//     servo_arr[servoId].servo.write(servo_arr[servoId].angle);
// }

void servo_rotateTo(servo_id_t servoId, uint8_t angle)
{
    if (servo_arr[servoId].angle > angle)
    {
        for (int i=servo_arr[servoId].angle; i > angle; i-=2)
        {
            pwm_start(PB_1, 50, _angle_to_duty(i), TimerCompareFormat_t::RESOLUTION_16B_COMPARE_FORMAT);
            // servo_arr[servoId].servo.write(i);
            delay(30);
            // delay(100); // 50
        }
    }
    else
    {
        for (int i=servo_arr[servoId].angle; i < angle; i+=2)
        {
            // serial_send(COMPUTER, "here");
            Serial.println(_angle_to_duty(i));
            pwm_start(PB_1, 50, _angle_to_duty(i), TimerCompareFormat_t::RESOLUTION_16B_COMPARE_FORMAT); // PERCENT_COMPARE_FORMAT
            delay(30);
            // servo_arr[servoId].servo.write(i);
            // delay(100); // 50
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
