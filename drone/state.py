'''
state.py
Manages and tracks the current state of the drone.
'''
from mavsdk import System

# Global drone state variables
droneInstance = None    # MAVLink drone instance
nedPosition = None      # NED (North East Down) position of the drone
offboard = False        # Offboard mode state of the drone

def get_instance():
    """Get the current drone instance. If it doesn't exist, create one."""
    global droneInstance
    if droneInstance is None:
        droneInstance = System()
    return droneInstance

def reset_instance():
    """Reset all drone state variables."""
    global droneInstance, nedPosition, offboard
    droneInstance = None
    nedPosition = None
    offboard = False

def get_ned_position():
    """
    Get the NED position of the drone.
    """
    return nedPosition

def set_ned_position(position):
    """
    Set the NED position of the drone.
    Args:
        position: New NED coordinates
    """
    global nedPosition
    nedPosition = position

def get_offboard_state():
    """
    Get the current offboard state of the drone.
    """
    return offboard

def set_offboard_state(status):
    """
    Set the offboard state of the drone.
    Args:
        status: Offboard mode - True if active, False otherwise
    """
    global offboard
    offboard = status