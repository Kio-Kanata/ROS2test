from time import sleep
import serial

ser = serial.Serial("/dev/ttyACM0", 115200)

def main():
    while True:
        data = ser.read(ser.in_waiting)
        if len(data) > 0:
            print(f"0x{data.hex()}")
        sleep(0.1)

if __name__ == '__main__':
    main()
