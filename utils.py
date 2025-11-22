"""
utils.py
Miscellaneous utility functions.
"""
import config

def convert_to_meters(value, unit):
    """
    Convert a measurement to meters based on the provided unit.
    Args:
        value: Numeric value to convert
        unit: Unit type
    """
    # Returns None if either value or unit is invalid
    if not value or not unit:
        return None
    
    # Check cache first
    cacheKey = (value, unit)
    cachedResult = config._conversionCache.get(cacheKey)
    if cachedResult is not None:
        return cachedResult

    # Convert unit to meters (degrees treated as meters)
    factor = config.CONVERSION_FACTORS.get(unit)
    if factor is None:
        return None
    
    result = value * factor

    # Cache result if space is available
    if len(config._conversionCache) < 50:
        config._conversionCache[cacheKey] = result
    
    return result

def get_stop_requested():
    """Get the stop request flag."""
    return config._stopRequested

def set_stop_requested(value):
    """Set the stop request flag."""
    config._stopRequested = value

def get_command_executing():
    """Get the command executing flag."""
    return config._commandExecuting

def set_command_executing(value):
    """Set the command executing flag."""
    config._commandExecuting = value