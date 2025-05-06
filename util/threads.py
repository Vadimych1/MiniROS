import threading

def threaded(daemon=True):
    def wwrapper(func):
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
            t.start()
            return t
        return wrapper
        
    return wwrapper
