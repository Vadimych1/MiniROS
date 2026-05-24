import asyncio
from miniros.util.src.sock import AsyncDistributedServer

import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] > %(message)s"
)


async def run(host, port):
    s = AsyncDistributedServer(host, port)
    return await s.run()


if __name__ == "__main__":
    asyncio.run(run("localhost", 3000))
