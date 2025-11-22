"""
parser.py
Parses recognized speech into drone commands.
"""
import re
from config import (
    DIGIT_PATTERN,
    SEPARATOR_PATTERN,
    UNIT_PATTERNS,
    COMMAND_LOOKUP,
    NUM_DICT
)

def parse_commands(input):
    """
    Parse input into command(s).
    Args:
        input: String of recognized speech
    """
    if not input:
        return []
    
    # Split input into potential commands using separators
    try:
        commands = SEPARATOR_PATTERN.split(input.lower())

        # Sort through commands and parse each
        parsedCommands = []
        for command in commands:
            command = command.strip()
            if command:
                result = get_command(command)
                if result[0]:
                    parsedCommands.append(result)
        
        return parsedCommands
    
    # General exception handling
    except Exception as e:
        print(f"Error parsing commands: {e}")
        return []

def get_command(command):
    """
    Extract command type, distance value, and unit type from command
    Args:
        command: Lowercase single command string
    """
    if not command:
        return (None, None, None)
    
    try:
        command = command.strip()
        
        cmdType = None
        remInput = command

        # Sort through command dictionary for matches
        for trigger, cmd in COMMAND_LOOKUP.items():
            if trigger in command:
                cmdType = cmd
                remInput = command.replace(trigger, '', 1).strip()
                break
        
        if not cmdType:
            return (None, None, None)
        
        # Extract distance value and unit type
        distVal, distType = extract_values(remInput)
        return (cmdType, distVal, distType)
    
    # General exception handling
    except Exception as e:
        print(f"Error extracting command: {e}")
        return (None, None, None)
    
def extract_values(input):
    """
    Extract distance and unit from remaining command string.
    Args:
        input: Remaining lowercase command string after extracting command type
    """
    if not input:
        return (None, None)
    
    try:
        input = input.strip()
        
        # Extract numeric value - check digits first (most common case)
        distVal = None
        digitMatch = DIGIT_PATTERN.search(input)
        if digitMatch:
            distVal = int(digitMatch.group())
        else:
            words = input.split()
            total = 0
            for word in words:
                if word in NUM_DICT:
                    total = total * 100 if NUM_DICT[word] == 100 else total + NUM_DICT[word]
                elif total > 0:
                    break
            distVal = total if total > 0 else None
        
        # Extract unit type
        distType = None
        for unit, pattern in UNIT_PATTERNS.items():
            if pattern.search(input):
                distType = unit
                break
        
        # Default unit to meters if no unit is specified
        if distVal and not distType:
            distType = 'meters'

        return (distVal, distType)
    
    # General exception handling
    except Exception as e:
        print(f"Error extracting values: {e}")
        return (None, None)