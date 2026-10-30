from copy import deepcopy
from typing import Callable
from enum import Enum


class InterpolateCopy(Enum):
    COPY_PREVIOUS = 0
    COPY_NEXT = 1


class UnknownTimestamp(Enum):
    THROW = 0
    LINEARIZE = 1
    RETURN_LAST = 2


def ainterpolate(
    getter_name: str,
    interpolate_fields: list[str],
    timestamp_field: str = "timestamp",
    arg_index: int = 1,
    buffer_size: int = 10,
    copy_method = InterpolateCopy.COPY_NEXT, 
    interpolate_unknown_method = UnknownTimestamp.THROW,
):
    """
    Caches value from MiniROS topic to use in 'get_interpolated' and '@ause_interpolate'
    """
    
    is_ts_field_str = type(timestamp_field) is str
    is_fields_str = all(type(field) is str for field in interpolate_fields)
    
    if buffer_size < 2:
        raise ValueError("buffer size must be at least 2 for interpolation")
    
    if is_ts_field_str and is_fields_str:
        def wwrapper(func):
            async def wrapper(self, *args, **kwargs):
                interp_values = getattr(self, "__interp_values", {})
                if getter_name not in interp_values:
                    interp_values[getter_name] = {
                        "cpm": copy_method,
                        "ium": interpolate_unknown_method,
                        "ts_f": timestamp_field,
                        "int_fs": interpolate_fields,
                        "data": [],
                    }
                    setattr(self, "__interp_values", interp_values)
                
                interp_values[getter_name]["data"].append(args[arg_index - 1])
                if len(interp_values[getter_name]["data"]) > buffer_size:
                    interp_values[getter_name]["data"].pop(0) 
                                
                return await func(self, *args, **kwargs)
            
            return wrapper
        return wwrapper
    
    else:
        raise ValueError("'timestamp_field' and 'interpolate_fields' should be of types 'str' and 'list[str]'")

def interpolate(
    getter_name: str,
    interpolate_fields: list[str],
    timestamp_field: str = "timestamp",
    arg_index: int = 1,
    buffer_size: int = 10,
    copy_method = InterpolateCopy.COPY_NEXT, 
    interpolate_unknown_method = UnknownTimestamp.THROW,
):
    """
    Caches value from MiniROS topic to use in 'get_interpolated' and '@ause_interpolate'
    """
    
    is_ts_field_str = type(timestamp_field) is str
    is_fields_str = all(type(field) is str for field in interpolate_fields)
    
    if buffer_size < 2:
        raise ValueError("buffer size must be at least 2 for interpolation")
    
    if is_ts_field_str and is_fields_str:
        def wwrapper(func):
            def wrapper(self, *args, **kwargs):
                interp_values = getattr(self, "__interp_values", {})
                if getter_name not in interp_values:
                    interp_values[getter_name] = {
                        "cpm": copy_method,
                        "ium": interpolate_unknown_method,
                        "ts_f": timestamp_field,
                        "int_fs": interpolate_fields,
                        "data": [],
                    }
                    setattr(self, "__interp_values", interp_values)
                
                interp_values[getter_name]["data"].append(args[arg_index - 1])
                if len(interp_values[getter_name]["data"]) > buffer_size:
                    interp_values[getter_name]["data"].pop(0) 
                                
                return func(self, *args, **kwargs)
            
            return wrapper
        return wwrapper
    
    else:
        raise ValueError("'timestamp_field' and 'interpolate_fields' should be of types 'str' and 'list[str]'")


def ause_interpolate(getter_name: str, timestamp_function: Callable):
    """
    Adds interpolated value to MiniROS topic handler argument list, for example:
    
    ```python
    from miniros import aparsedata, datatypes, AsyncROSClient
    
    TSFloatDt = datatypes.NamedComposedDatatype({
        "timestamp": datatypes.Double,
        "value": datatypes.Float
    }, "ts_float")
    
    class Client(AsyncROSClient):
        @interpolate("motor_speed", ["value"])
        @aparsedata(TSFloatDt)
        async def on_motorcontroller_speed(self, speed):
            print(f"new data: {speed.value} at {speed.timestamp}")
        
        # in this example on_sync_heartbeat carries a Double with timestamp
        # args[-1] represents last argument which is time from heartbeat
        # NOTE: ause_interpolate adds an interpolated argument right after 'self'
        @ause_interpolate("motor_speed", lambda args: args[-1])
        @aparsedata(datatypes.Double)
        async def on_sync_heartbeat(self, motor_speed, timestamp):
            print(f"heartbeat: {motor_speed.value} at {timestamp}")
    
    ```
    """
    
    def wwrapper(func):
        async def wrapper(self, *args, **kwargs):
            v = get_interpolated(self, getter_name, timestamp_function(args))
            return await func(self, v, *args, **kwargs)
        return wrapper
    return wwrapper

