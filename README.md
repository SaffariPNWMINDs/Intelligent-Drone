# Intelligent Drone - Voice Command System

Voice-controlled drone system using MAVSDK and Vosk speech recognition for autonomous flight control via natural language commands.

## Requirements

- Python 3.7 or higher (tested on Python 3.12)
- Pixhawk 6C flight controller (or compatible MAVSDK-supported hardware)
- Bluetooth headset with microphone
- Jetson Nano or compatible Linux system for deployment
- RC transmitter (required for safety/failsafe)
- GPS module with 3D fix capability for outdoor flight

## System Architecture Overview

The project consists of four major subsystems running cooperatively on the Jetson Nano:

### 1. Audio Interface
- Captures microphone input from Bluetooth headset
- Streams audio frames (16kHz, mono) into Vosk for speech recognition
- Processes audio in 100ms intervals with configurable buffer size

### 2. Command Parsing Layer
- Converts raw recognized text into structured drone commands
- Extracts distances, angles, units, and command sequences
- Supports command chaining with separators ("then", "and", "next", etc.)
- Validates command syntax before execution

### 3. Drone Control Layer (MAVSDK)
- Connects to Pixhawk via UART (`/dev/ttyTHS1` at 57600 baud)
- Performs arming, takeoff, movement, rotation, landing operations
- Manages Offboard Mode for continuous position control
- Validates drone state (armed, in-air) before executing commands

### 4. State & Logging Subsystem
- Tracks real-time drone state (armed, airborne, GPS status)
- Writes millisecond-precision timestamped logs to `logs/` directory
- Provides async logging to prevent blocking main command loop

### System Flow
```
Voice → Bluetooth Mic → Vosk Recognition → Parser → Command Queue
                                                           ↓
                                              MAVSDK → Pixhawk → Drone Motion
                                                           ↓
                                                   State Tracking + Logging
```

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Jetson Serial Port Setup (One-Time Only)

**Note**: This section is only required for Jetson Nano with direct UART connection to Pixhawk. Skip if using USB connection or simulator.

The Jetson Nano uses `/dev/ttyTHS1` for UART communication with the Pixhawk's TELEM3 port. Complete these one-time setup steps so MAVSDK can reliably access the serial interface.

#### 1. Disable System Serial Console on ttyTHS1

By default, Jetson Linux may run a login console on the UART pins, blocking Pixhawk communication.

```bash
sudo systemctl stop serial-getty@ttyTHS1.service
sudo systemctl disable serial-getty@ttyTHS1.service
```

#### 2. Create udev rule for proper permissions

This step ensures `/dev/ttyTHS1` is readable and writable after every reboot.

```bash
sudo nano /etc/udev/rules.d/99-ttyths1.rules
```

Add the following line:
```
KERNEL=="ttyTHS1", MODE="0666"
```

Reload rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 3. Add your user to required groups

```bash
sudo usermod -a -G tty,dialout $USER
```

Log out and log back in (or reboot) to apply group membership.

#### 4. (Optional) Verify UART Configuration

```bash
sudo /opt/nvidia/jetson-io/jetson-io.py
```

Ensure `/dev/ttyTHS1` is enabled as a UART interface.

**After these steps**, the Jetson will automatically expose a usable serial port, allowing `python3 main.py` to connect without manual intervention.

### 3. Hardware Setup (Jetson ↔ Pixhawk Wiring)

Connect the Jetson Nano to Pixhawk 6C using **TELEM3** port:

| Pixhawk TELEM3 | Signal | Jetson Nano Pin | Notes                  |
|----------------|--------|-----------------|------------------------|
| Pin 2          | TX     | Pin 10 (RX)     | Cross TX→RX            |
| Pin 3          | RX     | Pin 8 (TX)      | Cross RX→TX            |
| Pin 6          | GND    | Any GND         | Common ground required |

