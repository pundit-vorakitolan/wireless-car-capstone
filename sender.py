import socket
import time

import pygame


SERVER_IP = "147.224.143.221"
SERVER_PORT = 4210
REFRESH_HZ = 60

STEER_AXIS_INDEX = 0


def main() -> None:
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick found.")
        pygame.quit()
        return

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Joystick detected: {js.get_name()}")
    print(f"Sending UDP to {SERVER_IP}:{SERVER_PORT} at {REFRESH_HZ} Hz")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    period = 1.0 / REFRESH_HZ
    seq = 0

    try:
        while True:
            start = time.time()

            pygame.event.pump()

            steer = js.get_axis(STEER_AXIS_INDEX)

            msg = f"CMD;{seq};{steer:.4f}"
            sock.sendto(msg.encode("utf-8"), (SERVER_IP, SERVER_PORT))

            print(f"seq={seq} | steer={steer:.4f}")

            seq += 1
            sleep_time = period - (time.time() - start)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
