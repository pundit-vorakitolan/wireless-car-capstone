import socket
import time

UDP_IP = "0.0.0.0"
UDP_PORT = 4210

# How often (seconds) to expect a heartbeat before declaring car disconnected.
# ESP32 should send HEARTBEAT at least this often to keep NAT hole open.
HEARTBEAT_TIMEOUT = 30.0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Relay server live on port {UDP_PORT}. Waiting for car heartbeat...")

car_address = None
last_heartbeat = 0.0

while True:
    try:
        data, addr = sock.recvfrom(1024)
    except OSError as e:
        print(f"Socket error: {e}")
        time.sleep(1)
        continue

    try:
        message = data.decode("utf-8").strip()
        print(f"DEBUG - Received: '{message}' from {addr}")
    except UnicodeDecodeError:
        message = ""
        print(f"DEBUG - Received raw bytes from {addr}")

    if message == "HEARTBEAT":
        car_address = addr
        last_heartbeat = time.time()
        print(f"✅ CAR CONNECTED! Logged IP: {addr}")
        # ACK back so the car knows the server is alive and to keep the NAT mapping open
        try:
            sock.sendto(b"ACK", car_address)
        except OSError as e:
            print(f"Failed to ACK car: {e}")

    elif car_address and addr != car_address:
        # Check if car heartbeat has gone stale
        if time.time() - last_heartbeat > HEARTBEAT_TIMEOUT:
            print(f"⚠️  Car heartbeat timed out — dropping CMD packet (stale address: {car_address})")
        else:
            try:
                sock.sendto(data, car_address)
            except OSError as e:
                print(f"Failed to forward to car: {e}")