**Important Wiring Notes:**
- **TX and RX must be crossed** (TX→RX, RX→TX)
- **Do NOT connect 5V** from Pixhawk to Jetson (both should be separately powered)
- Ensure solid connections - loose wiring is the #1 cause of connection failures
- Verify ground is shared between Jetson and Pixhawk

**Pin Reference:**
- Jetson Nano Pin 8 = GPIO14 (UART TX)
- Jetson Nano Pin 10 = GPIO15 (UART RX)

### 4. Pixhawk Configuration (One-Time Setup)

Configure the Pixhawk TELEM3 port for MAVLink communication. A complete parameter file is provided in the repository.

#### Using Mission Planner (Recommended):

1. Connect the Pixhawk to your computer via USB
2. Open Mission Planner and connect to the Pixhawk
3. Navigate to **Config/Tuning → Full Parameter List**
4. Click **Load from file** and select `Pixhawk_Param_List.param` from the project directory
5. Click **Write Params** to apply the configuration
6. **Reboot the Pixhawk** for changes to take effect

#### Using QGroundControl:

1. Connect the Pixhawk to your computer via USB
2. Open QGroundControl and wait for connection
3. Navigate to **Vehicle Setup → Parameters**
4. Click **Tools → Load from file** and select `Pixhawk_Param_List.param`
5. Apply the parameters and reboot the Pixhawk

#### Manual Configuration:

If you prefer to set parameters manually, refer to `Pixhawk_Param_List.param` for all required settings. Key parameters include SERIAL5 configuration for TELEM3 communication, failsafe settings, and arming requirements.

**Critical:** After changing parameters, **reboot the Pixhawk** for changes to take effect.

### 5. Download Vosk Speech Model

1. Visit https://alphacephei.com/vosk/models
2. Download **"vosk-model-small-en-us-0.15"**
3. Unzip the model
4. Place the extracted folder in your project directory

### 6. Find Bluetooth Headset MAC Address

On Linux/Jetson Nano:
```bash
bluetoothctl
devices         # Lists all paired devices with MAC addresses
# Look for your headset and copy the MAC address (e.g., 40:58:99:5B:08:79)
```

Replace colons with underscores for the config file: `40_58_99_5B_08_79`

### 7. Configure System

Edit the following parameters in `config.py`:

```python
# Required Configuration
MODEL_LOCATION = r"/absolute/path/to/vosk-model-small-en-us-0.15"
HEADSET_MAC = "40_58_99_5B_08_79"   # Your Bluetooth headset MAC address
SIM_MODE = True                     # Set to False for real drone operation

# Connection Settings (automatically selected based on SIM_MODE)
# For real drone (Jetson UART): serial:///dev/ttyTHS1:57600
# For real drone (USB): serial:///dev/ttyUSB0:115200
# For simulator: udp://:14540

# Optional: Noise Testing (for research purposes)
NOISE_TESTING = False   # Set to True to add noise to audio
SNR_DB = 20.0           # Signal-to-Noise Ratio in dB (lower = more noise)
```

## Flight Mode Requirements

For movement and rotation commands to work, the Pixhawk must be in a flight mode that supports position control.

### For ArduPilot:

**Supported Modes:**
- **GUIDED** (Recommended) - Allows full offboard control from MAVSDK
- **LOITER** - GPS-based position hold, accepts guided commands

**Behavior:**
- System automatically switches to Offboard mode for movement/rotation commands
- Keep RC transmitter powered on with sticks centered during voice control
- Set flight mode channel (typically CH7) to GUIDED or LOITER before starting

**Incompatible Modes (Do Not Use):**
- **STABILIZE** - Manual control only; position commands will not work
- **ALT_HOLD** - Manual horizontal control conflicts with voice commands
- **MANUAL** - Full manual control; all voice commands ignored
- **ACRO** - Rate control mode incompatible with position commands

### For PX4:

**Requirements:**
- System automatically enters Offboard mode when movement commands begin
- RC transmitter must remain active (required for failsafe)
- Set Position mode as the fallback flight mode

