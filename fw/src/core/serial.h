#ifndef SERIAL_COMM
#define SERIAL_COMM

/*******************************************************************************
*                               Standard Includes
*******************************************************************************/

#include <Arduino.h>

/*******************************************************************************
*                               Header File Includes
*******************************************************************************/

/*******************************************************************************
*                               Static Functions
*******************************************************************************/

/*******************************************************************************
*                               Constants
*******************************************************************************/

#define CMD_EOL              '\n'
#define STRING_EOL           '\0'
#define COMMAND_BUFF_MAX_LEN 30
#define COMMAND_ARGS_MAX_LEN 4
#define COMMAND_PROMPT       "station> "

/*******************************************************************************
*                               Structures
*******************************************************************************/

typedef struct {
    // char array to store the message
    char line[COMMAND_BUFF_MAX_LEN];
    // index to add next char received
    uint8_t index;
} message_t;

typedef struct {
    message_t message;
    HardwareSerial* connection;
} serial_conn_t;

typedef enum {
    RPI,
    COMPUTER
} serial_id_t;

/*******************************************************************************
*                               Variables
*******************************************************************************/

/*******************************************************************************
*                               Functions
*******************************************************************************/

void serial_init(serial_id_t serialId);

bool serial_available(serial_id_t serialId); 

char serial_read(serial_id_t serialId);

void serial_send(serial_id_t serialId, char* bytes);

bool serial_handleByte(serial_id_t serialId, char byte);

void serial_echo(serial_id_t serialId);

void serial_parseCmd(char* message);

char* serial_getMessage(serial_id_t serialId);

#endif