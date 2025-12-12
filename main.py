'''
main.py
Main execution point for Voice Command Recognition and MAVLink Communication.
Script contains audio initialization and main listening loop.
Please refer to README.md for setup and usage instructions before running this script.
'''
import asyncio
import time
import subprocess
from config import PROCESS_INTERVAL, AUDIO_BUFFER_SIZE
from logger import (
    initialize_logger,
    cleanup_logger,
    log_message,
    log_recognition,
    log_error,
    log_event
)
from voice.parser import parse_commands
from drone.command import execute_command
from drone.connect import connect_to_drone, cleanup_drone
from voice.microphone import ensure_headset_profile
from utils import (
    get_stop_requested,
    set_stop_requested,
    get_command_executing,
    set_command_executing
)
from voice.recognizer import (
    initialize_speech_recognition,
    initialize_audio_stream,
    process_audio,
    cleanup_audio
)

# Global variables
model = None    # Vosk model
rec = None      # Kaldi recognizer
p = None        # PyAudio instance
stream = None   # Audio stream

def initialize_audio():
    """Initialize speech recognition and audio stream for audio capture."""
    global model, rec, p, stream

    try:
        # Initialize logger
        logPath = initialize_logger()
        log_event(f"Logger initialized: {logPath}")
        
        # Ensure Bluetooth headset is in correct profile
        headsetOk, sourceName, msg = ensure_headset_profile()
        log_message(msg)
        if not headsetOk:
            raise RuntimeError("Headset mic not ready, aborting.")
        
        # Initialize Vosk model
        model, rec = initialize_speech_recognition()
        log_event("Vosk model loaded.")

        # Initialize PyAudio for audio capture
        p, stream = initialize_audio_stream()
        log_event("Audio stream started. Now listening for commands:")
    
    # General exception handling
    except Exception as e:
        log_error("Error during initialization", e)
        cleanup_audio(p, stream)
        raise

async def process_voice_commands():
    """Separate coroutine for processing voice commands."""
    global stream, rec
    
    prevProcessTime = time.time()   # Last time audio was processed
    
    while True:
        try:
            currentTime = time.time()   # Time at start of loop iteration
            
            # If not enough time has passed, wait
            if currentTime - prevProcessTime < PROCESS_INTERVAL:
                await asyncio.sleep(0.02)
                continue
            
            # Read and process audio with error handling
            try:
                # Captured audio data
                data = stream.read(
                    AUDIO_BUFFER_SIZE,
                    exception_on_overflow=False
                )

                # Recognized command from audio data
                command = process_audio(rec, data)

            # General exception handling 
            except Exception as audioError:
                log_error("Audio read error", audioError)
                await asyncio.sleep(0.1)
                continue
            
            if command:
                log_recognition(command)
                
                # Check for immediate STOP command
                isExecuting = get_command_executing()
                if isExecuting and ('stop' in command.lower()):
                    # Fast path for stop commands
                    parsedCommands = parse_commands(command)
                    if parsedCommands and parsedCommands[0][0] == "STOP":
                        msg = (
                            "STOP command received. "
                            "Interrupting current operation."
                        )
                        log_event(msg)
                        set_stop_requested(True)
                        continue
                
                # Only process new commands if nothing is executing
                if not isExecuting:
                    parsedCommands = parse_commands(command)

                    if parsedCommands:
                        # Create task to execute commands without blocking
                        # audio loop
                        task = execute_command_chain(parsedCommands)
                        asyncio.create_task(task)
                    else:
                        msg = f"No valid commands found in: '{command}'"
                        log_message(msg)
            
            prevProcessTime = currentTime

        # General exception handling
        except Exception as e:
            log_error("Audio processing error", e)
            await asyncio.sleep(0.1)

async def execute_command_chain(parsedCommands):
    """
    Execute a chain of commands with interrupt support.
    Args:
        parsedCommands: List of parsed command tuples (cmdType, distVal, distType)
    """
    try:
        set_command_executing(True)
        set_stop_requested(False)
        
        if len(parsedCommands) > 1:
            log_event(f"Executing {len(parsedCommands)} sequential commands:")
            for i, commandData in enumerate(parsedCommands, 1):
                # Check for stop request before each command
                if get_stop_requested():
                    log_event("Command chain interrupted by STOP command!")
                    break
                    
                log_message(f"    Step {i}: ", printToConsole=False)
                result = await execute_command(*commandData)
                
                # Check for shutdown signal
                if result == "SHUTDOWN":
                    msg = (
                        "Shutdown command received. "
                        "Cleaning up and powering off Jetson..."
                    )
                    log_event(msg)
                    await cleanup()
                    system_shutdown()
                    raise SystemExit(0)
        else:
            result = await execute_command(*parsedCommands[0])

            # Check for shutdown signal
            if result == "SHUTDOWN":
                msg = (
                    "Shutdown command received. "
                    "Cleaning up and powering off Jetson..."
                )
                log_event(msg)
                await cleanup()
                system_shutdown()
                raise SystemExit(0)
    
    # General exception handling
    except Exception as e:
        log_error("Error executing command chain", e)
    finally:
        set_command_executing(False)
        set_stop_requested(False)

async def listen():
    """Main listening loop with concurrent command processing."""
    try:
        await connect_to_drone()
        
        # Start voice processing as a background task
        voice_task = asyncio.create_task(process_voice_commands())
        
        # Keep the main loop running
        try:
            await voice_task
        
        # User interrupt handling
        except KeyboardInterrupt:
            voice_task.cancel()
            raise

    # User interrupt handling        
    except KeyboardInterrupt:
        log_event("Keyboard interrupt received. Exiting...")
        await cleanup()
    # General exception handling. Clean resources before exiting
    except Exception as e:
        log_error("Unexpected error in listen loop", e)
        await cleanup()

async def cleanup():
    """Clean all resources."""
    global p, stream

    try:
        # Clean drone resources
        await cleanup_drone()

        # Clean audio resources
        cleanup_audio(p, stream)
        log_event("Audio resources cleaned.")

        log_event("Cleanup complete. Exiting...")
        
        # Clean up logger last
        cleanup_logger()
    
    # General exception handling
    except Exception as e:
        log_error("Error during cleanup", e)
        cleanup_logger()

def system_shutdown():
    """Shutdown the Jetson Nano (requires passwordless sudo)."""
    try:
        log_event("Initiating system shutdown...")
        
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
    except subprocess.CalledProcessError as e:
        log_error("Failed to shutdown system", e)
        msg = (
            "Note: Ensure the script has passwordless sudo access "
            "for shutdown command."
        )
        log_message(msg)
    except Exception as e:
        log_error("Unexpected error during system shutdown", e)

# Main function
async def main():
    """Main function"""
    try:
        # Initialize audio systems
        initialize_audio()

        # Start listening for commands
        await listen()
    
    # User interrupt handling
    except KeyboardInterrupt:
        log_event("Keyboard interrupt received in main. Exiting...")
    # General exception handling
    except Exception as e:
        log_error("Unexpected error in main", e)
    finally:
        await cleanup()

# Program entry point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_event("Program terminated by user")
    except Exception as e:
        log_error("Fatal error", e)