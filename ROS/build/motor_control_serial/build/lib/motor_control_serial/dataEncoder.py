from typing import List
from enum import IntEnum
import struct
import time

MAX_DATA_NUM = 10
MAX_BIT = MAX_DATA_NUM * 32
MAX_BYTE = MAX_BIT // 7 + 5

MAX_PORT_NUM = 10
BUFFER_SIZE = 255

def bitRead(x: int, n: int) -> int:
    return (int(x) >> int(n)) & 0x1

def delayMicroseconds(us: int):
    if us <= 0:
        return
    time.sleep(us / 1_000_000.0)

class TYPE(IntEnum):
    NONE = 0
    BOOL = 10
    UINT8_T = 20
    UINT16_T = 21
    UINT32_T = 22
    UINT64_T = 23
    INT8_T = 30
    INT16_T = 31
    INT32_T = 32
    INT64_T = 33
    FLOAT = 40
    DOUBLE = 41

class TYPE_D(IntEnum):
    NONE = 0
    BOOL = 1
    UINT = 2
    INT = 3
    FLOAT = 4

class _LengthItem:
    def __init__(self):
        self.preEncoded = 0
        self.encoded = 0

class _Length:
    def __init__(self):
        self.bitSum: int = 0
        self.data: List["_LengthItem"] = [_LengthItem() for _ in range(MAX_DATA_NUM)]

class _ToInit:
    def __init__(self):
        self.length: int = 0
        self.data: List[int] = [0]*(MAX_DATA_NUM*2 + 5)

class _ToSend:
    def __init__(self):
        self.length: int = 0
        self.data: List[int] = [0]*MAX_BYTE

