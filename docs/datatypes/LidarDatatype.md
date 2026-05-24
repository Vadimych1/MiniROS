# LidarDatatype
This datatype is a nice example of creating NamedComposedDatatype:
```python
LidarDatatype = NamedComposedDatatype(
    {"distances": NumpyArray, "angles": NumpyArray},
    "LidarDatatype",
)
```

## Constructor
```python
LidarDatatype(*, distances: numpy.ndarray | list[float], angles: numpy.ndarray | list[float])
```