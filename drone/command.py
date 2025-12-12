'''
command.py
Executes commands to the drone via MAVSDK.
'''
import asyncio
import math
from mavsdk.action import ActionError
from mavsdk.offboard import OffboardError, PositionNedYaw
from utils import convert_to_meters, get_stop_requested
from logger import log_message, log_command, log_error, log_event
from config import (
    SIM_MODE,
    ACTION_TIMEOUT,
    MOVEMENT_TIMEOUT,
    OFFBOARD_TIMEOUT,
    BASE_DIRECTION_OFFSETS
)
from .state import (
    get_instance,
    get_offboard_state,
    set_offboard_state,
    get_ned_position,
    set_ned_position
)

async def check_armed_state(drone):
    """
    Check if the drone is armed.
    Args:
        drone: The drone instance
    """
    try:
        async for armed in drone.telemetry.armed():
            return armed
    except Exception as e:
        log_error("Error checking armed state", e)
        return False

async def check_in_air(drone):
    """
    Check if the drone is in the air.
    Args:
        drone: The drone instance
    """
    try:
        async for inAir in drone.telemetry.in_air():
            return inAir
    except Exception as e:
        log_error("Error checking in-air state", e)
        return False

async def check_gps_fix(drone):
    """
    Check if the drone has a valid GPS fix.
    Args:
        drone: The drone instance
    """
    try:
        async for gpsInfo in drone.telemetry.gps_info():
            # GPS fix type: 0 = No GPS, 1 = No Fix, 2 = 2D Fix, 3 = 3D Fix
            hasFix = gpsInfo.fix_type >= 3
            numSatellites = gpsInfo.num_satellites
            return (hasFix, numSatellites)
    except Exception as e:
        log_error("Error checking GPS fix", e)
        return (False, 0)

async def check_home_position(drone):
    """
    Check if the home position has been set.
    Args:
        drone: The drone instance
    """
    try:
        async for home in drone.telemetry.home():
            # If home position exists and has valid coordinates
            hasHome = (home.latitude_deg != 0.0 or home.longitude_deg != 0.0)
            return hasHome
    except Exception as e:
        log_error("Error checking home position", e)
        return False

async def check_flight_mode(drone):
    """
    Check the current flight mode of the drone.
    Args:
        drone: The drone instance
    """
    try:
        async for flightMode in drone.telemetry.flight_mode():
            return str(flightMode)
    except Exception as e:
        log_error("Error checking flight mode", e)
        return "UNKNOWN"

async def check_health_status(drone):
    """
    Check overall health status of the drone.
    Args:
        drone: The drone instance
    """
    try:
        async for health in drone.telemetry.health():
            healthStatus = {
                'is_gyrometer_calibration_ok': health.is_gyrometer_calibration_ok,
                'is_accelerometer_calibration_ok': health.is_accelerometer_calibration_ok,
                'is_magnetometer_calibration_ok': health.is_magnetometer_calibration_ok,
                'is_local_position_ok': health.is_local_position_ok,
                'is_global_position_ok': health.is_global_position_ok,
                'is_home_position_ok': health.is_home_position_ok
            }
            return healthStatus
    except Exception as e:
        log_error("Error checking health status", e)
        return None

