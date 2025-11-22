"""
logger.py
Handles asynchronous logging to file with timestamps.
"""
import asyncio
import os
import queue
import threading
from datetime import datetime
from pathlib import Path


# Global logging queue and thread
_logQueue = queue.Queue()
_loggingThread = None
_logFile = None
_stopLogging = False

def initialize_logger():
    """Initialize the logging system and create the log file."""
    global _loggingThread, _logFile
    
    # Create logs directory if it doesn't exist
    logsDir = Path("logs")
    logsDir.mkdir(exist_ok=True)
    
    # Generate log filename with current date and time
    now = datetime.now()
    logFilename = f"LOG {now.strftime('%d_%m %H_%M')}.txt"
    logPath = logsDir / logFilename
    
    # Open log file
    _logFile = open(logPath, 'w', encoding='utf-8')
    
    # Start background logging thread
    _loggingThread = threading.Thread(target=_logging_worker, daemon=True)
    _loggingThread.start()
    
    # Write log header
    log_message(f"=== Log started at {now.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    return str(logPath)

def _logging_worker():
    """Background worker thread that writes log entries to file."""
    global _logFile, _stopLogging
    
    while not _stopLogging:
        try:
            # Get message from queue with timeout
            message = _logQueue.get(timeout=0.1)
            
            # Check for sentinel value to stop logging
            if message is None:
                break
            
            # Write to file and flush immediately
            _logFile.write(message + '\n')
            _logFile.flush()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Logging error: {e}")

def log_message(message, printToConsole=True):
    """
    Log a message with timestamp.
    Args:
        message: Message to log
        printToConsole: Whether to also print to console (default: True)
    """
    # Generate timestamp
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
    
    # Format log entry
    logEntry = f"[{timestamp}] {message}"
    
    # Print to console if requested
    if printToConsole:
        print(message)
    
    # Add to logging queue (non-blocking)
    try:
        _logQueue.put_nowait(logEntry)
    except queue.Full:
        # If queue is full, skip this message to avoid blocking
        pass

def log_command(cmdType, distVal=None, distType=None):
    """
    Log a drone command with timestamp.
    Args:
        cmdType: Command type
        distVal: Distance value (optional)
        distType: Distance unit type (optional)
    """
    if distVal and distType:
        message = f"Command: {cmdType} {distVal} {distType}"
    elif distVal:
        message = f"Command: {cmdType} {distVal}"
    else:
        message = f"Command: {cmdType}"
    
    log_message(message)

def log_recognition(recognizedText):
    """
    Log recognized speech with timestamp.
    Args:
        recognizedText: The recognized speech text
    """
    log_message(f"Recognized: '{recognizedText}'")

def log_error(errorMessage, exception=None):
    """
    Log an error with timestamp.
    Args:
        errorMessage: Error description
        exception: Exception object (optional)
    """
    if exception:
        message = f"ERROR: {errorMessage} - {str(exception)}"
    else:
        message = f"ERROR: {errorMessage}"
    
    log_message(message)

def log_event(eventMessage):
    """
    Log a general event with timestamp.
    Args:
        eventMessage: Event description
    """
    log_message(eventMessage)

def cleanup_logger():
    """Clean up logging resources."""
    global _loggingThread, _logFile, _stopLogging
    
    try:
        # Signal logging thread to stop
        _stopLogging = True
        _logQueue.put(None)  # Sentinel value
        
        # Wait for thread to finish with timeout
        if _loggingThread and _loggingThread.is_alive():
            _loggingThread.join(timeout=2.0)
        
        # Close log file
        if _logFile:
            log_message("=== Log ended ===", printToConsole=False)
            _logFile.close()
            _logFile = None
    
    except Exception as e:
        print(f"Error cleaning up logger: {e}")
