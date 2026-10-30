from miniros.util.src.sock import AsyncDistributedClient as AsyncSockClient
from miniros.util.datatypes import NamedComposedDatatype, Datatype
from miniros.util.options import on_handlers_enabled
from typing import Callable
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
        post_func: Callable[[str, bytes], Any],
    ):
        self.post_func = post_func
        self.field = field
        self.encoder = encoder

    async def post(self, data: Any) -> None:
        await self.post_func(self.field, bytes(self.encoder.encode(data)))


class AsyncROSClient:
    def __init__(self, name, ip="localhost", port=3000):
        self.name = name
        self.ip = ip
        self.port = port

        self.fields = []

        self.client = AsyncSockClient(ip, port, name)

        self.fields = []
        self.client.anon_handlers = {}

        if on_handlers_enabled():
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
    
    def add_topic_handler(self, handler: Callable, node: str, field: str):
        """
        Adds a topic to subscribe list
        """
        
        t = (node, field, handler)
        if t in self.fields:
            raise ValueError(f"topic handler '{node}:{field}' already registered")
        
        self.fields.append(t)
    
    def add_anon_handler(self, handler: Callable, field: str):
        """
        Adds anon handler to handler map
        """
        
        if field in self.client.anon_handlers:
            raise ValueError(f"anon handler '{field}' already registered")
        
        self.client.anon_handlers[field] = handler

    async def wait(self, sub_when_activated: bool = True):
        """
        Wait for mainloop to start
        
        When `sub_when_activated` is set to `True`: automatically subscribes to added topics (see `add_topic_handler`)
        """

        await self.client._is_running.wait()
        await self.client._is_sent_credentials.wait()

        if sub_when_activated:
            await self.sub()

    async def sub(self):
        """
        Subscribe to provided topic handlers
        """

        for node, field, handler in self.fields:
            await self.client.subscribe(node, field, handler)

    async def run(self):
        """
        Run client mainloop
        """
        
        await self.client.mainloop()

    async def topic(self, field: str, datatype: NamedComposedDatatype | type[Datatype]):
        """
        Create topic and return topic scope for posting
        """
        
        await self.client.create_topic(field)
        return AsyncTopic(field, datatype, self.client.post)

    async def anon(
        self, node: str, field: str, data: bytes, force_to_tcp: bool = False
    ):
        await self.client.anon(node, field, data, force_to_tcp)

    async def stop(self):
        self.client._is_running.clear()
