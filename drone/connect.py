'''
connect.py
Handles drone connection and connection termination via MAVSDK.
'''
import asyncio
from mavsdk import System
from logger import log_message, log_error, log_event
from config import (
    SIM_MODE,
    DRONE_CONNECTION_PATH,
    CONNECTION_TIMEOUT,
    MAX_CONNECTION_RETRIES,
    OFFBOARD_TIMEOUT,
    INITIAL_RETRY_DELAY,
    RETRY_BACKOFF_MULTIPLIER
)
from .state import (
    get_instance,
    reset_instance,
    get_offboard_state
)

async def wait_for_connection():
    """Attempt to connect to the drone via drone telemetry."""
    # Attempt to confirm connection within the timeout period.
    drone = get_instance()
    startTime = asyncio.get_event_loop().time()

    async for state in drone.core.connection_state():
        if state.is_connected:
            log_event("Drone connection confirmed.")
            return True

        # Break if timeout is exceeded
        if (asyncio.get_event_loop().time() - startTime) >= CONNECTION_TIMEOUT:
            log_error("Connection attempt timed out")
            break

        await asyncio.sleep(0.1)

    return False

async def connect_to_drone():
    """Establish a connection to the drone."""
    retryDelay = INITIAL_RETRY_DELAY    # Current delay between retries

    # Establish the drone instance
    drone = get_instance()

    # In simulation mode, skip the connection process
    if SIM_MODE:
        log_event("Simulation mode enabled. Skipping drone connection.")
        return None
    
    # Attempt to connect to the drone while under the retry limit
    retryCount = 0
    while retryCount < MAX_CONNECTION_RETRIES:
        try:
            # Displays connection attempt message
            attemptMsg = (
                f"Attempting to connect to drone "
                f"(Attempt {retryCount + 1}/{MAX_CONNECTION_RETRIES})..."
            )
            log_event(attemptMsg)
            await asyncio.wait_for(
                drone.connect(system_address=DRONE_CONNECTION_PATH),
                timeout=CONNECTION_TIMEOUT
            )

            # Attempt to establish connection within the timeout period
            isConnectionEstablished = await asyncio.wait_for(
                wait_for_connection(),
                timeout=CONNECTION_TIMEOUT
            )

            # Verify connection stability
            if isConnectionEstablished:
                msg = "Successfully connected to the drone. Verifying stability..."
                log_event(msg)
                await asyncio.sleep(1.0)

                try:
                    isConnectionStable = await asyncio.wait_for(
                        wait_for_connection(),
                        timeout=CONNECTION_TIMEOUT
                    )
                    if isConnectionStable:
                        log_event("Connection stable.")
                        return
                    else:
                        raise ConnectionError("Connection lost during verification.")
                except asyncio.TimeoutError:
                    raise ConnectionError("Connection verification timed out.")
            else:
                raise ConnectionError("Failed to establish connection.")
        
        # Timeout error handling
        except asyncio.TimeoutError:
            retryCount += 1
            if retryCount < MAX_CONNECTION_RETRIES:
                msg = (
                    f"Connection attempt timed out. "
                    f"Retrying in {retryDelay} seconds..."
                )
                log_message(msg)
                await asyncio.sleep(retryDelay)
                retryDelay *= RETRY_BACKOFF_MULTIPLIER
            else:
                msg = (
                    "Maximum connection attempts reached. "
                    "Unable to connect to the drone"
                )
                log_error(msg)
                err_msg = (
                    f"Drone connection failed after "
                    f"{MAX_CONNECTION_RETRIES} attempts."
                )
                raise ConnectionError(err_msg)
        
        # Connection error handling
        except ConnectionError as e:
            retryCount += 1
            if retryCount < MAX_CONNECTION_RETRIES:
                msg = (
                    f"Connection error occurred: {e}. "
                    f"Retrying in {retryDelay} seconds..."
                )
                log_error(msg)
                await asyncio.sleep(retryDelay)
                retryDelay *= RETRY_BACKOFF_MULTIPLIER
            else:
                msg = (
                    f"Maximum connection attempts reached. "
                    f"Unable to connect to the drone. Last error: {e}"
                )
                log_error(msg)
                err_msg = (
                    f"Drone connection failed after "
                    f"{MAX_CONNECTION_RETRIES} attempts."
                )
                raise ConnectionError(err_msg)
        
        # Unexpected error handling
        except Exception as e:
            retryCount += 1
            if retryCount < MAX_CONNECTION_RETRIES:
                log_error(f"Unexpected error occurred", e)
                log_message(f"Retrying in {retryDelay} seconds...")
                await asyncio.sleep(retryDelay)
                retryDelay *= RETRY_BACKOFF_MULTIPLIER
            else:
                log_error(
                    "Maximum connection attempts reached. "
                    "Unable to connect to the drone. Last error",
                    e
                )
                err_msg = (
                    f"Drone connection failed after "
                    f"{MAX_CONNECTION_RETRIES} attempts."
                )
                raise ConnectionError(err_msg)

async def cleanup_drone():
    """Cleans drone resources on shutdown."""
    # Clean offboard mode and resets NED position
    try:
        if get_offboard_state() and not SIM_MODE:
            drone = get_instance()
            try:
                await asyncio.wait_for(
                    drone.offboard.stop(),
                    timeout=OFFBOARD_TIMEOUT
                )
            except asyncio.TimeoutError:
                msg = "Timeout while stopping offboard mode during cleanup"
                log_error(msg)
            finally:
                reset_instance()
    
    # General exception handling
    except Exception as e:
        log_error("Error disabling offboard mode", e)