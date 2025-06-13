from typing import Any
import numpy as np
import cv2 as cv
from enum import Enum
import struct

class Datatype:
    """
    Base interface for encoding and decoding data
    """

    CODE = 0x00

    @staticmethod
    def decode(data: bytearray) -> Any:
        """
        Decode bytesarray (or bytesarray-like) to Python object.

        :param data: Data to decode 
        :type data: bytearray

        :return: Decoded data
        :rtype: Any
        """

        raise NotImplementedError

    @staticmethod
    def encode(data: Any) -> bytearray:
        """
        Encode Python object to bytesarray (or bytesarray-like)

        :param data: object to encode
        :type data: Any

        :return: Encoded data
        :rtype: bytearray
        """

        raise NotImplementedError

class NumpyArrayType(Enum):
    INT8 = 0x00
    INT16 = 0x01
    
    UINT8 = 0x02
    UINT16 = 0x03

    FLOAT16 = 0x04
    FLOAT32 = 0x05
    FLOAT64 = 0x06
_arr_type_to_numpy = {
    NumpyArrayType.INT8: np.dtype('uint8'),
    NumpyArrayType.INT16: np.dtype('int16'),

    NumpyArrayType.UINT8: np.dtype('uint8'),
    NumpyArrayType.UINT16: np.dtype('uint16'),

    NumpyArrayType.FLOAT16: np.dtype('float16'),
    NumpyArrayType.FLOAT32: np.dtype('float32'),
    NumpyArrayType.FLOAT64: np.dtype('float64'),
}
_numpy_to_arr_type = {val: key for key, val in _arr_type_to_numpy.items()}

class NumpyArray(Datatype):
    @staticmethod
    def decode(data: bytearray):
        datatype = NumpyArrayType(data[0])
        dtype =  _arr_type_to_numpy[datatype]
        b = np.frombuffer(data[1:], dtype)

        return b
    
    @staticmethod
    def encode(data: np.ndarray):
        encoded = data.tobytes()
        datatype = _numpy_to_arr_type[data.dtype]
        return bytearray([datatype.value]) + encoded

OpenCV_IMDECODE = int
class OpenCVImageType(Enum):
    RGB = 0x00
    GRAYSCALE = 0x01
    BGR = 0x02
_img_type_to_cv = {
    OpenCVImageType.RGB: cv.IMREAD_COLOR_RGB,
    OpenCVImageType.GRAYSCALE: cv.IMREAD_GRAYSCALE,
    OpenCVImageType.BGR: cv.IMREAD_COLOR_BGR,
}
# _cv_to_img_type = {value: key for key, value in _img_type_to_cv.items()} # uncomment if needed
class OpenCVImage(NumpyArray):
    @staticmethod
    def decode(data: bytearray) -> cv.Mat:
        datatype = OpenCVImageType(data[0])
        arr = NumpyArray.decode(data[1:])
        return cv.imdecode(arr, _img_type_to_cv[datatype])
    
    @staticmethod
    def encode(image: cv.Mat, datatype: OpenCVImageType) -> bytearray:
        arr = cv.imencode(".jpg", image)[1]
        return bytearray([datatype.value]) + NumpyArray.encode(arr)

class String(Datatype):
    @staticmethod
    def encode(data: str):
        return data.encode()
    
    @staticmethod
    def decode(data):
        return data.decode()
    
class Int(Datatype):
    @staticmethod
    def encode(data: int):
        return struct.pack(">i", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">i", data)[0]

class UInt(Datatype):
    @staticmethod
    def encode(data: int):
        return struct.pack(">I", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">I", data)[0]

class Float(Datatype):
    @staticmethod
    def encode(data: int):
        return struct.pack(">f", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">f", data)[0]


class Bytes(Datatype):
    @staticmethod
    def encode(data):
        return data
    
    @staticmethod
    def decode(data):
        return data


class Vector(Datatype):
    def __init__(self, x: float, y: float, z: float):
        super().__init__()

        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other: "Vector") -> "Vector":
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: "Vector") -> "Vector":
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __str__(self):
        return f"Vector({self.x}, {self.y}, {self.z})"

    @staticmethod
    def encode(data: "Vector") -> bytearray:
        return struct.pack(">fff", data.x, data.y, data.z)
    
    @staticmethod
    def decode(data: bytearray) -> "Vector":
        return Vector(*struct.unpack(">fff", data))

class Dict(Datatype):
    @staticmethod
    def encode(data: dict[str, Any], encoders: dict[type, tuple[Datatype, int]] = {
        str: (String, 0),
        int: (Int, 1),
        float: (Float, 2),
        bytes: (Bytes, 3),
        bytearray: (Bytes, 3),
        Vector: (Vector, 4)
    }) -> bytearray:
        keys = list(data.keys())

        metadata = b'\x00'.join(map(str.encode, keys))
        metadata_length = struct.pack(">I", len(metadata))
        metadata += metadata_length

        encoded = b''
        for key in keys:
            if type(data[key]) in encoders:
                e, ind = encoders[type(data[key])]
                e = e.encode(data[key])

                l = struct.pack(">I", len(e))
                encoded += l + bytearray([ind]) + e
            else:
                raise TypeError(f"encoder for type '{type(data[key])}' is not found")

        return encoded + metadata
    
    @staticmethod
    def decode(data: bytearray, decoders: dict[int, Datatype] = {
        0: String,
        1: Int,
        2: Float,
        3: Bytes,
    }) -> dict[str, Any]:
        metadata_length = struct.unpack(">I", data[-4:])[0]
        metadata = data[-4-metadata_length:-4]

        keys = list(map(bytes.decode, metadata.split(b"\x00")))

        i = 0
        decoded = {}
        while len(data[:-4-metadata_length]) > 0:
            length = struct.unpack(">I", data[:4])[0]
            ind = data[4]
            key = data[5:5+length]

            if ind not in decoders:
                raise TypeError(f"decoder for type '{ind}' is not found")

            decoded[keys[i]] = decoders[ind].decode(key)

            i += 1
            data = data[5+length:]

        return decoded

class Movement(Dict):
    def __init__(self, pos: Vector, ang: Vector):
        super().__init__()

        self.pos = pos
        self.ang = ang

    def __add__(self, other: "Movement"):
        return Movement(other.pos + self.pos, other.ang + self.ang)
    
    def __sub__(self, other: "Movement"):
        return Movement(self.pos - other.pos, self.ang - other.ang)

    def __str__(self):
        return f"Movement({self.pos}, {self.ang})"

    @staticmethod
    def encode(data: "Movement", encoders = { Vector: (Vector, 0) }):
        return Dict.encode({
            "pos": data.pos,
            "ang": data.ang,
        }, encoders)

    @staticmethod
    def decode(data, decoders = { 0: Vector }):
        d = Dict.decode(data, decoders)
        return Movement(
            d["pos"],
            d["ang"]
        )