**Offboard Mode Behavior:**
- MAVSDK sends continuous position setpoints (required by PX4)
- If position commands stop for >500ms, Offboard mode exits
- System maintains offboard stream automatically during operations

### RC Transmitter Requirements

**Always keep RC transmitter powered on during flight:**
- Enables manual override if voice control fails
- Activates failsafe if Jetson/MAVSDK connection is lost
- Configure RC failsafe action to LAND or RTL

## Usage

### Startup Checklist (Real Drone)

Complete the pre-flight safety checklist (see Safety Notes section), then start the system:

**System Startup:**
```bash
cd ~/Senior\ Design/
python3 main.py
```

**Expected Output:**
```
Logger initialized: logs/LOG 11_12 14_23.txt
Using mic source: bluez_source.40_58_99_5B_08_79.headset_head_unit
Vosk model loaded.
Audio stream started. Now listening for commands:
Attempting to connect to drone (Attempt 1/3)...
Successfully connected to the drone. Verifying stability...
Connection stable.
```

**Flight Sequence:**
1. `"arm drone"` - Wait for confirmation
2. `"takeoff"` - Drone rises to 1 meter altitude
3. Fly using voice commands (forward, left, turn right, etc.)
4. `"land"` - Drone lands at current position
5. `"disarm"` - Motors stop
6. `"shutdown"` - Safe Jetson shutdown

**Emergency Procedures:**
- **Lost voice control:** Use RC transmitter to switch to STABILIZE/MANUAL and land manually
- **Unexpected behavior:** Say `"stop"` immediately or use RC override
- **System unresponsive:** Use RC transmitter to RTL or land manually

### Shutdown Procedure

The system provides multiple shutdown options:

**Voice Command Shutdown (Recommended):**
```
Say: "shutdown"
```
This command performs a complete system shutdown:
1. Stops accepting new commands
2. Disables offboard mode (if active)
3. Closes drone connection
4. Stops audio processing
5. Closes all log files
6. Powers off Jetson Nano

**Manual Shutdown (Ctrl+C):**
- Press `Ctrl+C` in terminal
- System performs cleanup (closes connections, stops audio, saves logs)
- Jetson remains powered on; manual shutdown required afterward

**Important:** Never power off Jetson abruptly. Always use proper shutdown to prevent log file corruption, ensure clean drone disconnection, and avoid SD card damage.

### Available Commands

#### Basic Flight Commands
- `"arm drone"` - Arm the motors
- `"takeoff"` - Take off to default altitude (**1 meter**)
- `"takeoff 2 meters"` - Take off to specified altitude
- `"land"` - Land at current position
- `"disarm"` - Disarm the motors

#### Movement Commands
Default distance: **10 cm** if no distance specified
- `"forward"` / `"forward 5 meters"` - Move forward
- `"backward"` / `"backward 3 feet"` - Move backward
- `"left"` / `"left 50 inches"` - Move left
- `"right"` / `"right 2 yards"` - Move right
- `"up"` / `"up 1 meter"` - Move up
- `"down"` / `"down 6 inches"` - Move down

#### Rotation Commands
Default angle: **90 degrees** if no angle specified
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

Supported separators: `then`, `and`, `next`, `after that`, `followed by`, `afterward`

### Supported Units

The system recognizes multiple units for distance and rotation:

**Distance Units:**
- Inches: `"forward 12 inches"`
- Feet: `"up 3 feet"`
- Yards: `"backward 2 yards"`
- Meters (default): `"left 5 meters"` or just `"left 5"`

**Rotation Units:**
- Degrees: `"turn left 45 degrees"` or `"turn left 45"`

**Number Recognition:**
- Digits: `"forward 5 meters"`
- Words: `"forward five meters"`
- Combined: `"forward twenty three feet"`

### Viewing Logs

Logs are automatically created in the `logs/` directory with timestamps:

