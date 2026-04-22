# Wireless Drive-By-Wire — Capstone Project

Remote control of a real car's steering over the internet using a joystick, a cloud relay server, and an ESP32 on the vehicle.

---

## System Overview

```
[Your PC]                  [OCI Cloud Server]         [ESP32 on Car]
sender.py         ──────►  relay_server.py  ──────►   esp32_car.ino
reads joystick             forwards packets            drives steering
```

Because the ESP32 is on a home/mobile WiFi network behind a NAT router, it has no public IP address and cannot be reached directly from the internet. The OCI server acts as a middleman that both sides can talk to.

---

## Files

| File | Runs on | Purpose |
|---|---|---|
| `sender.py` | Your PC | Reads joystick and sends control packets to the server |
| `relay_server.py` | OCI Cloud Server | Receives packets and forwards them to the car |
| `esp32_car.ino` | ESP32 (on car) | Receives steering commands and drives the actuators |

---

## How It Works — Step by Step

### 1. Car registers with the server (NAT hole punching)
When the ESP32 boots, it connects to WiFi and immediately begins sending a `HEARTBEAT` UDP packet to the OCI server every 2 seconds. This does two things:
- Tells the server "I'm here, this is my current public IP and port"
- Keeps the NAT router's port mapping alive so the server can send packets back through it

The server responds with `ACK` to confirm it is alive and to keep the NAT hole open from both directions.

### 2. Joystick sender streams control inputs
`sender.py` runs on your PC and reads three axes from the joystick at 60 Hz:
- **Steering** — axis 0, range -1.0 to +1.0
- **Throttle** — axis 2, normalized from -1/+1 to 0.0–1.0
- **Brake** — axis 3, normalized from -1/+1 to 0.0–1.0

Each frame it sends a UDP packet formatted as:
```
CMD;<seq>;<steer>;<throttle>;<brake>
```
Example: `CMD;1042;-0.3120;0.7500;0.0000`

### 3. Server forwards to the car
`relay_server.py` listens on UDP port 4210. When it receives a `CMD` packet from your PC, it looks up the last known address of the car and forwards the packet verbatim. If no heartbeat has been received from the car in the last 30 seconds, the packet is dropped and a warning is printed.

### 4. ESP32 drives the steering
The ESP32 parses the `CMD` packet and extracts the steering value. It then:

1. **Scales** the steering value (-1.0 to +1.0) to a target steering angle in degrees (× 250)
2. **Smooths** the target with a low-pass filter to avoid sharp jerks
3. **Reads** the actual current steering angle from the car's CAN bus (message ID `0x2`)
4. **Runs a PID loop** to compute a corrective torque value
5. **Outputs** the torque via two DAC channels in a push-pull configuration:
   - Channel A = midpoint + torque
   - Channel B = midpoint - torque

The DAC midpoint (2.45 V, or DAC value ~2449 out of 4095) corresponds to zero torque on the steering motor.

```
Joystick steer (-1.0 to +1.0)
        │
        × 250
        │
   targetSTA (degrees)
        │
   low-pass smooth
        │
   PID controller  ◄── actual angle from CAN bus
        │
   torque value
        │
   DAC A = 2449 + torque  ──► steering motor
   DAC B = 2449 - torque  ──►
```

---

## Hardware

- **ESP32** — main microcontroller on the car
- **MCP2515** — CAN bus controller (reads steering angle sensor via SPI)
- **MCP4728 (×2)** — quad 12-bit DAC over I2C; `dac` for throttle/brake, `dac2` for steering
- **Steering angle sensor** — sends angle on CAN ID `0x2`, little-endian int16, units of 0.1°

### Pin Assignments

| Signal | ESP32 Pin |
|---|---|
| SPI SCK | 18 |
| SPI MISO | 19 |
| SPI MOSI | 23 |
| CAN CS | 5 |
| CAN INT | 4 |
| I2C Bus 1 (SDA/SCL) | 21 / 22 |
| I2C Bus 2 (SDA/SCL) | 33 / 32 |

---

## Setup

### Relay Server (OCI)
1. SSH into your OCI instance
2. Ensure UDP port 4210 is open in the OCI security list and the instance firewall
3. Run: `python3 relay_server.py`

### Sender (PC)
1. Install dependencies: `pip install pygame`
2. Plug in your joystick/wheel
3. Run: `python3 sender.py`

### ESP32
1. Open `esp32_car.ino` in Arduino IDE
2. Install libraries: `Adafruit MCP4728`, `mcp_can`, `WiFi`, `WiFiUdp`
3. Update `ssid` and `password` with your WiFi credentials
4. Flash to the ESP32
