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

// static message_t message
// {
//     .index = 0
// };

static serial_conn_t serial_arr[] = 
{
    {
        .message =
        {
            .index = 0
        },
        .connection = new HardwareSerial(USART2)
    }
};

// HardwareSerial Serial2 = new HardwareSerial(USART2);

// HardwareSerial Serial2(USART2);

// static char* args[COMMAND_ARGS_MAX_LEN];
// static char* tokCommand[(COMMAND_ARGS_MAX_LEN + 1)];

/*******************************************************************************
*                               Functions
*******************************************************************************/

// could init, read, and send methods be replaced with a single getter method 
//    for the specific serial_conn_t in the serial_arr?

void serial_init(serial_id_t serialId)
{
    // Begin the serial connection
    serial_arr[serialId].connection.begin(BAUD_RATE);

    // Serial2.begin(BAUD_RATE);
}

bool serial_available(serial_id_t serialId)
{
    return serial_arr[serialId].connection.available() > 0;
}

char serial_read(serial_id_t serialId)
{
    return serial_arr[serialId].connection.read();
}

void serial_send(serial_id_t serialId, char* bytes)
{
    serial_arr[serialId].connection.println(bytes);
    // Serial2.println(bytes);
}

bool serial_handleByte(serial_id_t serialId, char byte)
{   
    serial_conn_t s = serial_arr[serialId];

    if (byte == CMD_EOL)
    {
        s.message.line[s.message.index] = STRING_EOL;
        s.message.index = 0;
        // we have reached the end of the message
        return true;
    }
    else
    {
        s.message.line[s.message.index++] = byte;
        // we have not yet reached the end of the message
        return false;
    }
}

void serial_echo(serial_id_t serialId)
{
    serial_conn_t s = serial_arr[serialId];
    uint8_t i = 0;
    while (s.message.line[i] != STRING_EOL)
    {
        s.connection.print(s.message.line[i]);
        i++;
    }
    s.connection.print(CMD_EOL);
}