async def execute_command(cmdType, distVal, distType):
    """
    Executes a command from COMMAND_LOOKUP.
    Args:
        cmdType: Command from COMMAND_LOOKUP
        distVal: Distance or angle value (if applicable)
        distType: Unit type for distance (if applicable)
    """
    # Check for stop request at start of command
    if get_stop_requested() and cmdType != "STOP":
        log_message(f"Skipping {cmdType} due to STOP request")
        return
        
    # Get current drone and offboard states
    drone = get_instance()
    offboard = get_offboard_state()

    # Attempt to execute cmdType
    try:
        # Convert distance/angle to standard units (meters/degrees)
        distMeters = convert_to_meters(distVal, distType) if distVal else None

        # In SIM_MODE, skip actual command execution and print the command instead
        if SIM_MODE:
            # If a command that disables offboard is issued, update the offboard state
            if cmdType in ("STOP", "RETURN", "LAND", "DISARM", "SHUTDOWN") and offboard:
                set_offboard_state(False)
            elif cmdType in ("FORWARD", "BACKWARD", "UP", "DOWN", "LEFT", "RIGHT", "RO_LEFT", "RO_RIGHT", "TAKEOFF", "ARM"):
                set_offboard_state(True)
            
            # Print the command
            log_command(cmdType, distVal, distType)
            
            # Return SHUTDOWN if called
            if cmdType == "SHUTDOWN":
                return "SHUTDOWN"
            return
        
        # While SIM_MODE is False, execute commands on the drone
        if offboard and cmdType in ("STOP", "RETURN", "LAND", "DISARM", "SHUTDOWN"):
            try:
                await asyncio.wait_for(drone.offboard.stop(), timeout=OFFBOARD_TIMEOUT)
                offboard = False
                set_offboard_state(offboard)

            # Timeout error handling (still assume offboard is disabled)
            except asyncio.TimeoutError:
                log_error("Offboard stop timed out")
                offboard = False
                set_offboard_state(offboard)
                return

        # Execute basic commands
        if cmdType == "ARM":
            log_command("ARM")
            await asyncio.wait_for(drone.action.arm(), timeout=ACTION_TIMEOUT)
        elif cmdType == "STOP":
            # Check if drone is armed and in the air before holding position
            isArmed = await check_armed_state(drone)
            if not isArmed:
                log_error("Cannot execute STOP: Drone is not armed.")
                return
            
            isInAir = await check_in_air(drone)
            if not isInAir:
                log_error("Cannot execute STOP: Drone is not in the air.")
                return
            
            log_command("STOP")
            await asyncio.wait_for(drone.action.hold(), timeout=ACTION_TIMEOUT)

        elif cmdType == "RETURN":
            # Check if drone is armed before returning to launch
            isArmed = await check_armed_state(drone)
            if not isArmed:
                log_error("Cannot return: Drone is not armed.")
                return
            
            # Check if drone is in the air
            isInAir = await check_in_air(drone)
            if not isInAir:
                log_error("Cannot return: Drone is not in the air.")
                return
            
            log_command("RETURN")
            await asyncio.wait_for(drone.action.return_to_launch(), timeout=ACTION_TIMEOUT)
        elif cmdType == "SHUTDOWN":
            log_command("SHUTDOWN")
            return "SHUTDOWN"
        elif cmdType == "LAND":
            # Check if drone is armed before landing
            isArmed = await check_armed_state(drone)
            if not isArmed:
                log_error("Cannot land: Drone is not armed.")
                return
            
            # Check if drone is in the air
            isInAir = await check_in_air(drone)
            if not isInAir:
                log_error("Cannot land: Drone is already on the ground.")
                return
            
            log_command("LAND")
            await asyncio.wait_for(drone.action.land(), timeout=ACTION_TIMEOUT)
        elif cmdType == "DISARM":
            # Safety check: Do not disarm while in the air
            isInAir = await check_in_air(drone)
            if isInAir:
                log_error("Cannot disarm: Drone is in the air. Please land first.")
                return
            
            log_command("DISARM")
            await asyncio.wait_for(drone.action.disarm(), timeout=ACTION_TIMEOUT)
        elif cmdType == "TAKEOFF":
            # Check if drone is armed before takeoff
            isArmed = await check_armed_state(drone)
            if not isArmed:
                log_error("Cannot takeoff: Drone is not armed. Please arm the drone first.")
                return
            
            # Log current flight mode
            currentMode = await check_flight_mode(drone)
            log_event(f"Takeoff initiated in flight mode: {currentMode}")
            
            if distMeters:
                log_command("TAKEOFF", distVal, distType)
                await asyncio.wait_for(drone.action.set_takeoff_altitude(distMeters), timeout=ACTION_TIMEOUT)
            else:
                log_command("TAKEOFF")
                await asyncio.wait_for(drone.action.set_takeoff_altitude(1.0), timeout=ACTION_TIMEOUT)
            
            await asyncio.wait_for(drone.action.takeoff(), timeout=ACTION_TIMEOUT)
        
        # Execute movement commands
        elif cmdType in ("FORWARD", "BACKWARD", "UP", "DOWN", "LEFT", "RIGHT"):
            # Check if drone is armed and in the air before movement
            isArmed = await check_armed_state(drone)
            if not isArmed:
                log_error(f"Cannot execute {cmdType}: Drone is not armed.")
                return
            
            isInAir = await check_in_air(drone)
            if not isInAir:
                log_error(f"Cannot execute {cmdType}: Drone is not in the air. Please take off first.")
                return
            
            if distMeters:
                log_command(f"MOVE {cmdType}", distVal, distType)
                await asyncio.wait_for(execute_movement_command(cmdType, distMeters), timeout=MOVEMENT_TIMEOUT)
            else:
                log_command(f"MOVE {cmdType}", 10, "cm")
                await asyncio.wait_for(execute_movement_command(cmdType, 0.1), timeout=MOVEMENT_TIMEOUT)
        
        # Execute rotation commands
        elif cmdType in ("RO_LEFT", "RO_RIGHT"):
            # Check if drone is armed and in the air before rotation
            isArmed = await check_armed_state(drone)
            if not isArmed:
                log_error(f"Cannot execute {cmdType}: Drone is not armed.")
                return
            
            isInAir = await check_in_air(drone)
            if not isInAir:
                log_error(f"Cannot execute {cmdType}: Drone is not in the air. Please take off first.")
                return
            
            log_command(cmdType, distVal or 90, "degrees")
            await asyncio.wait_for(execute_rotation_command(cmdType, distMeters or 90), timeout=MOVEMENT_TIMEOUT)
        
    # Timeout error handling
    except asyncio.TimeoutError:
        log_error(f"{cmdType} command timed out")
    # Action error handling
    except ActionError as actionErr:
        log_error(f"Action error during {cmdType}", actionErr)
    # Offboard error handling
    except OffboardError as offboardErr:
        log_error(f"Offboard error during {cmdType}", offboardErr)
    # General exception handling
    except Exception as e:
        log_error(f"Unexpected error during {cmdType}", e)

