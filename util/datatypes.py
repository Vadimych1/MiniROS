from typing import Any
import numpy as np
import cv2 as cv
from enum import Enum

class Datatypes:
    NONE = 0x00

class Datatype:
    """
    Base interface for encoding and decoding data
    """

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
    
if __name__ == "__main__":
    image = cv.imread("test.jpg")

    encoded = OpenCVImage.encode(image, OpenCVImageType.BGR)
    decoded = OpenCVImage.decode(encoded)

    cv.imshow("lol", decoded)
    cv.waitKey(0)