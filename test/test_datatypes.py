from miniros import datatypes
import random, math, enum


async def test_int():
    int_d = 120010
    encoded = datatypes.Int.encode(int_d)
    decoded = datatypes.Int.decode(encoded)

    assert decoded == int_d

    int_d = -120031
    encoded = datatypes.Int.encode(int_d)
    decoded = datatypes.Int.decode(encoded)

    assert decoded == int_d


async def test_uint():
    uint_d = 8814810
    encoded = datatypes.UInt.encode(uint_d)
    decoded = datatypes.UInt.decode(encoded)

    assert decoded == uint_d


async def test_float():
    float_d = random.uniform(-10000, -1)
    encoded = datatypes.Float.encode(float_d)
    decoded = datatypes.Float.decode(encoded)

    assert math.isclose(float_d, decoded, rel_tol=1e-6, abs_tol=1e-9)

    float_d = random.uniform(1, 10000)
    encoded = datatypes.Float.encode(float_d)
    decoded = datatypes.Float.decode(encoded)

    assert math.isclose(float_d, decoded, rel_tol=1e-6, abs_tol=1e-9)


async def test_bool():
    bool_d = random.choice([True, False])
    encoded = datatypes.Bool.encode(bool_d)
    decoded = datatypes.Bool.decode(encoded)

    assert decoded == bool_d


async def test_bytes():
    bytes_d = random.randbytes(1024)
    encoded = datatypes.Bytes.encode(bytes_d)
    decoded = datatypes.Bytes.decode(encoded)

    assert bytes_d == decoded


async def test_string():
    string_d = "Hello, world!"
    encoded = datatypes.String.encode(string_d)
    decoded = datatypes.String.decode(encoded)

    assert string_d == decoded


async def test_vector():
    v = datatypes.Vector(1, -1, 10.56)
    encoded = datatypes.Vector.encode(v)
    decoded = datatypes.Vector.decode(encoded)

    assert v == decoded


async def test_dict():
    d = {
        "a": "123",
        "b": 312,
        "c": b"Hello, world!",
        "d": datatypes.Vector(1, 2, 3),
    }

    encoded = datatypes.Dict.encode(d)
    decoded = datatypes.Dict.decode(encoded)

    assert d == decoded


async def test_any_array():
    arr = [1, 0.125, "abcdef"]

    encoded = datatypes.AnyArray.encode(arr)
    decoded = datatypes.AnyArray.decode(encoded)

    assert arr == decoded


async def test_enum_datatype():
    class MyEnum(enum.Enum):
        VAL_1 = 0
        VAL_2 = 1
        VAL_3 = 3

    enum_wrapper = datatypes.EnumDatatype(MyEnum)

    encoded1 = enum_wrapper.encode(MyEnum.VAL_1)
    encoded2 = enum_wrapper.encode(MyEnum.VAL_2)

    decoded1 = enum_wrapper.decode(encoded1)
    decoded2 = enum_wrapper.decode(encoded2)

    assert decoded1 == MyEnum.VAL_1
    assert decoded2 == MyEnum.VAL_2


# TODO: NumpyArray
# TODO: OpenCVImage
# TODO: NamedComposedDatatype