def use_interpolate(getter_name: str, timestamp_function: Callable):
    """
    Adds interpolated value to MiniROS topic handler argument list. See 'ause_interpolate' for example
    """
    
    def wwrapper(func):
        def wrapper(self, *args, **kwargs):
            v = get_interpolated(self, getter_name, timestamp_function(args))
            return func(self, v, *args, **kwargs)
        return wrapper
    return wwrapper

def get_interpolated(self, getter_name: str, current_timestamp: float | Callable):
    """
    Returns value linearly interpolated to current_timestamp
    Requires data from 'ainterpolate' decorator to work properly 
    """
    
    interp_values = getattr(self, "__interp_values", {})
    if getter_name not in interp_values:
        raise ValueError(f"getter name {getter_name} does not exist or haven't initialized yet")

    interp_values = interp_values[getter_name]

    copy_method: InterpolateCopy = interp_values["cpm"]
    interpolate_unknown_method: UnknownTimestamp = interp_values["ium"]
    timestamp_field: str = interp_values["ts_f"]
    interpolate_fields: list[str] = interp_values["int_fs"]
    data = interp_values["data"]

    if len(data) < 2:
        raise ValueError(f"not enough values in interpolation buffer: {len(data)} of required 2")

    if callable(current_timestamp):
        current_timestamp = current_timestamp()

    data = sorted(data, key=lambda x: getattr(x, timestamp_field))

    # exact match
    for item in data:
        if getattr(item, timestamp_field) == current_timestamp:
            return deepcopy(item)

    first_ts = getattr(data[0], timestamp_field)
    last_ts = getattr(data[-1], timestamp_field)

    if current_timestamp < first_ts:
        if interpolate_unknown_method == UnknownTimestamp.THROW:
            raise Exception(f"found no value for timestamp {current_timestamp} and strict mode enabled")
        elif interpolate_unknown_method == UnknownTimestamp.RETURN_LAST:
            return deepcopy(data[0])
        d1, d2 = data[0], data[1]

    elif current_timestamp > last_ts:
        if interpolate_unknown_method == UnknownTimestamp.THROW:
            raise Exception(f"found no value for timestamp {current_timestamp} and strict mode enabled")
        elif interpolate_unknown_method == UnknownTimestamp.RETURN_LAST:
            return deepcopy(data[-1])
        d1, d2 = data[-2], data[-1]

    else:
        for i in range(len(data) - 1):
            t1 = getattr(data[i], timestamp_field)
            t2 = getattr(data[i + 1], timestamp_field)

            if t1 < current_timestamp < t2:
                d1, d2 = data[i], data[i + 1]
                break

    if copy_method == InterpolateCopy.COPY_PREVIOUS:
        cp = deepcopy(d1)
    else:
        cp = deepcopy(d2)

    setattr(cp, timestamp_field, current_timestamp)

    vals1 = [getattr(d1, f) for f in interpolate_fields]
    vals2 = [getattr(d2, f) for f in interpolate_fields]
    t1 = getattr(d1, timestamp_field)
    t2 = getattr(d2, timestamp_field)

    vals_new = _interp_values(t1, t2, current_timestamp, vals1, vals2)

    for f, v in zip(interpolate_fields, vals_new):
        setattr(cp, f, v)

    return cp
    

def _interp_values(ts_1: float, ts_2: float, ts: float, values_1: list[float], values_2: list[float]):
    for a, b in zip(values_1, values_2):
        yield a + (b - a) / (ts_2 - ts_1) * (ts - ts_1)

if __name__ == "__main__":
    import asyncio
    from miniros import aparsedata, datatypes

    TSFloatDt = datatypes.NamedComposedDatatype({
        "timestamp": datatypes.Double,
        "value": datatypes.Float
    }, "ts_float")

    class Client:
        @aparsedata(TSFloatDt)
        @ainterpolate("motor_speed", ["value"])
        async def on_motorcontroller_speed(self, speed):
            print(f"new data: {speed.value} at {speed.timestamp}")
        
        # in this example on_sync_heartbeat carries a Double with timestamp
        # args[-1] represents last argument which is time from heartbeat
        # NOTE: ause_interpolate adds an interpolated argument right after 'self'
        @aparsedata(datatypes.Double)
        @ause_interpolate("motor_speed", lambda args: args[-1])
        async def on_sync_heartbeat(self, motor_speed, timestamp):
            print(f"heartbeat: {motor_speed.value} at {timestamp}")

    async def main():
        c = Client()
        
        await c.on_motorcontroller_speed(TSFloatDt.encode(TSFloatDt(timestamp=0.0, value=1.0)))
        await c.on_motorcontroller_speed(TSFloatDt.encode(TSFloatDt(timestamp=1.0, value=3.0)))
        await c.on_motorcontroller_speed(TSFloatDt.encode(TSFloatDt(timestamp=2.0, value=5.0)))
        
        await c.on_sync_heartbeat(datatypes.Double.encode(1.0))
        await c.on_sync_heartbeat(datatypes.Double.encode(1.5))
        
        print("done")

    asyncio.run(main())