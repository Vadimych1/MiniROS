# Dict
Datatype for handling `dicts`

Unlike JSON, Dict datatype can handle not only string/integer/float/bool data but every MiniROS datatype. By default it supports:
- String;
- Int;
- Float;
- Bytes;
- Vector;
- Movement.

You can change encoding extensions by creating (Python type)-(encoder, index) and (index)-(decoder) mappings:
```python
from miniros.util.datatypes import Dict, Int, String

MyCustomDatatype = ...


# default encoders and decoders are:
encoders: dict[type, tuple[Datatype, int]] = {
    str: (String, 0),
    int: (Int, 1),
    float: (Float, 2),
    bytes: (Bytes, 3),
    bytearray: (Bytes, 3),
    Vector: (Vector, 4),
    Movement: (Movement, 5),
}

decoders: dict[int, Datatype] = {
    0: String,
    1: Int,
    2: Float,
    3: Bytes,
    4: Vector,
    5: Movement
}


# using custom datatypes
encoders = {
    MyCustomDatatype: (MyCustomDatatype, 0),
    int: (Int, 1),
    str: (String, 2)
}

decoders = {
    0: MyCustomDatatype,
    1: Int,
    2: String
}

encoded_data = Dict.encode({
    "x": MyCustomDatatype(),
    "y": 20,
    "z": "303"
}, encoders = encoders)

decoded_data = Dict.decode(encoded_data, decoders = decoders)
```

*Make sure you are using the same encoders-decoders mappings, otherwise data would not decode correctly. Note that Dict datatype is slow and space-inefficient. You should use it only for transferring dicts with varying scheme. Use [miniros.util.NamedComposedDatatype](NamedComposedDatatype.md) for constant-structured data instead*