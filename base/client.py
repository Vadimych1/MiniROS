from ..util.sock import TCPSockClient as SockClient
# from ..util.sock import UDPSockClient as SockClient # UNSTABLE
import threading
from miniros.util.datatypes import Datatype
from miniros.util.decorators import decorators
from typing import Callable
import sys
import time
from typing import Any
import cv2
import numpy as np

import logging

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] > %(message)s")

class Topic:
    def __init__(self, field: str, encoder: Datatype, post_func: Callable[[str, bytearray], Any]):
        self.post_func = post_func
        self.field = field
        self.encoder = encoder

    def post(self, data: Any) -> None:
        self.post_func(self.field, self.encoder.encode(data))

class ROSClient:
    def __init__(self, name: str, ip: str = "localhost", port: int = 3000):
        self.name = name
        self.ip = ip
        self.port = port

        self.client = SockClient(ip, port, name)
        self.run_thread = None
        
        self.fields = []

        for c in self.__class__.__dict__:
            if c.startswith("on_"):
                data = c.split("_")[1:]

                if len(data) == 2:
                    node, field = data
                    self.fields.append((node, field, self.__getattribute__(c)))
                else:
                    field = data[0]
                    self.client.anon_handlers[field] = self.__getattribute__(c)

    @decorators.threaded()
    def _run(self):
        self.client.mainloop()

    def run(self) -> threading.Thread:
        self.run_thread = self._run()
        
        time.sleep(0.2)

        for (node, field, handler) in self.fields:
            self.client.subscribe(node, field, handler)

        return self.run_thread

    def topic(self, field: str, datatype: Datatype):
        self.client.post(field, b"")
        return Topic(field, datatype, self.client.post)
    
    def anon(self, node: str, field: str, data: bytearray):
        self.client.anon(node, field, data)

if __name__ == "__main__":
    fr = 0
    st = time.time()

    class MyROSClient1(ROSClient):
        def on_cl2_cam(self, data):
            global fr, st

            if (len(data) < 10):
                return
            
            data = cv2.imdecode(np.frombuffer(data, np.uint8), flags=cv2.IMREAD_COLOR)
            fr += 1
            print(fr / (time.time() - st))

    class MyROSClient2(ROSClient):
        ...

    name = sys.argv[1]
    client = MyROSClient1(name) if name == "cl1" else MyROSClient2(name)
    client.run()

    if name == "cl2":
        topic1 = client.topic("cam")
        
        cap = cv2.VideoCapture(0)
        
        frames = 0
        # start_time = time.time()
        while cap.isOpened():
            ret, frame = cap.read()

            cv2.imshow("dd", frame)

            if not ret:
                break

            if True or frames % 1 == 0:
                data = cv2.imencode('.jpg', frame)[1].tobytes()
                topic1.post(data)

            frames += 1

            if cv2.waitKey(1) == ord("q"):
                break

    client.run_thread.join()