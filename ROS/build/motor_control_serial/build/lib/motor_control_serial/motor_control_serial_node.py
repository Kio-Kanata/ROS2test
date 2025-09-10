import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

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

class Serial4wheel4steer(Node):
    def __init__(self):
        super().__init__('motor_control_serial_node')
        self.pub = self.create_publisher(Float64MultiArray, '/motor/actual_val', 10)
        self.sub = self.create_subscription(Float64MultiArray, '/rover/targets', self.motor_cb, 10)
        self.ser = serial.Serial("/dev/ttyACM0", 115200)
        self.enc = dataEncoder.dataEncoder(0)
        self.dec = dataEncoder.dataDecoder()
        self.sendData = commData()
        self.recvData = commData()
        self.encoderInit()
        self.timer = self.create_timer(0.1, self.loop)
    
    def encoderInit(self):
        self.enc.append(0, self.sendData.wakeUp)
        self.enc.append(1, self.sendData.wheel.FL)
        self.enc.append(2, self.sendData.wheel.RL)
        self.enc.append(3, self.sendData.wheel.RR)
        self.enc.append(4, self.sendData.wheel.FR)
        self.enc.append(5, self.sendData.steer.FL)
        self.enc.append(6, self.sendData.steer.RL)
        self.enc.append(7, self.sendData.steer.RR)
        self.enc.append(8, self.sendData.steer.FR)
        self.enc.init()
        dataPacket = self.enc.getPacket()
        self.ser.write(bytes(dataPacket.toInit.data))
        for data in dataPacket.toInit.data:
            self.dec.appendToBuffer(data)
        self.dec.decode()

    def send(self):
        self.enc.encode()
        dataPacket = self.enc.getPacket()
        self.ser.write(bytes(dataPacket.toSend.data))

    def recv(self):
        dataPacket = self.enc.getPacket()
        data_num = self.ser.in_waiting
        if data_num >= dataPacket.toSend.length:
            buff = self.ser.read(data_num)
            for data in buff:
                self.dec.appendToBuffer(data)        
            self.dec.decode()
            self.recvData.wakeUp[0] = self.dec.decodedData(0, 0)
            self.recvData.wheel.FL[0] = self.dec.decodedData(0, 1)
            self.recvData.wheel.RL[0] = self.dec.decodedData(0, 2)
            self.recvData.wheel.RR[0] = self.dec.decodedData(0, 3)
            self.recvData.wheel.FR[0] = self.dec.decodedData(0, 4)
            self.recvData.steer.FL[0] = self.dec.decodedData(0, 5)
            self.recvData.steer.RL[0] = self.dec.decodedData(0, 6)
            self.recvData.steer.RR[0] = self.dec.decodedData(0, 7)
            self.recvData.steer.FR[0] = self.dec.decodedData(0, 8)

    def printData(self):
        print(self.recvData.wakeUp, self.recvData.wheel.FL, self.recvData.wheel.RL, self.recvData.wheel.RR, self.recvData.wheel.FR, self.recvData.steer.FL, self.recvData.steer.RL, self.recvData.steer.RR, self.recvData.steer.FR)

    def setVal(self, msg):
        self.sendData.wheel.FL[0] = msg.data[0]
        self.sendData.wheel.RL[0] = msg.data[1]
        self.sendData.wheel.RR[0] = msg.data[2]
        self.sendData.wheel.FR[0] = msg.data[3]
        self.sendData.steer.FL[0] = msg.data[4]
        self.sendData.steer.RL[0] = msg.data[5]
        self.sendData.steer.RR[0] = msg.data[6]
        self.sendData.steer.FR[0] = msg.data[7]
    
    def motor_cb(self, msg):
        self.setVal(msg)
        pub_data = Float64MultiArray()
        pub_data.data = [self.recvData.wheel.FL[0], self.recvData.wheel.RL[0], self.recvData.wheel.RR[0], self.recvData.wheel.FR[0], self.recvData.steer.FL[0], self.recvData.steer.RL[0], self.recvData.steer.RR[0], self.recvData.steer.FR[0]]
        self.pub.publish(pub_data)
    
    def loop(self):
        self.recv()
        self.printData()
        self.sendData.wakeUp[0] = not self.recvData.wakeUp[0]
        self.send()

def main(args=None):
    rclpy.init(args=args)
    node = Serial4wheel4steer()
    rclpy.spin(node)

if __name__ == '__main__':
    main()