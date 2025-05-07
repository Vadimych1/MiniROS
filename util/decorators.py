import threading

class decorators:
    @staticmethod
    def parsedata(datatype: type, arg: int = 0):
        def wwrapper(func):
            def wrapper(*args, **kwargs):
                args = list(args)
                args[arg] = datatype.decode(args[arg])
                return func(*args, **kwargs)
            
            return wrapper
        
        return wwrapper

    def symlink(name: str):
        def wwrapper(func):
            owner = func.__self__

            symlinks = owner.symlinks if "symlinks" in owner.__dir__() else {}
            symlinks[name] = func
            owner.symlinks = symlinks

            return func

        return wwrapper

    def threaded(daemon=True):
        def wwrapper(func):
            def wrapper(*args, **kwargs):
                t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
                t.start()
                return t
            return wrapper
            
        return wwrapper
