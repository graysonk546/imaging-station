#include <Arduino.h>

#include "comm/serial.h"

void setup() 
{
    serial_init();
}

void loop() 
{
    if (Serial2.available())
    {
        if (serial_handleByte(Serial2.read()))
        {
            serial_echo();
        }
    }
}