async def execute_movement_command(direction, distance):
    """
    Performs a movement command in the specified direction by the specified distance.
    Args:
        direction: Direction to move
        distance: Distance to move (in meters)
    """
    # Get current drone state, offboard state, and NED position
    drone = get_instance()
    offboard = get_offboard_state()
    nedPos = get_ned_position()

    # Initialize NED position if offboard is not active
    if not offboard:
        await _initialize_offboard(drone)
        offboard = get_offboard_state()
        nedPos = get_ned_position()

    # Get direction vector
    dirOffset = BASE_DIRECTION_OFFSETS.get(direction)
    if not dirOffset:
        log_error(f"Unknown direction '{direction}'")
        return
    
    # Get current yaw to adjust movement direction
    yaw = 0.0
    try:
        async for attitude in drone.telemetry.attitude_euler():
            yaw = attitude.yaw_deg
            break
    # General exception handling. If error occurs, default to 0.0 degrees.
    except Exception as e:
        log_error("Error getting current yaw", e)
        yaw = 0.0

    # Convert yaw from degrees to radians for trigonometric calculations
    yawRad = math.radians(yaw)
    cosYaw = math.cos(yawRad)
    sinYaw = math.sin(yawRad)

    # Rotate movement vector by current yaw
    vectorX = dirOffset[0] * distance
    vectorY = dirOffset[1] * distance
    vectorZ = dirOffset[2] * distance

    # Transform to new direction based on yaw
    moveX = vectorX * cosYaw - vectorY * sinYaw
    moveY = vectorX * sinYaw + vectorY * cosYaw
    moveZ = vectorZ
    
    # Calculate new yaw
    newNorth = nedPos[0] + moveX
    newEast = nedPos[1] + moveY
    newDown = nedPos[2] + moveZ
    newPos = [newNorth, newEast, newDown]

    # Trigger movement command and update stored NED position
    await asyncio.wait_for(
        drone.offboard.set_position_ned(PositionNedYaw(
            newPos[0], newPos[1], newPos[2], yaw)),
        timeout=OFFBOARD_TIMEOUT
    )
    set_ned_position(newPos)
    
    # Checks for interruption during sleep. 10 iterations of 0.1s = 1s total
    for i in range(10):
        if get_stop_requested():
            log_event("Movement command interrupted!")
            return
        await asyncio.sleep(0.1)

