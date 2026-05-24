import pytest
import asyncio
from miniros import AsyncROSClient, datatypes
from miniros.base.server import AsyncDistributedServer


@pytest.fixture
async def miniros_server(unused_tcp_port):
    host, port = "localhost", unused_tcp_port
    server = AsyncDistributedServer(host, port)

    task = asyncio.create_task(server.run())

    await server.wait()

    yield host, port

    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_server_running(miniros_server):
    host, port = miniros_server

    client = AsyncROSClient(
        "test-client",
        ip=host,
        port=port,
    )

    async def _test():
        await client.wait()

    client_task = asyncio.create_task(client.run())
    await asyncio.sleep(0.1)

    await asyncio.wait_for(_test(), timeout=2)

    client_task.cancel()

    try:
        await client_task

    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_post(miniros_server):
    host, port = miniros_server
    send_data = b"hello, world!"
    got_result_event = asyncio.Event()

    # sender
    class Client1(AsyncROSClient):
        def __init__(self, ip=host, port=port, _parse_handlers=True):
            super().__init__("client1", ip, port, _parse_handlers)

    # receiver
    class Client2(AsyncROSClient):
        def __init__(self, ip=host, port=port, _parse_handlers=True):
            super().__init__("client2", ip, port, _parse_handlers)

        async def on_client1_data(self, data: bytes):
            assert data == send_data
            got_result_event.set()

    client1 = Client1()
    client2 = Client2()

    client1_task = asyncio.create_task(client1.run())
    client2_task = asyncio.create_task(client2.run())
    result_event = asyncio.create_task(got_result_event.wait())

    await asyncio.sleep(0.1)

    async def _test():
        await client1.wait()
        await client2.wait()

        await asyncio.sleep(0.3)

        topic = await client1.topic("data", datatypes.Bytes)
        await topic.post(send_data)

    try:
        await asyncio.wait_for(_test(), timeout=2)
        await asyncio.wait_for(result_event, timeout=2)

    finally:
        client1_task.cancel()
        client2_task.cancel()
        result_event.cancel()

        try:
            await client1_task

        except asyncio.CancelledError:
            pass

        try:
            await client2_task

        except asyncio.CancelledError:
            pass

        try:
            await result_event

        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_anon(miniros_server):
    host, port = miniros_server
    send_data = b"hello, world!"
    got_result_event = asyncio.Event()

    # sender
    class Client1(AsyncROSClient):
        def __init__(self, ip=host, port=port, _parse_handlers=True):
            super().__init__("client1", ip, port, _parse_handlers)

    # receiver
    class Client2(AsyncROSClient):
        def __init__(self, ip=host, port=port, _parse_handlers=True):
            super().__init__("client2", ip, port, _parse_handlers)

        async def on_data(self, data: bytes, sender: str):
            assert data == send_data
            assert sender == "client1"

            got_result_event.set()

    client1 = Client1()
    client2 = Client2()

    client1_task = asyncio.create_task(client1.run())
    client2_task = asyncio.create_task(client2.run())
    result_event = asyncio.create_task(got_result_event.wait())

    await asyncio.sleep(0.1)

    async def _test():
        await client1.wait()
        await client2.wait()

        await asyncio.sleep(0.3)

        await client1.anon(
            "client2", "data", send_data, force_to_tcp=True
        )  # forced tcp for now

    try:
        await asyncio.wait_for(_test(), timeout=2)
        await asyncio.wait_for(result_event, timeout=2)

    finally:
        client1_task.cancel()
        client2_task.cancel()
        result_event.cancel()

        try:
            await client1_task

        except asyncio.CancelledError:
            pass

        try:
            await client2_task

        except asyncio.CancelledError:
            pass

        try:
            await result_event

        except asyncio.CancelledError:
            pass
