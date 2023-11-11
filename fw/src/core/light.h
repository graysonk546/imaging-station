#include <Arduino.h>

typedef enum
{
    BACK,
    DOME
} light_id_t;

typedef enum {
    BACK_OFF = 0,
    BACK_ON = 5,
    DOME_OFF = 100,
    DOME_ON = 50
} brightness_map_t;

typedef struct
{
    uint8_t pin;
    PinName pwm_pin;
    brightness_map_t brightness;
} light_periph_t;

void light_init(light_id_t light);

void light_update(light_id_t light, brightness_map_t brightness);