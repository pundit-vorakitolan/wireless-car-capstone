# Wireless Drive-By-Wire — Capstone Spring 2026

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
7. [Troubleshooting](#troubleshooting)

---

## System Overview

```
[Driver]                        [Cloud]                  [Car]
G29 Wheel
    │ USB
Laptop
(sender.py) ──── internet ──► OCI Relay Server ──── WiFi/hotspot ──► ESP32 on PCB
                              (relay_server.py)                       (esp32_car.ino)
                                                                            │
                                                                       DAC outputs
                                                                            │
                                                                       Steering motor
```

The driver's laptop reads the G29 steering wheel and sends commands over the internet to a cloud relay server. The relay server forwards those commands to an ESP32 microcontroller mounted on a custom PCB inside the car. The ESP32 uses the steering input to drive a PID control loop, outputting analog voltages through DACs to control the car's steering motor.

---

## Hardware Requirements

| Component | Qty | Notes |
|---|---|---|
| Logitech G29 Steering Wheel | 1 | Connected via USB to the driver's laptop |
| Driver Laptop | 1 | Any laptop capable of running Python 3 |
| ESP32 | 1 | Mounted on the car PCB |
| Custom DBW PCB | 1 | Connects ESP32 to car CAN bus and DACs |
| MCP2515 CAN Controller | 1 | On PCB — SPI interface to ESP32 |
| MCP4728 DAC (×2) | 2 | On PCB — I2C interface to ESP32 |
| Mobile Hotspot | 1 | Car-side WiFi access point for the ESP32 |
| Car with CAN bus | 1 | Steering angle sensor must output on CAN ID `0x2` |

### Wiring / Pin Reference

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
- `pygame` library

Install dependencies:
```
pip install pygame
```

### OCI Server

- Python 3.8 or newer
- No external libraries required

### ESP32

- Arduino IDE 2.x
- The following Arduino libraries (install via Library Manager):
  - `Adafruit MCP4728`
  - `mcp_can` (by Seeed Studio)
  - `WiFi` (built into ESP32 Arduino core)
  - `WiFiUdp` (built into ESP32 Arduino core)
- ESP32 board support package installed in Arduino IDE

---

## Setup

### 1. OCI Relay Server

The relay server runs on an Oracle Cloud instance with a public IP. It should already be running persistently. If it is not running, SSH into the instance and start it:

```
python3 relay_server.py
```

You will see:
```
Relay server live on port 4210. Waiting for car heartbeat...
```

> **Note:** Ensure that UDP port 4210 is open in the OCI instance's security list and firewall rules.

---

### 2. ESP32 (Car PCB)

#### Configure WiFi credentials

Open `esp32_car.ino` in Arduino IDE. Find the following lines near the top and update them with the hotspot credentials the car will connect to:

```cpp
const char* ssid = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";
```

#### Flash the ESP32

1. Connect the ESP32 to your laptop via USB.
2. Open `esp32_car.ino` in Arduino IDE.
3. Under **Tools → Board**, select **ESP32 Dev Module**.
4. Under **Tools → Port**, select the COM port your ESP32 is on.
5. Click **Upload** (the right-arrow button).
6. Wait for "Done uploading." to appear.
7. Open the Serial Monitor (**Tools → Serial Monitor**) and set the baud rate to **115200**.
8. Power up the hotspot. You should see:

```
WiFi connected
ESP32 IP: ...
UDP listening on port: 4210
```

Once connected to WiFi, the ESP32 will automatically begin sending a heartbeat to the relay server every 2 seconds. The relay server terminal will print:

```
CAR CONNECTED: ('x.x.x.x', 4210)
```

---

### 3. Sender Laptop

No installation beyond `pip install pygame` is required. Plug in the G29 wheel via USB before running the script.

---

## Running the System

Once the relay server is running and the ESP32 is connected and sending heartbeats, start the sender on the driver's laptop:

```
python3 sender.py
```

You will see:
```
Joystick detected: Logitech G29 Driving Force Racing Wheel
Sending UDP to 147.224.143.221:4210 at 60 Hz
seq=0 | steer=0.0000
seq=1 | steer=0.0012
...
```

The system is now live. Turning the G29 wheel will steer the car.

To stop, press **Ctrl+C**.

---

## How It Works

1. `sender.py` reads the G29 steering axis at 60 Hz and sends a UDP packet formatted as `CMD;<seq>;<steer>` to the OCI server. Steering is a value from -1.0 (full left) to +1.0 (full right).

2. `relay_server.py` receives the packet and forwards it to the last known address of the ESP32, which it learned from the ESP32's periodic `HEARTBEAT` packets.

3. `esp32_car.ino` receives the `CMD` packet, scales the steering value to a target angle in degrees (×250), and runs a PID control loop:
   - The **actual** steering angle is read from the car's CAN bus (message ID `0x2`)
   - The PID computes a corrective torque
   - Two DAC channels output push-pull analog voltages to the steering motor:
     - **DAC Channel C** = midpoint + torque
     - **DAC Channel D** = midpoint − torque

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `No joystick found.` | G29 not detected | Unplug and replug the G29, then rerun |
| Relay server never prints `CAR CONNECTED` | ESP32 not reaching server | Check hotspot is on, check OCI firewall allows UDP 4210 |
| Steering does not respond | CMD packets not reaching ESP32 | Confirm relay server is running and car is connected |
| Steering runs to the limit | CAN bus not working (no angle feedback) | Check MCP2515 wiring and crystal frequency |
| Serial Monitor shows `MCP2515 Init Failed` | SPI wiring issue or wrong CS pin | Check wiring against pin table above |