class dataEncoder:
    class dataPacket_t:
        def __init__(self):
            self.toInit = _ToInit()
            self.toSend = _ToSend()

    def __init__(self, id_: int):
        self._id: int = id_
        self._isEditable: bool = True
        self._type: List[TYPE] = [TYPE.NONE for _ in range(MAX_DATA_NUM)]
        self._ptr: List[object] = [None for _ in range(MAX_DATA_NUM)]
        self._length = _Length()
        self._binary: List[int] = [0]*MAX_BIT
        self._dataPacket = dataEncoder.dataPacket_t()

    def append(self, ord_: int, dataPtr_, size_: int = 0, signed: bool = False):
        if self._isEditable:
            self._type[ord_] = self.identifyType(dataPtr_, signed)
            self._ptr[ord_] = dataPtr_
            t = self._type[ord_]
            if t == TYPE.BOOL:
                pre_bits = 8
            elif t in (TYPE.UINT8_T, TYPE.INT8_T):
                pre_bits = 8
            elif t in (TYPE.UINT16_T, TYPE.INT16_T):
                pre_bits = 16
            else:
                pre_bits = 32
            self._length.data[ord_].preEncoded = pre_bits
            self._length.data[ord_].encoded = self.decideSize(self._type[ord_], size_)

    def init(self):
        self._isEditable = False
        self._length.bitSum = 0
        for i in range(MAX_DATA_NUM):
            self._length.bitSum += self._length.data[i].encoded

        num = 0
        self._dataPacket.toInit.data[num] = 0b11000000 | (self._id & 0x0F)
        num += 1
        for i in range(MAX_DATA_NUM):
            self._dataPacket.toInit.data[num] = int(self._type[i]) // 10
            num += 1
            self._dataPacket.toInit.data[num] = self._length.data[i].encoded & 0xFF
            num += 1

        checkSum = 0
        for i in range(1, num):
            checkSum += self._dataPacket.toInit.data[i]
        self._dataPacket.toInit.data[num] = (checkSum >> 14) & 0x7F
        num += 1
        self._dataPacket.toInit.data[num] = (checkSum >> 7) & 0x7F
        num += 1
        self._dataPacket.toInit.data[num] = (checkSum) & 0x7F
        num += 1

        self._dataPacket.toInit.data[num] = 0b10000000 | (num + 1)
        self._dataPacket.toInit.length = num + 1

    def encode(self):
        for i in range(MAX_BYTE):
            self._dataPacket.toSend.data[i] = 0
        self.generateBinary()
        num = 0
        self._dataPacket.toSend.data[num] = 0b10000000 | (self._id & 0x0F)
        num += 1
        for i in range(self._length.bitSum):
            self._dataPacket.toSend.data[num] |= (self._binary[i] & 1) << (6 - (i % 7))
            if (i % 7) == 6:
                num += 1
        if (self._length.bitSum % 7) != 0:
            num += 1
        checkSum = 0
        for i in range(1, num):
            checkSum += self._dataPacket.toSend.data[i]
        self._dataPacket.toSend.data[num] = (checkSum >> 14) & 0x7F
        num += 1
        self._dataPacket.toSend.data[num] = (checkSum >> 7) & 0x7F
        num += 1
        self._dataPacket.toSend.data[num] = (checkSum) & 0x7F
        num += 1
        self._dataPacket.toSend.data[num] = 0b10000000 | (num + 1)
        self._dataPacket.toSend.length = num + 1

    def getPacket(self):
        return self._dataPacket

    def identifyType(self, dataPtr_, signed: bool) -> TYPE:
        val = dataPtr_[0]
        if isinstance(val, bool):
            return TYPE.BOOL
        if isinstance(val, float):
            return TYPE.FLOAT
        if isinstance(val, int):
            return TYPE.INT32_T if signed else TYPE.UINT32_T
        return TYPE.NONE

    def decideSize(self, type_: TYPE, size_: int) -> int:
        if type_ == TYPE.BOOL:
            return 1
        if type_ in (TYPE.UINT64_T, TYPE.INT64_T, TYPE.FLOAT, TYPE.DOUBLE):
            return 32
        if size_ == 0:
            if type_ in (TYPE.UINT8_T, TYPE.INT8_T):
                return 8
            if type_ in (TYPE.UINT16_T, TYPE.INT16_T):
                return 16
            return 32
        return size_

    def _get_raw_bits_uint32(self, ord_: int) -> int:
        t = self._type[ord_]
        v = self._ptr[ord_][0]
        if t == TYPE.BOOL:
            return int(bool(v)) & 0x1
        if t in (TYPE.UINT8_T, TYPE.UINT16_T, TYPE.UINT32_T, TYPE.UINT64_T):
            return int(v) & 0xFFFFFFFF
        if t in (TYPE.INT8_T, TYPE.INT16_T, TYPE.INT32_T, TYPE.INT64_T):
            return int(v) & 0xFFFFFFFF
        if t in (TYPE.FLOAT, TYPE.DOUBLE):
            return struct.unpack('<I', struct.pack('<f', float(v)))[0]
        return int(v) & 0xFFFFFFFF

    def _get_raw_bits_int32(self, ord_: int) -> int:
        v = self._ptr[ord_][0]
        packed = struct.pack('<i', int(v))
        return struct.unpack('<I', packed)[0]

    def _get_raw_bits_float(self, ord_: int) -> int:
        v = self._ptr[ord_][0]
        return struct.unpack('<I', struct.pack('<f', float(v)))[0]

    def getData(self, ord_: int) -> int:
        t = self._type[ord_]
        group = int(t) // 10
        if group in (1, 2):
            devidedBinary = self._get_raw_bits_uint32(ord_)
        elif group == 3:
            devidedBinary = self._get_raw_bits_int32(ord_)
            fill = bitRead(devidedBinary, 31)
            for i in range(self._length.data[ord_].encoded, 32):
                if fill:
                    devidedBinary |= (1 << i)
                else:
                    devidedBinary &= ~(1 << i)
        elif group == 4:
            devidedBinary = self._get_raw_bits_float(ord_)
        else:
            devidedBinary = 0
        return devidedBinary & 0xFFFFFFFF

    def generateBinary(self):
        bitNum = 0
        for i in range(MAX_DATA_NUM):
            if self._type[i] != TYPE.NONE:
                encoded_bits = self._length.data[i].encoded
                wd = self.getData(i)
                for bit in range(encoded_bits):
                    self._binary[bitNum] = bitRead(wd, encoded_bits - bit - 1)
                    bitNum += 1

