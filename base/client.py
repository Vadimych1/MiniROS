from miniros.util.sock import TCPSockClient as SockClient
from miniros.util.sock import AsyncDistrubutedClient as AsyncSockClient

import threading
from miniros.util.datatypes import Datatype
from miniros.util.decorators import decorators
from typing import Callable
import time
from typing import Any
import logging

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] > %(message)s")

class Topic:
    def __init__(self, field: str, encoder: Datatype, post_func: Callable[[str, bytearray], Any]):
        self.post_func = post_func
        self.field = field
        self.encoder = encoder

    def post(self, data: Any) -> None:
        self.post_func(self.field, self.encoder.encode(data))

class AsyncTopic:
    def __init__(self, field: str, encoder: Datatype, post_func: Callable[[str, bytearray], Any]):
        self.post_func = post_func
        self.field = field
        self.encoder = encoder

    async def post(self, data: Any) -> None:
        await self.post_func(self.field, self.encoder.encode(data))

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

class AsyncROSClient(ROSClient):
    def __init__(self, name, ip = "localhost", port = 3000):
        super().__init__(name, ip, port)

        self.client = AsyncSockClient(ip, port, name)

        self.fields = []
        self.client.anon_handlers = {}
        
        for c in self.__class__.__dict__:
            if c.startswith("on_"):
                data = c.split("_")[1:]

                if len(data) == 2:
                    node, field = data
                    self.fields.append((node, field, self.__getattribute__(c)))
                else:
                    field = data[0]
                    self.client.anon_handlers[field] = self.__getattribute__(c)

    async def run(self):
        for (node, field, handler) in self.fields:
            await self.client.subscribe(node, field, handler)

        await self.client.mainloop()

    async def topic(self, field: str, datatype: Datatype):
        await self.client.post(field, b"")
        return AsyncTopic(field, datatype, self.client.post)
    
    async def anon(self, node: str, field: str, data: bytes):
        await self.client.anon(node, field, data)

if __name__ == "__main__":
    import asyncio
    
    class Client1(AsyncROSClient):
        def __init__(self, ip="localhost", port=3000):
            super().__init__("client1", ip, port)
        
        async def on_hello(self, data, node):
            print(data, node)

            print("GOT GOT GOT !!!! YEEEEE")

    class Client2(AsyncROSClient):
        def __init__(self, ip="localhost", port=3000):
            super().__init__("client2", ip, port)

    if False:
        client = Client1()
        asyncio.run(client.run())

    else:
        from miniros.util.util import Ticker

        ticker = Ticker(0.5)

        client = Client2()

        async def main():
            while not client.client._is_running:
                await asyncio.sleep(0.5)

            print("Sending!")

            while True:
                await ticker.tick_async()
                await client.anon(
                    "client1",
                    "hello",
                    b"Hello, world!"
                )
        
        async def run():
            await asyncio.gather(
                client.run(),
                main(),
            )  

        asyncio.run(
            run()
        )