```bash
cd logs
ls -lt                          # List logs by time (newest first)
cat "LOG 11_12 14_23.txt"       # View specific log
tail -f "LOG 11_12 14_23.txt"   # Follow log in real-time
```

#### Log Format

Each log entry includes millisecond-precision timestamps for detailed analysis:

**Example Log Snippet:**
```
[14:23:15.342] === Log started at 2025-12-11 14:23:15 ===
[14:23:15.845] Logger initialized: logs/LOG 11_12 14_23.txt
[14:23:16.123] Using mic source: bluez_source.40_58_99_5B_08_79.headset_head_unit
[14:23:18.567] Vosk model loaded.
[14:23:18.891] Audio stream started. Now listening for commands:
[14:23:19.234] Attempting to connect to drone (Attempt 1/3)...
[14:23:24.567] Drone connection confirmed.
[14:23:25.890] Successfully connected to the drone. Verifying stability...
[14:23:27.123] Connection stable.
[14:23:35.456] Recognized: 'arm drone'
[14:23:35.458] Command: ARM
[14:23:36.234] Recognized: 'takeoff'
[14:23:36.236] Takeoff initiated in flight mode: FlightMode.GUIDED
[14:23:36.237] Command: TAKEOFF
[14:23:42.567] Recognized: 'forward five meters'
[14:23:42.569] Command: MOVE FORWARD 5 meters
[14:23:43.890] Switching from FlightMode.GUIDED to OFFBOARD mode
[14:23:49.123] Recognized: 'turn right ninety degrees'
[14:23:49.125] Command: RO_RIGHT 90 degrees
[14:23:55.456] Recognized: 'land'
[14:23:55.458] Command: LAND
[14:24:02.789] Recognized: 'disarm'
[14:24:02.791] Command: DISARM
```

**Timestamp Precision:**
- Format: `[HH:MM:SS.mmm]` (hours:minutes:seconds.milliseconds)
- Useful for debugging command latency and identifying delays between voice input and execution
- Each command entry shows: recognized text → command type → values/units

## Testing with Simulator

Before flying with real hardware, test with PX4 SITL simulator:

1. Set `SIM_MODE = True` in `config.py` (connection path will automatically switch to UDP)

2. Start the PX4 SITL simulator:
```bash
# On Ubuntu/Jetson Nano
cd ~/PX4-Autopilot
make px4_sitl_default none_iris
```

3. Run the voice control system:
```bash
cd ~/path/to/Senior\ Design
python3 main.py
```

The system automatically uses `udp://:14540` when `SIM_MODE = True`.

## Project Structure

```
Senior Design/
├── main.py                         # Main entry point
├── config.py                       # Configuration settings
├── logger.py                       # Asynchronous logging system
├── utils.py                        # Utility functions
├── requirements.txt                # Python dependencies
├── drone/
│   ├── command.py                  # Command execution
│   ├── connect.py                  # Drone connection management
│   └── state.py                    # Drone state tracking
├── voice/
│   ├── microphone.py               # Bluetooth headset management
│   ├── parser.py                   # Speech-to-command parsing
│   └── recognizer.py               # Vosk integration
├── logs/                           # Flight logs (auto-generated)
└── vosk-model-small-en-us-0.15/    # Speech model (download separately)
```

## Safety Notes

### Critical Safety Requirements

**RC Transmitter (Required):**
- Must remain powered on during all flights
- Provides manual override if voice control fails
- Configure RC failsafe action: LAND or RTL (recommended)
- Test RC override before voice-controlled flight
- Keep transmitter within range at all times

**GPS Requirements (Outdoor Flight):**
- Require 3D GPS fix with 6+ satellites before arming
- GPS arming requirements are configured in the provided parameter file
- For indoor flight: GPS not required but use extreme caution
- Always monitor GPS status before takeoff