class dataDecoder:
    def __init__(self):
        self._type = [[TYPE_D.NONE for _ in range(MAX_DATA_NUM)] for __ in range(MAX_PORT_NUM)]
        self._length = [type('lenrec', (), {'bitSum': 0, 'encoded': [0]*MAX_DATA_NUM})() for _ in range(MAX_PORT_NUM)]
        class _DataStruct:
            __slots__ = ('buffer','toRead','binary','dividedBinary')
        self._data = _DataStruct()
        self._data.buffer = [0]*BUFFER_SIZE
        self._data.toRead = [0]*MAX_BYTE
        self._data.binary = [0]*MAX_BIT
        self._data.dividedBinary = [[0]*MAX_DATA_NUM for _ in range(MAX_PORT_NUM)]
        self._bufferIndex = 0

    def appendToBuffer(self, data: int):
        self._data.buffer[self._bufferIndex] = data & 0xFF
        self._bufferIndex += 1
        if self._bufferIndex >= BUFFER_SIZE:
            self._bufferIndex = BUFFER_SIZE - 1

    def decode(self) -> bool:
        error = self._extractData()
        if not error:
            id_ = self._data.toRead[0] & 0x0F
            hdr = (self._data.toRead[0] >> 6) & 0x03
            if hdr == 0b11:
                self._regId(id_)
            if hdr == 0b10:
                self._read(id_)
                self._divide(id_)
        return bool(error)

    def decodedData(self, id_: int, ord_: int):
        t = self._type[id_][ord_]
        if t == TYPE_D.BOOL:
            return bool(self._cast_bool(id_, ord_))
        elif t == TYPE_D.UINT:
            return int(self._cast_u32(id_, ord_))
        elif t == TYPE_D.INT:
            u = self._cast_u32(id_, ord_)
            if u & 0x80000000:
                return int(struct.unpack('<i', struct.pack('<I', u & 0xFFFFFFFF))[0])
            else:
                return int(u & 0x7FFFFFFF)
        elif t == TYPE_D.FLOAT:
            return float(self._cast_float(id_, ord_))
        else:
            return int(self._cast_u32(id_, ord_))

    def _extractData(self) -> int:
        error = 0
        for i in range(MAX_BYTE):
            self._data.toRead[i] = 0

        idx = 0
        while (self._data.buffer[idx] & 0b10000000) == 0:
            if idx == (BUFFER_SIZE - 1):
                error = 1
                break
            idx += 1
        self._shiftLeftArray(idx)

        if not error:
            length = 2
            while (self._data.buffer[length - 1] & 0b10000000) == 0:
                length += 1
                if length == BUFFER_SIZE:
                    error = 2
                    break

            if not error:
                if (self._data.buffer[length - 1] & 0b01111111) != length:
                    error = 3

                checkSum = 0
                for i in range(1, length - 4):
                    checkSum += self._data.buffer[i]
                chk = ((self._data.buffer[length - 4] << 14) | (self._data.buffer[length - 3] << 7) | (self._data.buffer[length - 2]))
                if checkSum != chk:
                    error = 4

                if error == 0:
                    for i in range(length):
                        self._data.toRead[i] = self._data.buffer[i]

            self._shiftLeftArray(length if error == 0 else idx)

        return error

    def _shiftLeftArray(self, step_: int):
        if step_ <= 0:
            return
        for i in range(BUFFER_SIZE):
            if (i + step_) < BUFFER_SIZE:
                self._data.buffer[i] = self._data.buffer[i + step_]
            else:
                self._data.buffer[i] = 0
        if self._bufferIndex >= step_:
            self._bufferIndex -= step_
        else:
            self._bufferIndex = 0

    def _regId(self, id_: int):
        num = 1
        while (self._data.toRead[num] >> 7) != 0b1:
            if (num % 2) == 1:
                grp = self._data.toRead[num]
                idx = (num - 1)//2
                if idx < MAX_DATA_NUM:
                    if grp == 1:
                        self._type[id_][idx] = TYPE_D.BOOL
                    elif grp == 2:
                        self._type[id_][idx] = TYPE_D.UINT
                    elif grp == 3:
                        self._type[id_][idx] = TYPE_D.INT
                    elif grp == 4:
                        self._type[id_][idx] = TYPE_D.FLOAT
                    else:
                        self._type[id_][idx] = TYPE_D.NONE
            else:
                idx = (num - 2)//2
                if idx < MAX_DATA_NUM:
                    self._length[id_].encoded[idx] = self._data.toRead[num]
            num += 1
        self._length[id_].bitSum = 0
        for i in range(MAX_DATA_NUM):
            self._length[id_].bitSum += self._length[id_].encoded[i]

    def _read(self, id_: int):
        num = 1
        for i in range(self._length[id_].bitSum):
            self._data.binary[i] = (self._data.toRead[num] >> (6 - (i % 7))) & 0x01
            if (i % 7) == 6:
                num += 1
        if (self._data.toRead[num] >> 7) != 0b1:
            num += 1

    def _divide(self, id_: int):
        num = 0
        for i in range(MAX_DATA_NUM):
            self._data.dividedBinary[id_][i] = 0
            dividedBinary = 0
            for j in range(self._length[id_].encoded[i]):
                delayMicroseconds(1)
                dividedBinary = ((dividedBinary << 1) | (self._data.binary[num] & 0x1)) & 0xFFFFFFFF
                num += 1
            if self._type[id_][i] == TYPE_D.INT:
                fill = bitRead(dividedBinary, self._length[id_].encoded[i] - 1) if self._length[id_].encoded[i] > 0 else 0
                for j in range(self._length[id_].encoded[i], 32):
                    if fill:
                        dividedBinary |= (1 << j)
                    else:
                        dividedBinary &= ~(1 << j)
            self._data.dividedBinary[id_][i] = dividedBinary & 0xFFFFFFFF

    def _cast_bool(self, id_: int, ord_: int) -> bool:
        return bool(self._data.dividedBinary[id_][ord_] & 0x1)

    def _cast_u32(self, id_: int, ord_: int) -> int:
        return int(self._data.dividedBinary[id_][ord_] & 0xFFFFFFFF)

    def _cast_float(self, id_: int, ord_: int) -> float:
        u = self._data.dividedBinary[id_][ord_] & 0xFFFFFFFF
        return struct.unpack('<f', struct.pack('<I', u))[0]
