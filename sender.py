import socket
import time
import pygame

STEER_AXIS_INDEX = 0
THROTTLE_AXIS_INDEX = 2
BRAKE_AXIS_INDEX = 3

SERVER_IP = "147.224.143.221"
SERVER_PORT = 4210
REFRESH_HZ = 60


def normalize_01_from_minus1_1(v: float) -> float:
    return max(0.0, min(1.0, (v + 1.0) / 2.0))


def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick found.")
        pygame.quit()
        return

    js = pygame.joystick.Joystick(0)
    js.init()

    print(f"Joystick detected: {js.get_name()}")
    print(f"Sending UDP to OCI Server at {SERVER_IP}:{SERVER_PORT}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    seq = 0
    period = 1.0 / REFRESH_HZ

    try:
        while True:
            start = time.time()

            pygame.event.pump()

            steering = js.get_axis(STEER_AXIS_INDEX)
            throttle = normalize_01_from_minus1_1(js.get_axis(THROTTLE_AXIS_INDEX))
            brake = normalize_01_from_minus1_1(js.get_axis(BRAKE_AXIS_INDEX))

            msg = f"CMD;{seq};{steering:.4f};{throttle:.4f};{brake:.4f}"
            sock.sendto(msg.encode("utf-8"), (SERVER_IP, SERVER_PORT))

            print(
                f"seq={seq} | "
                f"steer={steering:.4f} | "
                f"throttle={throttle:.4f} | "
                f"brake={brake:.4f}"
            )

            seq += 1

            elapsed = time.time() - start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopped sender.")
    finally:
        sock.close()
        pygame.quit()


if __name__ == "__main__":
    main()
