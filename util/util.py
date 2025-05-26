import time

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