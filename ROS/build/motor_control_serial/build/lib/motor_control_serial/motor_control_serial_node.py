from time import sleep
import serial

from motor_control_serial import dataEncoder

class motorVal:
    def __init__(self):
        self.FL = [0.0]
        self.RL = [0.0]
        self.RR = [0.0]
        self.FR = [0.0]

class commData:
    def __init__(self):
        self.wakeUp = [False]
        self.wheel = motorVal()
        self.steer = motorVal()

ser = serial.Serial("/dev/ttyACM0", 115200)

enc = dataEncoder.dataEncoder(0)
dec = dataEncoder.dataDecoder()
sendData = commData()
recvData = commData()

def encoderInit():
    enc.append(0, sendData.wakeUp)
    enc.append(1, sendData.wheel.FL)
    enc.append(2, sendData.wheel.RL)
    enc.append(3, sendData.wheel.RR)
    enc.append(4, sendData.wheel.FR)
    enc.append(5, sendData.steer.FL)
    enc.append(6, sendData.steer.RL)
    enc.append(7, sendData.steer.RR)
    enc.append(8, sendData.steer.FR)
    enc.init()
    dataPacket = enc.getPacket()
    ser.write(bytes(dataPacket.toInit.data))
    for data in dataPacket.toInit.data:
        dec.appendToBuffer(data)
    dec.decode()

def send():
    enc.encode()
    dataPacket = enc.getPacket()
    ser.write(bytes(dataPacket.toSend.data))

def recv():
    dataPacket = enc.getPacket()
    data_num = ser.in_waiting
    if data_num >= dataPacket.toSend.length:
        buff = ser.read(data_num)
        for data in buff:
            dec.appendToBuffer(data)        
        dec.decode()
        recvData.wakeUp[0] = dec.decodedData(0, 0)
        recvData.wheel.FL[0] = dec.decodedData(0, 1)
        recvData.wheel.RL[0] = dec.decodedData(0, 2)
        recvData.wheel.RR[0] = dec.decodedData(0, 3)
        recvData.wheel.FR[0] = dec.decodedData(0, 4)
        recvData.steer.FL[0] = dec.decodedData(0, 5)
        recvData.steer.RL[0] = dec.decodedData(0, 6)
        recvData.steer.RR[0] = dec.decodedData(0, 7)
        recvData.steer.FR[0] = dec.decodedData(0, 8)

def printData():
    print(recvData.wakeUp, recvData.wheel.FL, recvData.wheel.RL, recvData.wheel.RR, recvData.wheel.FR, recvData.steer.FL, recvData.steer.RL, recvData.steer.RR, recvData.steer.FR)

def setData():
    sendData.wakeUp[0] = not recvData.wakeUp[0]
    sendData.wheel.FL[0] = 0.0
    sendData.wheel.RL[0] = 0.0
    sendData.wheel.RR[0] = 10.0
    sendData.wheel.FR[0] = 0.0
    sendData.steer.FL[0] = 0.0
    sendData.steer.RL[0] = 0.0
    sendData.steer.RR[0] = 0.0
    sendData.steer.FR[0] = 0.0

def main():
    encoderInit()
    while True:
        recv()
        printData()
        setData()
        send()
        sleep(0.1)

if __name__ == '__main__':
    main()