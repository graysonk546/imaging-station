

#include <Arduino.h>
#include "cli/cli.h"

typedef void (*cli_func_t)(uint8_t argNumber, char* args[]);

typedef struct {
    cli_func_t function;
    const char *command;
    const char *parameters;
    const char *description;
    uint8_t minParam;
    uint8_t maxParam;
} command_t;

/*******************************************************************************
*                               Variables
*******************************************************************************/

#define LIST_TERMINATOR "END_OF_LIST"

/*******************************************************************************
*                               Functions
*******************************************************************************/

// array mapping commands to functions
static const command_t commandArr[] = {
    CLI_COMMANDS
    {NULL, LIST_TERMINATOR, NULL, NULL, 0, 0}
};