**Battery Management:**
- Always use fully charged batteries before flight
- Monitor voltage during flight via telemetry
- Low battery failsafe thresholds are configured in the provided parameter file
- Verify battery parameters match your specific battery configuration (3S/4S/6S)
- Land immediately when battery warning activates

**Failsafe Configuration:**
- **GCS Failsafe:** Activates if MAVSDK connection is lost
  - Configured in the provided parameter file with appropriate timeouts
  - Triggers if Jetson crashes or UART disconnects
  - Review and adjust failsafe actions in Mission Planner if needed
- **RC Failsafe:** Backup protection if voice control and GCS both fail
- UART disconnection triggers GCS failsafe; drone executes configured action

### Pre-Flight Safety Checklist

**Verify before every flight:**
1. RC transmitter powered on and properly configured
2. GPS lock acquired (outdoor) or flight area cleared (indoor)
3. Battery fully charged with correct voltage
4. Propellers securely attached and undamaged
5. Flight area clear of people and obstacles
6. Bluetooth headset connected with working microphone
7. Jetson Nano powered and connected to drone
8. Failsafe actions configured and tested

### Operational Safety

- Always test in simulation mode first (`SIM_MODE = True`)
- System validates armed and in-air state before executing flight commands
- Maintain minimum 10m clearance around flight area
- Monitor battery levels continuously during flight
- Use `"stop"` command to immediately hold position and interrupt commands
- Default movement distance is 10 cm (adjustable via voice)
- Test all commands in controlled environment before outdoor use
- System prevents disarm while drone is airborne
- Offboard mode activates automatically for movement/rotation commands

### What Happens If Something Goes Wrong?

**Jetson Nano crashes or loses power:**
- GCS failsafe triggers within 5 seconds
- Drone executes configured failsafe action (LAND/RTL)
- RC transmitter remains available for manual control

**UART cable disconnects:**
- Immediate loss of MAVSDK communication
- GCS failsafe triggers
- Use RC transmitter to regain control

**Voice recognition failure:**
- Commands not recognized or mis-recognized
- Check logs for actual recognized text vs. expected
- Use `"stop"` command if drone behaves unexpectedly
- RC override always available

## Known Failure Modes

Understanding potential failure scenarios helps you respond appropriately:

### 1. Bluetooth/Audio Failures

**Headset disconnects during flight:**
- **Impact:** Voice commands stop working
- **Response:** Use RC transmitter immediately
- **Prevention:** Ensure headset is fully charged; test connection before flight
- **System behavior:** Drone continues last command or holds position

**Jetson Bluetooth stack hangs:**
- **Impact:** Audio processing stops; system appears unresponsive to voice
- **Response:** Use RC transmitter; SSH to Jetson to restart `pulseaudio` or reboot
- **Prevention:** Reboot Jetson before important flights
- **Indicator:** No recognized text appears in logs despite speaking

### 2. Communication/Connection Failures

**MAVSDK connection timeout or loss:**
- **Impact:** Commands fail; GCS failsafe triggers
- **Response:** Drone executes failsafe action (LAND or RTL)
- **Prevention:** Verify UART wiring; check `/dev/ttyTHS1` permissions before flight
- **Recovery:** Land manually with RC; check logs and wiring

**Pixhawk Offboard failsafe triggers:**
- **Impact:** Offboard mode exits; drone switches to failsafe mode
- **Cause:** MAVSDK stopped sending position setpoints (system crash or lag)
- **Response:** RC transmitter takes over; land manually
- **Prevention:** Ensure Jetson isn't overloaded (check CPU usage)

**UART data corruption:**
- **Impact:** MAVLink parsing errors; erratic behavior
- **Cause:** Poor wiring, electromagnetic interference, loose connections
- **Response:** Use RC override; land immediately
- **Prevention:** Use shielded cables; ensure solid connections; route away from motor wires

### 3. Recognition/Command Failures

