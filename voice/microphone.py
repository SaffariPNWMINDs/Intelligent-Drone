"""
microphone.py
Handles Bluetooth headset microphone profile configuration for PulseAudio.
"""
import subprocess
import time
from config import HEADSET_MAC

DESIRED_PROFILE = "headset_head_unit"

def run_cmd(cmd):
    """
    Execute a shell command and return the result.
    Args:
        cmd: Command string to execute
    """
    return subprocess.run(cmd, shell=True, check=False,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True)

def get_bt_card_name():
    """Gets the PulseAudio card name for the Bluetooth headset."""
    result = run_cmd("pactl list cards short")
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "bluez_card." in parts[1]:
            if HEADSET_MAC in parts[1]:
                return parts[1]
    
    return None

def get_card_active_profile(cardName):
    """
    Gets the active profile string for the given card.
    Args:
        cardName: Name of the PulseAudio card
    """
    result = run_cmd("pactl list cards")
    block = []
    inBlock = False
    for line in result.stdout.splitlines():
        if f"Name: {cardName}" in line:
            inBlock = True
            block = [line]
            continue
        
        if inBlock:
            if line.startswith("Name: ") and cardName not in line:
                break
            block.append(line)

    for line in block:
        line = line.strip()
        if line.startswith("Active Profile:"):
            return line.split("Active Profile:", 1)[1].strip()
    
    return None

def get_headset_source_name():
    """Get the source name for the headset mic."""
    result = run_cmd("pactl list sources short")
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "bluez_source." in parts[1]:
            if HEADSET_MAC in parts[1] and DESIRED_PROFILE in parts[1]:
                return parts[1]
    
    return None

def set_card_profile(cardName, profile):
    """
    Set the PulseAudio card to the specified profile.
    Args:
        cardName: Name of the PulseAudio card
        profile: Profile string
    """
    cmd = f"pactl set-card-profile {cardName} {profile}"
    result = run_cmd(cmd)
    return result.returncode == 0

def reconnect_headset():
    """Disconnects and reconnects the Bluetooth headset to ensure MAC address appears."""
    mac = HEADSET_MAC.replace("_", ":")
    run_cmd(f"bluetoothctl disconnect {mac}")
    time.sleep(1.0)
    run_cmd(f"bluetoothctl connect {mac}")
    time.sleep(1.0)

def ensure_headset_profile():
    """Ensures the Bluetooth headset card is in headset_head_unit profile."""
    # Check PulseAudio server is up
    info = run_cmd("pactl info")
    if info.returncode != 0:
        return False, None, "PulseAudio not running or unreachable."

    # Get Bluetooth card name
    card = get_bt_card_name()
    if not card:
        # If the card is not found, try reconnecting the headset once
        reconnect_headset()
        for _ in range(3):
            card = get_bt_card_name()
            if card:
                break
            time.sleep(0.25)
    
    if not card:
        return False, None, "Bluetooth headset card not found (is it connected/trusted?)."

    # Get active profile
    active = get_card_active_profile(card)
    if active != DESIRED_PROFILE:
        if not set_card_profile(card, DESIRED_PROFILE):
            return False, None, f"Failed to set profile {DESIRED_PROFILE} on {card}."
    
    # After changing profile, check source to ensure it's available
    time.sleep(0.5)
    src = get_headset_source_name()
    if not src:
        return False, None, "Headset mic source not found even after switching profile."

    return True, src, f"Using mic source: {src}"