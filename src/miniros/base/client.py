from miniros.util.src.sock import AsyncDistributedClient as AsyncSockClient
import threading
from miniros.util.datatypes import NamedComposedDatatype, Datatype
from miniros.util.decorators import threaded
from typing import Callable
import time
from typing import Any
import logging

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] > %(message)s"
)


class AsyncTopic:
    def __init__(
        self,
        field: str,
        encoder: NamedComposedDatatype | type[Datatype],
        post_func: Callable[[str, bytearray], Any],
    ):
        self.post_func = post_func
        self.field = field
        self.encoder = encoder

    async def post(self, data: Any) -> None:
        await self.post_func(self.field, self.encoder.encode(data))


class AsyncROSClient:
    def __init__(self, name, ip="localhost", port=3000, _parse_handlers=True):
        self.name = name
        self.ip = ip
        self.port = port

        self.fields = []

        self.client = AsyncSockClient(ip, port, name)

        self.fields = []
        self.client.anon_handlers = {}

        if _parse_handlers:
            self._parse_handlers()

    def _parse_handlers(self):
        for c in self.__class__.__dict__:
            if c.startswith("on_"):
                data = c.split("_")[1:]

                if len(data) == 2:
                    node, field = data
                    self.fields.append((node, field, self.__getattribute__(c)))
                else:
                    field = data[0]
                    self.client.anon_handlers[field] = self.__getattribute__(c)

    async def wait(self, sub_when_activated: bool = True):
        """
        Wait for mainloop to start.

        Can be used when running client mainloop and main code with asyncio.gather
        """

        await self.client._is_running.wait()
        await self.client._is_sended_credentials.wait()

        if sub_when_activated:
            await self.sub()

    async def sub(self):
        """
        Subscribe to provided topic handlers
        """

        for node, field, handler in self.fields:
            await self.client.subscribe(node, field, handler)

    async def run(self):
        await self.client.mainloop()

    async def topic(self, field: str, datatype: NamedComposedDatatype | type[Datatype]):
        await self.client.post(field, b"")
        return AsyncTopic(field, datatype, self.client.post)

    async def anon(
        self, node: str, field: str, data: bytes, force_to_tcp: bool = False
    ):
        await self.client.anon(node, field, data, force_to_tcp)
