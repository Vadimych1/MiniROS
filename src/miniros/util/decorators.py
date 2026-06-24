import threading
import logging

_decorators_logger = logging.getLogger("decorators")


def parsedata(datatype: type, arg: int = 1):
    def wwrapper(func):
        def wrapper(*args, **kwargs):
            args = list(args)

            try:
                args[arg] = datatype.decode(args[arg])

            except Exception as e:
                _decorators_logger.debug(f"failed to parse to '{datatype}': {e}")
                return None

            return func(*args, **kwargs)

        return wrapper

    return wwrapper


def aparsedata(datatype: type, arg: int = 1):
    def wwrapper(func):
        async def wrapper(*args, **kwargs):
            args = list(args)

            try:
                args[arg] = datatype.decode(args[arg])

            except Exception as e:
                _decorators_logger.debug(f"failed to parse to '{datatype}': {e}")
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
