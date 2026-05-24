# Datatype
MiniROS between-nodes messaging is based on serializing information from subclasses of `miniros.util.datatypes`

MiniROS has these built-in datatypes:
- [Bool](Basic.md)
- [Int](Basic.md)
- [UInt](Basic.md)
- [Float](Basic.md)
- [Bytes](Basic.md)
- [String](Basic.md)
- [Vector](Vector.md)
- [Movement](Movement.md)
- [Dict](Dict.md)
- [AnyArray](AnyArray.md)
- [EnumDatatype](EnumDatatype.md)
- [NumpyArray](NumpyArray.md) # TODO
- [OpenCVImage](OpenCVImage.md) # TODO
- [NamedComposedDatatype](NamedComposedDatatype.md)
- [LidarDatatype](LidarDatatype.md)

## Creating your own datatype
There are two ways to create a datatype

### 1. Creating a subclass of `miniros.util.datatypes.Datatype`
This approach could be used to create datatypes with complex encoding logic and a lot of methods 
```python
from miniros.util.datatypes import Datatype
from msgpack import packb, unpackb

class Dog(Datatype):
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    @staticmethod
    def encode(data: "Dog") -> bytearray:
        return packb([data.name, data.age])
    
    @staticmethod
    def decode(data: bytearray) -> Dog:
        return Dog(*unpackb(data))
```

### 2. Making `miniros.util.datatypes.NamedComposedDatatype`
Use this approach to create simple and short multi-field datatype (see more [here](NamedComposedDatatype.md))
```python
from miniros.util.datatypes import NamedComposedDatatype, String, UInt

Dog = NamedComposedDatatype({
    "name": String,
    "age": UInt
}, "Dog")
```