**Vosk mis-recognition causes wrong command:**
- **Impact:** Drone executes unintended movement
- **Example:** "forward" recognized as "up forward"
- **Response:** Immediately say `"stop"` or use RC override
- **Prevention:** Speak clearly; check logs after each command to verify recognition
- **Mitigation:** System validates armed/in-air state before dangerous commands

**Command execution delayed:**
- **Impact:** Commands execute seconds after speaking
- **Cause:** CPU overload; Bluetooth audio buffering; network lag (simulation)
- **Response:** Wait for current command to complete; use `"stop"` if needed
- **Prevention:** Close unnecessary processes on Jetson; reduce `PROCESS_INTERVAL` if needed

### 4. State Management Failures

**Offboard mode streaming interrupted:**
- **Impact:** PX4 exits Offboard mode; position commands fail
- **Cause:** MAVSDK offboard loop stopped due to exception or system lag
- **Response:** Drone returns to previous flight mode or failsafe
- **Prevention:** Monitor logs for errors; ensure system isn't overloaded

**GPS lock lost during flight (outdoor):**
- **Impact:** Position control degraded or lost
- **Response:** Drone may switch to ALT_HOLD or LAND (depending on failsafe config)
- **Mitigation:** Fly in open areas with clear sky view; avoid urban canyons

### 5. System Resource Exhaustion

**Jetson CPU overload:**
- **Impact:** Delayed command processing; potential MAVSDK timeout
- **Cause:** Too many processes; Vosk model loading issues
- **Response:** System may become unresponsive to voice; use RC
- **Prevention:** Close unnecessary applications; monitor CPU with `htop`

**SD card full (logs):**
- **Impact:** Log writes fail; system may crash
- **Prevention:** Regularly clean `logs/` directory; monitor disk space
- **Check:** `df -h` before flight

### Emergency Response Summary

| Failure Type           | Immediate Action                       | Recovery                        |
|------------------------|----------------------------------------|---------------------------------|
| Voice control lost     | Switch to RC manual control            | Land safely, restart system     |
| UART disconnected      | RC override                            | Check wiring, reconnect         |
| GCS failsafe triggered | Allow configured action or RC override | Verify Jetson/MAVSDK status     |
| Offboard mode exit     | RC control active                      | Land manually, check logs       |
| GPS lost               | Drone switches to ALT_HOLD/LAND        | RC control if needed            |
| Unexpected motion      | Say `"stop"` or RC override            | Review logs for mis-recognition |

**Golden Rule:** When in doubt, use RC transmitter. It always works.

## Performance Characteristics

**Audio Processing:**
- Minimum processing interval: 100ms (`PROCESS_INTERVAL`)
- Audio buffer size: 2048 frames
- Recognition works offline (no internet required)
- Concurrent audio processing allows interrupt commands during flight

**Timeouts:**
- Drone connection: 45 seconds
- Basic actions (arm/disarm/takeoff/land): 15 seconds
- Movement and rotation: 20 seconds
- Offboard mode operations: 8 seconds

**Connection Reliability:**
- Automatic retry: 3 attempts with exponential backoff
- Connection verification before accepting any commands
- Graceful cleanup on shutdown

## Troubleshooting

### Serial Connection Issues (Jetson Nano)

If the system hangs on `"Waiting to discover system..."` or reports a serial port error:

#### 1. Check what process is using the UART

Sometimes a previous MAVSDK instance or leftover process may be holding the port.

```bash
sudo fuser -v /dev/ttyTHS1
```

If a PID is listed, terminate it:
```bash
sudo kill -9 <PID>
```

#### 2. Check serial permissions

If the udev rule wasn't applied, you can temporarily fix the permissions:

```bash
sudo chmod 666 /dev/ttyTHS1
```

If this resolves the issue, verify the udev rule exists:
```bash
cat /etc/udev/rules.d/99-ttyths1.rules
```

#### 3. Confirm serial console is disabled

```bash
systemctl status serial-getty@ttyTHS1.service
```