async def execute_rotation_command(direction, angle):
    """
    Performs a rotation command in the specified direction by the specified angle.
    Args:
        direction: Rotation direction
        angle: Angle to rotate (in degrees)
    """
    # Get current drone state, offboard state, and NED position
    drone = get_instance()
    offboard = get_offboard_state()
    nedPos = get_ned_position()

    # Initialize NED position if offboard is not active
    if not offboard:
        await _initialize_offboard(drone)
        offboard = get_offboard_state()
        nedPos = get_ned_position()
    
    # Calculate new yaw
    yaw = 0.0
    try:
        async for attitude in drone.telemetry.attitude_euler():
            yaw = attitude.yaw_deg
            break
    
    # General exception handling.
    except Exception as e:
        log_error("Error getting current yaw", e)
    
    yaw = yaw + angle if direction == "RO_RIGHT" else yaw - angle

    # Trigger rotation command
    await asyncio.wait_for(
        drone.offboard.set_position_ned(PositionNedYaw(
            nedPos[0], nedPos[1], nedPos[2], yaw)),
        timeout=OFFBOARD_TIMEOUT
    )

    # Check for interruption during sleep. 10 iterations of 0.1s = 1s total.
    for i in range(10):
        if get_stop_requested():
            log_event("Rotation command interrupted!")
            return
        await asyncio.sleep(0.1)

async def _initialize_offboard(drone):
    """
    Initialize offboard mode for the drone.
    Args:
        drone: The drone instance
    """
    # Verify drone is armed before starting offboard mode
    isArmed = await check_armed_state(drone)
    if not isArmed:
        log_error("Cannot start offboard mode: Drone is not armed.")
        return
    
    # Verify drone is in the air before starting offboard mode
    isInAir = await check_in_air(drone)
    if not isInAir:
        log_error("Cannot start offboard mode: Drone is not in the air.")
        return
    
    # Log current flight mode before switching to offboard
    currentMode = await check_flight_mode(drone)
    log_event(f"Switching from {currentMode} to OFFBOARD mode")
    
    # Get current yaw to maintain heading
    yaw = 0.0
    try:
        async for attitude in drone.telemetry.attitude_euler():
            yaw = attitude.yaw_deg
            break
    except Exception as e:
        log_error("Error getting current yaw for offboard init", e)
        yaw = 0.0
    
    # Attempt to get current NED position from telemetry
    try:
        async for position_velocity in drone.telemetry.position_velocity_ned():
            nedPos = [
                position_velocity.position.north_m,
                position_velocity.position.east_m,
                position_velocity.position.down_m
            ]
            break
    
    # Handles errors. If error occurs, default to origin.
    except Exception as e:
        log_error("Could not get NED position. Setting to origin", e)
        nedPos = [0.0, 0.0, 0.0]
    
    set_ned_position(nedPos)

    # Synchronize drone to current NED position and yaw, then start offboard mode
    await asyncio.wait_for(
        drone.offboard.set_position_ned(PositionNedYaw(
            nedPos[0], nedPos[1], nedPos[2], yaw)),
        timeout=OFFBOARD_TIMEOUT
    )
    await asyncio.wait_for(drone.offboard.start(), timeout=OFFBOARD_TIMEOUT)
    set_offboard_state(True)
    await asyncio.sleep(0.8)