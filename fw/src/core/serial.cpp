/*******************************************************************************
*                               Standard Libraries
*******************************************************************************/

#include <Arduino.h>
#include "serial.h"
#include "command-listing.h"

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


static char* args[COMMAND_ARGS_MAX_LEN];
static char* tokCommand[(COMMAND_ARGS_MAX_LEN + 1)];


HardwareSerial Serial2(USART2);

static serial_conn_t serial_arr[] = 
{
    {
        .message =
        {
            .index = 0
        },
        .connection = &Serial2
    },
    {
        .message =
        {
            .index = 0
        },
        .connection = &Serial1
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
    // Serial1.begin(BAUD_RATE);

    serial_arr[serialId].connection->begin(BAUD_RATE);

    // serial_arr[serialId].connection.println("here");
    // Serial2.begin(BAUD_RATE);
}

bool serial_available(serial_id_t serialId)
{
    return serial_arr[serialId].connection->available() > 0;
}

char serial_read(serial_id_t serialId)
{
    return serial_arr[serialId].connection->read();
}

void serial_send(serial_id_t serialId, char* bytes)
{
    serial_arr[serialId].connection->println(bytes);
    // Serial2.println(bytes);
}

bool serial_handleByte(serial_id_t serialId, char byte)
{   
    serial_conn_t* s = &serial_arr[serialId];

    if (byte == CMD_EOL)
    {
        s->message.line[s->message.index] = STRING_EOL;
        s->message.index = 0;
        // we have reached the end of the message
        return true;
    }
    else
    {
        s->message.line[s->message.index++] = byte;
        // we have not yet reached the end of the message
        return false;
    }
}

void serial_echo(serial_id_t serialId)
{
    serial_conn_t* s = &serial_arr[serialId];

    uint8_t i = 0;
    while (s->message.line[i] != STRING_EOL)
    {
        s->connection->print(s->message.line[i]);
        i++;
    }
    s->connection->print(CMD_EOL);
}

void serial_parseCmd(char* message)
{
    // Tokenize the line with spaces as the delimiter
    char* tok = (char*) strtok(message, " ");
    uint8_t i = 0;
    while (tok != NULL && i < COMMAND_BUFF_MAX_LEN)
    {
        tokCommand[i] = tok;
        tok = strtok(NULL, " ");
        i++;
    }

    // Find a match for the command entered
    uint8_t j = 0;
    while (strcmp(commandArr[j].command, LIST_TERMINATOR) != 0)
    {
        if (strcmp(commandArr[j].command, tokCommand[0]) == 0)
        {
            break;
        }
        j++;
    }

    // Process the command entered
    if (strcmp(message, "") != 0)
    {
        if (strcmp(commandArr[j].command, LIST_TERMINATOR) == 0)
        {
            Serial.println("invalid command");
        }
        else if ((i - 1) > commandArr[j].maxParam)
        {
            Serial.println("too many args");
        }
        else if ((i - 1) < commandArr[j].minParam)
        {
            Serial.println("too few args");
        }
        else
        {
            // Package the args into a char* array
            for (uint8_t k = 1; k < i; k++)
            {
                args[(k - 1)] = tokCommand[k];
            }

            // Call the function corresponding to the comannd with args
            cli_func_t func = commandArr[j].function;
            func(i, args);

            // Don't know why there was an if else here
            // if (j == 0)
            // {
            //     // Call the function corresponding to the command with no args
            //     cli_func_t func = commandArr[j].function;
            //     func (0, NULL);
            // }
            // else
            // {
            //     // Package the args into a char* array
            //     for (uint8_t k = 1; k < i; k++)
            //     {
            //         args[(k - 1)] = tokCommand[k];
            //     }

            //     // Call the function corresponding to the comannd with args
            //     cli_func_t func = commandArr[j].function;
            //     func(i, args);
            // }
        }
    }
    // reset the args and command arrays
    memset(tokCommand, '\0', sizeof(tokCommand));
    memset(args, '\0', sizeof(args));
}

char* serial_getMessage(serial_id_t serialId)
{
    return serial_arr[serialId].message.line;
}