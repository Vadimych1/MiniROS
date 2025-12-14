from .base import UnitTest, fail_test, pass_test, check_pass
from miniros import AsyncROSClient
from miniros import datatypes
import asyncio

class AuthTest(UnitTest):
    async def test(self):
        client = AsyncROSClient("test")
        
        async def wait():
            await asyncio.sleep(1)
            
            if client.client._is_running:
                pass_test()
            else:
                fail_test()
            
        try:
            await asyncio.gather(
                client.run(),
                wait()
            )
            
        except Exception as e:
            return check_pass(e)
        
        
class PostTest(UnitTest):
    async def test(self):
        send_data = b'Hello, world!'
        recv_data = b''
        
        class RecvClient(AsyncROSClient):
            def on_send_test(self, data):
                nonlocal recv_data
                recv_data = data       
        
        send_client = AsyncROSClient("send")
        receive_client = RecvClient("recv")
        
        async def wait():
            await send_client.wait()
            t = await send_client.topic("test", datatypes.Bytes)
            
            await receive_client.wait()
            await asyncio.sleep(0.1)

            await t.post(send_data)
            
            await asyncio.sleep(1)
            
            if send_data == recv_data:
                pass_test()
            else:
                fail_test()
        
        async def run_receive():
            await send_client.wait()
            await receive_client.run()
        
        try:   
            await asyncio.gather(send_client.run(), run_receive(), wait())
            
        except Exception as e:
            return check_pass(e)

class AnonTest(UnitTest):
    async def test(self):
        send_data = b'Hello, world!'
        recv_data = b''
        
        class RecvClient(AsyncROSClient):
            def on_test(self, data, node):
                nonlocal recv_data
                recv_data = data
                
        send_client = AsyncROSClient("peer1")
        recv_client = RecvClient("peer2")

        async def wait():
            await send_client.wait()
            await recv_client.wait()
            
            await asyncio.sleep(0.1)
            
            await send_client.anon("peer2", "test", send_data)
            
            await asyncio.sleep(1)
            
            if send_data == recv_data:
                pass_test()
            else:
                fail_test()
            
        try:   
            await asyncio.gather(send_client.run(), recv_client.run(), wait())
            
        except Exception as e:
            return check_pass(e)
