# Intelligent Drone - Voice Command System

Voice-controlled drone system using MAVSDK and Vosk speech recognition for autonomous flight control via natural language commands.

## Requirements

- Python 3.7 or higher (tested on Python 3.12)
- Pixhawk 6C flight controller (or compatible MAVSDK-supported hardware)
- Bluetooth headset with microphone
- Jetson Nano or compatible Linux system for deployment

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Vosk Speech Model

1. Visit https://alphacephei.com/vosk/models
2. Download **"vosk-model-small-en-us-0.15"**
3. Unzip the model
4. Place the extracted folder in your project directory

### 3. Configure System

Edit the following parameters in `config.py`:

```python
# Required Configuration
MODEL_LOCATION = r"/absolute/path/to/vosk-model-small-en-us-0.15"
HEADSET_MAC = "XX_XX_XX_XX_XX_XX"  # Your Bluetooth headset MAC address
SIM_MODE = True  # Set to False for real drone operation

# Connection Settings (for real drone)
DRONE_CONNECTION_PATH = "serial:///dev/ttyUSB0:115200"  # Adjust as needed
```

### 4. Setup Passwordless Sudo (for Jetson Nano deployment)

To enable the shutdown command to power off the Jetson:

```bash
sudo visudo
# Add this line (replace 'username' with your actual username):
username ALL=(ALL) NOPASSWD: /sbin/shutdown
```

## Usage

### Running the System

```bash
python3 main.py
```

The system will:
1. Initialize the speech recognition model
2. Connect to the Bluetooth headset
3. Establish connection to the drone (if SIM_MODE = False)
4. Begin listening for voice commands

### Available Commands

#### Basic Flight Commands
- `"arm drone"` - Arm the motors
- `"takeoff"` - Take off to default altitude (1 meter)
- `"takeoff 2 meters"` - Take off to specified altitude
- `"land"` - Land at current position
- `"disarm"` - Disarm the motors

#### Movement Commands (default: 10 cm)
- `"forward"` / `"forward 5 meters"` - Move forward
- `"backward"` / `"backward 3 feet"` - Move backward
- `"left"` / `"left 50 centimeters"` - Move left
- `"right"` / `"right 2 yards"` - Move right
- `"up"` / `"up 1 meter"` - Move up
- `"down"` / `"down 6 inches"` - Move down

#### Rotation Commands (default: 90 degrees)
- `"turn left"` / `"turn left 45 degrees"` - Rotate left
- `"turn right"` / `"turn right 180 degrees"` - Rotate right

#### Control Commands
- `"stop"` - Hold current position (interrupts ongoing commands)
- `"return"` / `"come home"` - Return to launch position
- `"shutdown"` - Clean shutdown of system and Jetson Nano

#### Command Chaining
Commands can be chained using separators:
- `"arm drone, then takeoff, then forward 5 meters"`
- `"turn left 90 degrees and move forward 3 meters"`
- `"up 2 meters, then turn right, then land"`

### Viewing Logs

Logs are automatically created in the `logs/` directory with timestamps:

```bash
cd logs
ls -lt  # List logs by time
cat "LOG 17_11 22_10.txt"  # View specific log
```

Log entries include millisecond-precision timestamps for analyzing command execution times.

## Testing with Simulator

Before flying with real hardware, test with PX4 SITL simulator:

```bash
# On Ubuntu/Jetson Nano
cd ~/PX4-Autopilot
make px4_sitl_default none_iris

# In another terminal, run your code
cd ~/path/to/Senior\ Design
python3 main.py
```

Set `SIM_MODE = False` and `DRONE_CONNECTION_PATH = "udp://:14540"` in config.py for simulator testing.

## Project Structure

```
Senior Design/
├── main.py                 # Main entry point
├── config.py              # Configuration settings
├── logger.py              # Asynchronous logging system
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── drone/
│   ├── command.py        # Command execution
│   ├── connect.py        # Drone connection management
│   └── state.py          # Drone state tracking
├── voice/
│   ├── microphone.py     # Bluetooth headset management
│   ├── parser.py         # Speech-to-command parsing
│   └── recognizer.py     # Vosk integration
├── logs/                  # Flight logs (auto-generated)
└── vosk-model-small-en-us-0.15/  # Speech model (download separately)
```

## Safety Notes

- Always test in SIM_MODE before real flights
- Ensure adequate space for autonomous operation
- Keep manual override (RC transmitter) ready
- Monitor battery levels
- Use STOP command for immediate position hold
- Test all commands in controlled environment first

## Troubleshooting

**"Headset mic not ready"**: Ensure Bluetooth headset is connected and in HSP/HFP profile (not A2DP).

**"Connection timeout"**: Check USB cable connection to Pixhawk and verify DRONE_CONNECTION_PATH.

**Audio issues on Jetson**: Install required audio packages:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

**"Permission denied" for shutdown**: Configure passwordless sudo (see step 4 above).