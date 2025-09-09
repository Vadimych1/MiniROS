import threading
import warnings

def parsedata(datatype: type, arg: int = 1):
    def wwrapper(func):
        def wrapper(*args, **kwargs):
            args = list(args)
            
            try:
                args[arg] = datatype.decode(args[arg])
            
            except Exception as e:
                print("Exception occured while decoding:", e)
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
                print("Exception occured while decoding:", e)
                return None

            return await func(*args, **kwargs)
                
        return wrapper
    return wwrapper

def threaded(daemon=True):
    def wwrapper(func):
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
            t.start()
            return t
        return wrapper
        
    return wwrapper


@warnings.deprecated("Use parsedata, aparsedata and threaded functions instead")
class decorators:
    @staticmethod
    def parsedata(datatype: type, arg: int = 1):
        def wwrapper(func):
            def wrapper(*args, **kwargs):
                args = list(args)
                
                try:
                    args[arg] = datatype.decode(args[arg])
                
                except Exception as e:
                    print("Exception occured while decoding:", e)
                    return None
                    
                return func(*args, **kwargs)
            
            return wrapper
        
        return wwrapper

    @staticmethod
    def aparsedata(datatype: type, arg: int = 1):
        def wwrapper(func):
            async def wrapper(*args, **kwargs):
                args = list(args)
                
                try:
                    args[arg] = datatype.decode(args[arg])

                except Exception as e:
                    print("Exception occured while decoding:", e)
                    return None

                return await func(*args, **kwargs)
                    
            return wrapper
        return wwrapper

    def threaded(daemon=True):
        def wwrapper(func):
            def wrapper(*args, **kwargs):
                t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=daemon)
                t.start()
                return t
            return wrapper
            
        return wwrapper
