'''
config.py
Configuration settings for the voice command recognition system.
Please edit the marked parameters before running main.py.
DO NOT EDIT ANY OTHER PART OF THIS FILE.
'''
import re

# Editable parameters:
SIM_MODE = True     # Set to True for simulation mode, False for real drone

MODEL_LOCATION = r"C:\Senior Design\vosk-model-small-en-us-0.15"  # Absolute path to vosk model

HEADSET_MAC = "40_58_99_5B_08_79"  # Headset MAC address fragment

# Connection and timeout settings (in seconds)
CONNECTION_TIMEOUT = 45.0       # Initial drone connection
ACTION_TIMEOUT = 15.0           # Basic actions (arm, disarm, takeoff, land)
MOVEMENT_TIMEOUT = 20.0         # Movement and rotation commands
OFFBOARD_TIMEOUT = 8.0          # Offboard mode start/stop operations

# Connection retry settings
MAX_CONNECTION_RETRIES = 3      # Maximum number of connection retry attempts
INITIAL_RETRY_DELAY = 3.0       # Initial delay between retries (seconds)
RETRY_BACKOFF_MULTIPLIER = 2.0  # Multiplier for exponential backoff delay

# Audio processing settings
AUDIO_FORMAT = "paInt16"        # Audio format (review PyAudio documentation for other options)
AUDIO_CHANNELS = 1              # Number of audio channels (1 for mono, 2 for stereo)
AUDIO_RATE = 16000              # Audio sample rate (Hz)
AUDIO_BUFFER_SIZE = 4096        # Number of audio frames per buffer
PROCESS_INTERVAL = 0.1          # Minimum time between audio processing cycles (seconds)

# Drone connection path (Update else clause as needed)
DRONE_CONNECTION_PATH = "udp://:14540" if SIM_MODE else "serial:///dev/ttyUSB0:115200"

"""DO NOT EDIT BELOW THIS LINE"""
# Pre-compiled regex patterns
DIGIT_PATTERN = re.compile(r'\d+')                      # Digits
                                                        # Command separators
SEPARATOR_PATTERN = re.compile(r'(?:,\s*(?:then\s+|and\s+|next\s+)?|,?\s+(?:then|and|next|after\s+that|followed\s+by|afterward)\s+)')
UNIT_PATTERNS = {                                       # Measurement units
    'inches': re.compile(r'\b(?:inch|inches)\b'),
    'feet': re.compile(r'\b(?:feet|foot)\b'), 
    'yards': re.compile(r'\b(?:yard|yards)\b'),
    'degrees': re.compile(r'\b(?:degree|degrees)\b')
}

# List of valid commands and trigger phrases. Dictionary condensed for faster lookup.
COMMAND_DICT = {
    "STOP":     ["stop", "stop drone"],
    "RETURN":   ["return", "come home", "home"],
    "LAND":     ["land", "land drone"],
    "FORWARD":  ["forward"],
    "BACKWARD": ["backward"],
    "UP":       ["up"],
    "DOWN":     ["down"],
    "LEFT":     ["left"],
    "RIGHT":    ["right"],
    "RO_LEFT":  ["turn left", "rotate left"],
    "RO_RIGHT": ["turn right", "rotate right"],
    "TAKEOFF":  ["takeoff", "take off"],
    "DISARM":   ["disarm", "disarm drone"],
    "ARM":      ["arm", "arm drone"],
    "SHUTDOWN": ["shutdown", "power off"],
}
COMMAND_LOOKUP = {trigger: cmdType for cmdType, triggers in COMMAND_DICT.items() for trigger in triggers}

# Dictionary of integer variables for command parameters
NUM_DICT = {
    'one': 1, 'two': 2, 'to': 2, 'three': 3, 'four': 4, 'for': 4, 'five': 5, 'six': 6, 'seven': 7,
    'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
    'hundred': 100
}

# NED (North East Down) movement direction unit vectors
BASE_DIRECTION_OFFSETS = {
    "FORWARD": (1.0, 0.0, 0.0),     # +X relative to nose
    "BACKWARD": (-1.0, 0.0, 0.0),   # -X (negative North)
    "LEFT": (0.0, -1.0, 0.0),       # -Y (negative East)
    "RIGHT": (0.0, 1.0, 0.0),       # +Y (positive East)
    "UP": (0.0, 0.0, -1.0),         # -Z (up in NED)
    "DOWN": (0.0, 0.0, 1.0)         # +Z (down in NED)
}

# Pre-computed conversion factors
CONVERSION_FACTORS = {
    'inches': 0.0254,
    'feet': 0.3048,
    'yards': 0.9144,
    'meters': 1.0,
    'degrees': 1.0
}

# Value conversion cache assists in performance optimization
_conversionCache = {}

# Command interrupt control
_stopRequested = False
_commandExecuting = False