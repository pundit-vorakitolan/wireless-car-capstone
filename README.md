# Wireless Drive-By-Wire — Capstone Spring 2026

> ⚠️ **WARNING:** This repo is only recent as of Wednesday, April 22nd. Please create another branch and merge the most recent additions to main! Please be sure to keep the readme and presentations.

A system that allows a person to remotely steer a real car using a Logitech G29 steering wheel over the internet.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Hardware Requirements](#hardware-requirements)
3. [Software Requirements](#software-requirements)
4. [Setup](#setup)
   - [OCI Relay Server](#1-oci-relay-server)
   - [ESP32 (Car PCB)](#2-esp32-car-pcb)
   - [Sender Laptop](#3-sender-laptop)
5. [Running the System](#running-the-system)
6. [How It Works](#how-it-works)
7. [Not Yet Implemented](#not-yet-implemented)
8. [Troubleshooting](#troubleshooting)

---

## System Overview

```
[Driver Side]                  [Cloud]                    [Car Side]

G29 Wheel ──USB──► Laptop  ──internet──► OCI Relay Server ──WiFi──► ESP32 on PCB
                 (sender.py)            (relay_server.py)           (esp32_car.ino)
                                                                           │
                                                                      DAC outputs
                                                                           │
                                                                     Steering motor
```

The driver's laptop reads the G29 steering wheel and sends control packets over the internet to a cloud relay server (Oracle Cloud). The relay server forwards those packets to an ESP32 microcontroller on a custom PCB inside the car. The ESP32 runs a PID control loop, reading the actual steering angle from the car's CAN bus and outputting corrective voltages through DACs to drive the steering motor.

The relay server is necessary because the ESP32 is behind a mobile hotspot and has no public IP address — it cannot be reached directly from the internet. Instead, the ESP32 registers itself with the relay server on startup, and the relay server uses that registration to forward packets to it.

---

## Hardware Requirements

| Component | Qty | Notes |
|---|---|---|
| Logitech G29 Steering Wheel | 1 | Connected via USB to the driver's laptop |
| Driver Laptop | 1 | Any laptop capable of running Python 3 |
| ESP32 | 1 | Mounted on the custom DBW PCB |
| Custom DBW PCB | 1 | Houses the ESP32, CAN controller, and DACs |
| MCP2515 CAN Controller | 1 | Already on PCB — reads steering angle from car |
| MCP4728 DAC (×2) | 2 | Already on PCB — outputs analog voltages to car actuators |
| Mobile Hotspot | 1 | Provides WiFi for the ESP32 on the car side |
| Car with CAN bus | 1 | Steering angle sensor must transmit on CAN ID `0x2` |

### ESP32 Pin Reference

| Signal | ESP32 Pin |
|---|---|
| SPI SCK | 18 |
| SPI MISO | 19 |
| SPI MOSI | 23 |
| CAN CS | 5 |
| CAN INT | 4 |
| I2C Bus 1 SDA / SCL (DAC 1) | 21 / 22 |
| I2C Bus 2 SDA / SCL (DAC 2) | 33 / 32 |

---

## Software Requirements

### Driver Laptop

- Python 3.8 or newer
- `pygame` library (for reading the G29)

```
pip install pygame
```

### OCI Relay Server

- Python 3.8 or newer
- No additional libraries required — uses only the Python standard library

### ESP32

- Arduino IDE 2.x
- ESP32 board support package (install via **File → Preferences → Additional Board Manager URLs**, then search "esp32" in **Tools → Board → Board Manager**)
- The following libraries installed via **Tools → Manage Libraries**:
  - `Adafruit MCP4728`
  - `mcp_can` (by Seeed Studio)

> `WiFi` and `WiFiUdp` are included automatically with the ESP32 board package — do not install them separately.

---

## Setup

Complete these steps in order before running the system.

### 1. OCI Relay Server

The relay server runs on an Oracle Cloud instance and should already be running persistently. If it is not running, SSH into the instance and start it manually:

```
python3 relay_server.py
```

When running correctly you will see:
```
Relay server live on port 4210. Waiting for car heartbeat...
```

> **Note:** UDP port 4210 must be open in the OCI security list and the instance's firewall (`iptables` or `firewalld`). If the car never connects, this is the first thing to check.

---

### 2. ESP32 (Car PCB)

#### Step 1 — Set WiFi credentials

Open `esp32_car.ino` in Arduino IDE and update the following lines with the mobile hotspot's name and password:

```cpp
const char* ssid = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";
```

#### Step 2 — Flash the firmware

1. Connect the ESP32 to your laptop via USB.
2. In Arduino IDE, go to **Tools → Board** and select **ESP32 Dev Module**.
3. Go to **Tools → Port** and select the port your ESP32 is on (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux).
4. Click **Upload** (→ button). Wait for "Done uploading."

#### Step 3 — Verify connection

1. Open **Tools → Serial Monitor** and set the baud rate to **115200**.
2. Turn on the mobile hotspot.
3. Press the reset button on the ESP32. You should see:

```
WiFi connected
ESP32 IP: 10.x.x.x
UDP listening on port: 4210
```

Once connected, the ESP32 sends a heartbeat to the relay server every 2 seconds. On the relay server terminal you should see:

```
CAR CONNECTED: ('x.x.x.x', 4210)
```

This confirms the full car-to-server link is working.

---

### 3. Sender Laptop

1. Plug the G29 into the laptop via USB. Wait for the wheel to complete its self-calibration (it will spin and return to center on its own).
2. Confirm `pygame` is installed:
   ```
   pip install pygame
   ```
3. No other configuration is needed. The server IP is already set in `sender.py`.

---

## Running the System

Once the relay server is running and the ESP32 shows `CAR CONNECTED` on the server, run the sender on the driver's laptop:

```
python3 sender.py
```

Expected output:
```
Joystick detected: Logitech G29 Driving Force Racing Wheel
Sending UDP to 147.224.143.221:4210 at 60 Hz
seq=0 | steer=0.0000
seq=1 | steer=0.0012
...
```

The system is now live. Turning the G29 wheel will steer the car.

Press **Ctrl+C** to stop.

---

## How It Works

### Step 1 — Car registers with the relay server

When the ESP32 boots, it connects to the mobile hotspot and immediately begins sending a `HEARTBEAT` UDP packet to the relay server every 2 seconds. This does two things:
- Tells the server the ESP32's current public IP and port
- Keeps the hotspot's NAT mapping alive so the server can send packets back through it

The relay server responds with `ACK` to confirm it is reachable.

### Step 2 — Driver sends steering commands

`sender.py` reads the G29 steering axis at 60 Hz and sends a UDP packet to the relay server formatted as:

```
CMD;<seq>;<steer>
```

Where `<steer>` is a float from -1.0 (full left) to +1.0 (full right).

### Step 3 — Relay server forwards to the car

`relay_server.py` receives `CMD` packets from the driver's laptop and forwards them verbatim to the last address it received a `HEARTBEAT` from. If no heartbeat has been received in the last 30 seconds, the packet is dropped and a warning is printed.

### Step 4 — ESP32 drives the steering motor

The ESP32 parses the `CMD` packet and runs the steering value through a PID control loop:

```
Joystick steer (-1.0 to +1.0)
        │
        × 250
        │
   targetSTA (degrees)
        │
   low-pass smoothing filter
        │
   PID controller  ◄── actual angle read from CAN bus (ID 0x2)
        │
   torque value (-1500 to +1500)
        │
   DAC 2 Ch C = midpoint (2449) + torque  ──►  steering motor
   DAC 2 Ch D = midpoint (2449) - torque  ──►  (push-pull)
```

The midpoint DAC value of 2449 corresponds to 2.45 V, which is the zero-torque center point for the steering motor.

---

## Not Yet Implemented

> The following features are documented here for the next developer. The hardware (DAC channels, G29 pedal axes) is already in place — only software changes are needed.

### Throttle (Acceleration)

The G29 throttle pedal is on **axis 2**. pygame reports pedal axes as -1.0 when fully released and +1.0 when fully pressed. This must be normalized to a 0.0–1.0 range before use.

The normalized throttle value maps to an `accelmag` offset (0–1500) added to the baseline DAC voltages on **DAC 1, channels A and B**:

| Channel | Baseline Voltage | Baseline DAC Value | Formula |
|---|---|---|---|
| DAC 1 Ch A (accel main) | 0.37 V | ~370 | `accel1 + accelmag` |
| DAC 1 Ch B (accel sub) | 0.75 V | ~750 | `accel2 + (2 × accelmag)` |

```
accelmag = throttle_normalized × 1500
```

### Brakes

The G29 brake pedal is on **axis 3**, normalized the same way as throttle.

The normalized brake value maps to a `brakemag` offset (0–600) applied to **DAC 1, channels C and D**:

| Channel | Baseline Voltage | Baseline DAC Value | Formula |
|---|---|---|---|
| DAC 1 Ch C (brake main) | 3.38 V | ~3379 | `brake1 - brakemag` |
| DAC 1 Ch D (brake sub) | 1.48 V | ~1480 | `brake2 + brakemag` |

```
brakemag = brake_normalized × 600
```

> ⚠️ **Important:** The brake DAC channels must always be driven to their baseline voltages, even when no braking is commanded. Writing 0V to these channels is not the same as "no brake" and may be interpreted as a fault by the car's ECU.

### Code Changes Required

**`sender.py`** — restore the `normalize_01` helper and re-add throttle/brake to the packet:

```python
THROTTLE_AXIS_INDEX = 2
BRAKE_AXIS_INDEX = 3

def normalize_01(v: float) -> float:
    return max(0.0, min(1.0, (v + 1.0) / 2.0))

throttle = normalize_01(js.get_axis(THROTTLE_AXIS_INDEX))
brake = normalize_01(js.get_axis(BRAKE_AXIS_INDEX))
msg = f"CMD;{seq};{steer:.4f};{throttle:.4f};{brake:.4f}"
```

**`esp32_car.ino`** — update `sscanf` to parse throttle and brake, compute `accelmag` and `brakemag`, initialize baseline DAC values in `setup()`, and replace `dac.fastWrite(0, 0, 0, 0)` with:

```cpp
dac.fastWrite(
    accel1 + accelmag,
    accel2 + (2 * accelmag),
    brake1 - brakemag,
    brake2 + brakemag
);
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `No joystick found.` | G29 not detected by pygame | Unplug and replug the G29, wait for calibration spin, then rerun |
| Relay server never prints `CAR CONNECTED` | ESP32 cannot reach the server | Confirm hotspot is on; confirm UDP port 4210 is open on OCI |
| Steering does not respond after `sender.py` starts | CMD packets not reaching ESP32 | Confirm relay server is running and `CAR CONNECTED` was printed |
| Steering drives to the limit and stays there | CAN bus not working — no angle feedback to PID | Check MCP2515 wiring; verify crystal is 8 MHz |
| Serial Monitor shows `MCP2515 Init Failed` | SPI wiring issue or wrong CS pin | Check wiring against pin table above |
| Relay server prints `Car heartbeat timed out` | ESP32 stopped sending heartbeats | Check ESP32 is powered and connected to hotspot |
