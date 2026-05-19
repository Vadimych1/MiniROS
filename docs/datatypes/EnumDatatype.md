# EnumDatatype

Use this datatype for serializing `Enums`

## Constructor
```python
EnumDatatype(enum: type[Enum])
```

## Usage
```python
from miniros.util.datatypes import EnumDatatype
from enum import Enum

class Animals(Enum):
    CAT = 0
    DOG = 1
    BIRD = 2

# you can use this for encoding and decoding enum values now
AnimalsDatatype = EnumDatatype(Animals)
```