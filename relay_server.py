import socket
import time


UDP_IP = "0.0.0.0"
UDP_PORT = 4210
HEARTBEAT_TIMEOUT = 30.0


def main() -> None:
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
        except UnicodeDecodeError:
            message = ""

        if message == "HEARTBEAT":
            car_address = addr
            last_heartbeat = time.time()
            print(f"CAR CONNECTED: {addr}")
            try:
                sock.sendto(b"ACK", car_address)
            except OSError as e:
                print(f"Failed to ACK car: {e}")

        elif message == "ACK":
            pass

        elif car_address is not None and addr != car_address:
            if time.time() - last_heartbeat > HEARTBEAT_TIMEOUT:
                print(
                    f"WARNING: Car heartbeat timed out, "
                    f"dropping packet (stale address: {car_address})"
                )
            else:
                try:
                    sock.sendto(data, car_address)
                except OSError as e:
                    print(f"Failed to forward to car: {e}")


if __name__ == "__main__":
    main()
