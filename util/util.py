import time
import multiprocessing
from typing import Callable, Iterable, Any

multiprocessing.freeze_support()

class Ticker:
    """
    Ticker interface for providing constant send speed

    :param hz: wanted updates per second
    :type hz: int
    """

    def __init__(self, hz: int):
        self.time = 0

        self.hz = hz
        self.delay = 1 / hz

    def tick(self):
        """
        Update timer with a new time value and delay if needed
        """

        cur = time.time()
        while d := (cur - self.time) < self.delay:
            time.sleep(d)
            cur = time.time()
            
        self.time = cur

    def check(self):
        """
        Update timer and check is current tick available or not
        """
        
        cur = time.time()
        val = cur - self.time > self.delay
        self.time = cur

        return val

def _call_args(a):
    return a[0](*a[1:])

def _call_noargs(f):
    return f()

def run_paralelly(tasks: Iterable[Callable], args: Iterable[Any] | None = None):
    """
    Run specified tasks paralelly using multiprocessing
    """
    if args is not None and len(tasks) != len(args):
        raise ValueError("tasks and args length mismatch")
    
    pool = multiprocessing.Pool(len(tasks))

    if args is not None:
        pool.map(_call_args, zip(tasks, args))
    else:
        pool.map(_call_noargs, tasks)