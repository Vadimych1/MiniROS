from typing import Any
import numpy as np
import cv2 as cv
from enum import Enum
import struct
from msgpack import packb, unpackb
import math
import io


class Datatype:
    """
    Base interface for encoding and decoding data
    """

    CODE = 0x00  # TODO: check if this line still used, remove if not
    STATIC_SIZE = None  # int | None; represents number of bytes used to pack message if it is constant

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


class EnumDatatype:
    STATIC_SIZE = 1

    def __init__(self, enum: type[Enum]):
        self.enum = enum

    def encode(self, member):
        return bytearray([member.value])

    def decode(self, data: bytearray):
        return self.enum(data[0])


# new feature: named composed type
class NamedComposedValue:
    def __init__(self, values: dict[str, Any], parent: "NamedComposedDatatype"):
        super().__setattr__("_values", values)
        super().__setattr__("_names", list(parent.fields.keys()))
        super().__setattr__("_parent", parent)

    def __getattr__(self, name):
        if name == "values":
            return super().__getattribute__("_values")

        elif name == "parent":
            return super().__getattribute__("_parent")

        elif name == "names":
            return super().__getattribute__("_names")

        if name in self.names:
            if name in self.values:
                return self.values[name]

            else:
                return None

        else:
            raise AttributeError(
                f"NamedComposedValue of <NamedComposedDatatype {self.parent.name}> has no attribute '{name}'"
            )

    def __setattr__(self, name, value):
        v = self.values
        n = super().__getattribute__("_names")

        if name in n:
            v[name] = value
        else:
            raise AttributeError(
                f"NamedComposedValue of <NamedComposedDatatype {self.parent.name}> has no attribute '{name}'"
            )

    def __str__(self):
        vals = self.values
        return (
            f"<value of NamedComposedDatatype '{self.parent.name}' ["
            + ", ".join(
                map(
                    lambda x: x + ": " + (str(vals[x]) if x in vals else "None"),
                    self.names,
                )
            )
            + "]>"
        )


class NamedComposedDatatype(Datatype):
    def __init__(
        self,
        fields: dict[str, Datatype],
        name: str | None = None,
    ):
        # sort keys so the order is always the same
        fields = list(fields.items())
        fields.sort(key=lambda x: x[0])
        fields = dict(fields)

        self.fields = fields
        self._sizes = {k: v.STATIC_SIZE for k, v in fields.items()}

        if all(x != None for x in self._sizes.values()):
            self.STATIC_SIZE = sum(self._sizes.values())

        else:
            self.STATIC_SIZE = None

        self.name = name
        self.control_sum = sum(name.encode()) % 255 if name != None else 0

    def new(self, **values: dict[str, Any]):
        return NamedComposedValue(values, self)

    def __call__(self, **kwds):
        return self.new(**kwds)

    def encode(self, encode_data: NamedComposedValue) -> bytearray:
        values: dict[str, Any] = encode_data.values
        data = bytearray([self.control_sum])

        for k, v in self.fields.items():
            if k not in values:
                raise ValueError(f"provided data has no required attribute '{k}'")

            ssize = self._sizes[k]
            enc = v.encode(values[k])

            if ssize == None:
                data += struct.pack(">I", len(enc)) + enc

            else:
                data += enc

        return data

    def decode(self, data: bytearray) -> NamedComposedValue:
        values = {}

        cs = data[0]
        if cs != self.control_sum:
            raise ValueError(
                f"provided data has invalid checksum value {cs} instead of required {self.control_sum}"
            )

        i = 1
        for k, v in self.fields.items():
            ssize = self._sizes[k]

            if ssize == None:
                size = struct.unpack(">I", data[i : i + 4])[0]
                values[k] = v.decode(data[i + 4 : i + size + 4])
                i += 4 + size

            else:
                values[k] = v.decode(data[i : i + ssize])
                i += ssize

        return NamedComposedValue(values, self)

    def __str__(self):
        return (
            f"NamedComposedDatatype<{self.name} ["
            + ", ".join(map(lambda x: x[0] + ": " + str(x[1]), self.fields.items()))
            + "])"
        )


class NumpyArray(Datatype):
    STATIC_SIZE = None

    @staticmethod
    def decode(data: bytearray):
        return np.load(io.BytesIO(data))

    @staticmethod
    def encode(data: np.ndarray):
        buffer = io.BytesIO()
        np.save(buffer, data)

        return buffer.getvalue()


class AnyArray(Datatype):
    STATIC_SIZE = None

    @staticmethod
    def encode(data: list[Any]):
        return packb(data)

    @staticmethod
    def decode(data: bytearray) -> list:
        return unpackb(data)


OpenCV_IMDECODE = int


class OpenCVImageType(Enum):
    RGB = 0x00
    GRAYSCALE = 0x01
    BGR = 0x02


