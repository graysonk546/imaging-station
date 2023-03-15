/*******************************************************************************
*                               Standard Libraries
*******************************************************************************/

#include "serial.h"

/*******************************************************************************
*                               Header Files
*******************************************************************************/


/*******************************************************************************
*                               Static Functions
*******************************************************************************/

/*******************************************************************************
*                               Constants
*******************************************************************************/

#define SERIAL_TIMEOUT_MS 5000
#define BAUD_RATE 115200

/*******************************************************************************
*                               Structures
*******************************************************************************/

/*******************************************************************************
*                               Variables
*******************************************************************************/

static message_t message
{
    .index = 0
};

HardwareSerial Serial2(USART2);

// static char* args[COMMAND_ARGS_MAX_LEN];
// static char* tokCommand[(COMMAND_ARGS_MAX_LEN + 1)];

/*******************************************************************************
*                               Functions
*******************************************************************************/

void serial_init()
{
    // Begin the serial connection
    Serial2.begin(BAUD_RATE);
}

void serial_send(char* bytes)
{
    Serial2.println(bytes);
}

bool serial_handleByte(char byte)
{
    if (byte == CMD_EOL)
    {
        message.line[message.index] = STRING_EOL;
        message.index = 0;
        // we have reached the end of the message
        return true;
    }
    else
    {
        message.line[message.index++] = byte;
        // we have not yet reached the end of the message
        return false;
    }
}

void serial_echo()
{
    uint8_t i = 0;
    while (message.line[i] != STRING_EOL)
    {
        Serial2.print(message.line[i]);
        i++;
    }
    Serial2.print(CMD_EOL);
}