import asyncio
from ..util.sock import TCPSockAsyncServer as SockServer
# from ..util.sock import UDPSockServer as SockServer # UNSTABLE

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] > %(message)s")

async def run(host, port):
    s = SockServer(host, port)
    return await s.run()

if __name__ == "__main__":
    asyncio.run(run("localhost", 3000))