If active, disable it:
```bash
sudo systemctl stop serial-getty@ttyTHS1.service
sudo systemctl disable serial-getty@ttyTHS1.service
```

#### 4. Test UART manually

To verify Pixhawk is sending data:

```bash
sudo stty -F /dev/ttyTHS1 57600 raw -echo
sudo cat /dev/ttyTHS1 | hexdump -C
```

- **Continuous hex bytes** → UART is receiving MAVLink
- **No output** at common baudrates (57600/115200/921600) → Check wiring and Pixhawk settings

#### 5. Verify wiring (most common issue)

Correct wiring for **TELEM3 ↔ Jetson Nano UART**:

| Jetson Pin | Pixhawk TELEM3 Pin | Function |
|------------|--------------------|----------|
| Pin 8      | Pin 3              | TX → RX  |
| Pin 10     | Pin 2              | RX → TX  |
| GND        | Pin 6              | Ground   |

**Loose connections or TX–TX wiring will prevent MAVSDK from detecting the drone.**

#### 6. Verify Pixhawk parameters

Ensure you have loaded the `Pixhawk_Param_List.param` file as described in the Installation section. The parameter file contains all required SERIAL5/TELEM3 configuration for communication. You can verify parameters in Mission Planner under Config/Tuning → Full Parameter List.

---

### General Troubleshooting

**"Headset mic not ready"**: Ensure Bluetooth headset is connected and in HSP/HFP profile (not A2DP). System will attempt automatic reconnection.

**"Connection timeout"**: Verify `SIM_MODE` setting matches your setup. For real drone, check serial connection (see above). System retries 3 times with exponential backoff.

**"Cannot execute command: Drone is not armed"**: Arm the drone first with `"arm drone"` command.

**"Cannot execute command: Drone is not in the air"**: Movement and rotation require the drone to be airborne. Use `"takeoff"` first.

**Audio issues on Jetson**: Install required packages:
```bash
sudo apt-get install portaudio19-dev python3-pyaudio pulseaudio-utils
```

**High recognition error rate**: Check `NOISE_TESTING` is set to `False` in `config.py`. Ensure headset microphone is close to mouth.

**Commands not recognized**: Speak clearly and use exact command phrases. Check logs for recognized text vs expected commands.

## Known Limitations

- **Voice recognition accuracy**: Dependent on microphone quality, background noise, and speech clarity
- **Offline only**: No cloud-based recognition (intentional for security/latency)
- **Single user**: System processes one command chain at a time
- **English only**: Current model supports US English only
- **NED coordinate system**: Movement commands use drone's local frame (Forward = nose direction)
- **No obstacle avoidance**: System does not detect or avoid obstacles autonomously
- **GPS dependency**: Real flight requires GPS lock (3D fix) for outdoor operation

## Advanced Configuration

### Adjusting Timeouts (config.py)
```python
CONNECTION_TIMEOUT = 45.0       # Increase if drone takes longer to connect
ACTION_TIMEOUT = 15.0           # Increase for slow arm/disarm operations
MOVEMENT_TIMEOUT = 20.0         # Increase for longer distance movements
OFFBOARD_TIMEOUT = 8.0          # Rarely needs adjustment
```

### Jetson Nano Optimization
Current settings are optimized for Jetson Nano's ARM Cortex-A57:
- `PROCESS_INTERVAL = 0.1` - Balance between responsiveness and CPU usage
- `AUDIO_BUFFER_SIZE = 2048` - Optimized for 16kHz audio stream

### Noise Testing for Research
```python
NOISE_TESTING = True
SNR_DB = 15.0  # Lower values = more challenging conditions
# SNR_DB: 30 = very clean, 20 = moderate noise, 10 = heavy noise, 0 = extreme noise
```

## License and Credits

This project uses:
- **MAVSDK-Python** - Drone communication library
- **Vosk** - Offline speech recognition (Apache 2.0 License)
- **PyAudio** - Audio I/O library

Developed for autonomous drone research with voice control capabilities.