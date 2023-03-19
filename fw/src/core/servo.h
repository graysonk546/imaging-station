
#include <Arduino.h>
#include <Servo.h>

typedef struct {
    Servo servo;
    uint8_t angle;
} servo_periph_t;

typedef enum{
    ARM
} servo_id_t;

void servo_init(servo_id_t servoId, uint8_t pin);

uint8_t servo_getAngle(servo_id_t servoId);

void servo_rotateTo(servo_id_t servoId, uint8_t angle);