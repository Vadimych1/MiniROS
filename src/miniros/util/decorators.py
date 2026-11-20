from .datatypes import NamedComposedDatatype
from .log import get_logger
import threading

_l = get_logger("decorators")


def parsedata(datatype: type | NamedComposedDatatype, arg: int = 1):
    def wwrapper(func):
        def wrapper(*args, **kwargs):
            args = list(args)

            try:
                args[arg] = datatype.decode(args[arg])

            except Exception as e:
                _l.warning(f"parsedata: failed to parse to '{datatype}': {e}")
                return None

            return func(*args, **kwargs)

        return wrapper

    return wwrapper


def aparsedata(datatype: type | NamedComposedDatatype, arg: int = 1):
    def wwrapper(func):
        async def wrapper(*args, **kwargs):
            args = list(args)

            try:
                args[arg] = datatype.decode(args[arg])

            except Exception as e:
                _l.warning(f"aparsedata: failed to parse to '{datatype}': {e}")
                return None

            return await func(*args, **kwargs)

        return wrapper

    return wwrapper


# TODO: add exception capturing logic inside thread
def threaded(daemon=True):
    def wwrapper(func):
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
            t.start()
            return t

        return wrapper

    return wwrapper
