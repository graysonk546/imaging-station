
#include "light.h"

light_periph_t light_arr[] = 
{
    {
        .pin = PA0,
        .pwm_pin = PA_0,
        .brightness = BACK_OFF
    },
    {
        .pin = PA1,
        .pwm_pin = PA_1,
        .brightness = DOME_OFF
    }   
};

uint16_t _brightness_to_duty(brightness_map_t brightness)
{
    return (uint16_t) brightness / 100.0 * 65535;
}

void light_init(light_id_t light)
{
    pinMode(light_arr[light].pin, OUTPUT);
    light_update(light, light_arr[light].brightness);
}

void light_update(light_id_t light, brightness_map_t brightness)
{
    uint16_t duty = _brightness_to_duty(brightness);
    pwm_start(light_arr[light].pwm_pin, 2000, duty, 
              TimerCompareFormat_t::RESOLUTION_16B_COMPARE_FORMAT);
}