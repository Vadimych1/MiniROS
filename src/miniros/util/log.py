import logging
import datetime

_loggers = {}

def get_logger(name: str, level = logging.INFO) -> logging.Logger:
    if type(name) is not str:
        raise ValueError('name must be of type str')
    
    if name in _loggers:
        return _loggers[name]
    
    else:
        l = logging.getLogger(name)
        l.handlers.clear()
        
        l.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s:%(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        file_handler = logging.FileHandler(f'logs/miniros-{datetime.datetime.now()}.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        
        l.addHandler(file_handler)
        l.addHandler(console_handler)
        
        _loggers[name] = l
        
        return l