_img_type_to_cv = {
    OpenCVImageType.RGB: cv.IMREAD_COLOR,
    OpenCVImageType.GRAYSCALE: cv.IMREAD_GRAYSCALE,
    OpenCVImageType.BGR: cv.IMREAD_COLOR,
}


# _cv_to_img_type = {value: key for key, value in _img_type_to_cv.items()} # uncomment if needed
class OpenCVImage(NumpyArray):
    STATIC_SIZE = None

    @staticmethod
    def decode(data: bytearray) -> "cv.Mat":
        datatype = OpenCVImageType(data[0])
        arr = NumpyArray.decode(data[1:])
        return cv.imdecode(arr, _img_type_to_cv[datatype])

    @staticmethod
    def encode(image: "cv.Mat", datatype: OpenCVImageType) -> bytearray:
        arr = cv.imencode(".jpg", image)[1]
        return bytearray([datatype.value]) + NumpyArray.encode(arr)


class String(Datatype):
    STATIC_SIZE = None

    @staticmethod
    def encode(data: str):
        return data.encode()

    @staticmethod
    def decode(data):
        return data.decode()


class Bool(Datatype):
    STATIC_SIZE = 1

    @staticmethod
    def encode(data: bool):
        return struct.pack(">?", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">?", data)[0]


class Int(Datatype):
    STATIC_SIZE = 4

    @staticmethod
    def encode(data: int):
        return struct.pack(">i", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">i", data)[0]


class UInt(Datatype):
    STATIC_SIZE = 4

    @staticmethod
    def encode(data: int):
        return struct.pack(">I", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">I", data)[0]


class Float(Datatype):
    STATIC_SIZE = 4

    @staticmethod
    def encode(data: int):
        return struct.pack(">f", data)

    @staticmethod
    def decode(data: bytearray):
        return struct.unpack(">f", data)[0]


class Bytes(Datatype):
    STATIC_SIZE = None

    @staticmethod
    def encode(data):
        return data

    @staticmethod
    def decode(data):
        return data


class Vector(Datatype):
    STATIC_SIZE = 4 * 3

    def __init__(self, x: float, y: float, z: float):
        super().__init__()

        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other: "Vector") -> "Vector":
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector") -> "Vector":
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other: "Vector") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def __abs__(self):
        return self.__mul__(self) ** 0.5

    def __str__(self):
        return f"Vector({self.x}, {self.y}, {self.z})"

    def __iter__(self):
        for x in self.x, self.y, self.z:
            yield x

    def __eq__(self, value):
        return all(
            math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-9) for x, y in zip(value, self)
        )

    def norm(self) -> float:
        return (self * self) ** 0.5

    @staticmethod
    def encode(data: "Vector") -> bytearray:
        return struct.pack(">fff", data.x, data.y, data.z)

    @staticmethod
    def decode(data: bytearray) -> "Vector":
        return Vector(*struct.unpack(">fff", data))


class Movement(Datatype):
    STATIC_SIZE = 4 * 6

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
    def encode(data: "Movement"):
        return struct.pack(">ffffff", *data.pos, *data.ang)

    @staticmethod
    def decode(data: bytearray):
        a, b, c, d, e, f = struct.unpack(">ffffff", data)
        return Movement(Vector(a, b, c), Vector(d, e, f))


class Dict(Datatype):
    STATIC_SIZE = None

    @staticmethod
    def encode(
        data: dict[str, Any],
        encoders: dict[type, tuple[Datatype, int]] = {
            str: (String, 0),
            int: (Int, 1),
            float: (Float, 2),
            bytes: (Bytes, 3),
            bytearray: (Bytes, 3),
            Vector: (Vector, 4),
            Movement: (Movement, 5),
        },
    ) -> bytearray:
        keys = list(data.keys())

        metadata = b"\x00".join(map(str.encode, keys))
        metadata_length = struct.pack(">I", len(metadata))
        metadata += metadata_length

        encoded = b""
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
    def decode(
        data: bytearray,
        decoders: dict[int, Datatype] = {
            0: String,
            1: Int,
            2: Float,
            3: Bytes,
            4: Vector,
            5: Movement,
        },
    ) -> dict[str, Any]:
        metadata_length = struct.unpack(">I", data[-4:])[0]
        metadata = data[-4 - metadata_length : -4]

        keys = list(map(bytes.decode, metadata.split(b"\x00")))

        i = 0
        decoded = {}
        while len(data[: -4 - metadata_length]) > 0:
            length = struct.unpack(">I", data[:4])[0]
            ind = data[4]
            key = data[5 : 5 + length]

            if ind not in decoders:
                raise TypeError(f"decoder for type '{ind}' is not found")

            decoded[keys[i]] = decoders[ind].decode(key)

            i += 1
            data = data[5 + length :]

        return decoded


LidarDatatype = NamedComposedDatatype(
    {"distances": NumpyArray, "angles": NumpyArray},
    "LidarDatatype",
)
