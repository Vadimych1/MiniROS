# AsyncROSClient
ROS client interface with async and distributed service support 

### Args
- name: str - UNIQUE name of the node. 3 symbols
- ip: str - MiniROS server IP address
- port: int - MiniROS server port

### run
Runs mainloop. There is two recommended situations to use:

1. If you`re not supposed to run any code outside AsyncROSClient:
```python
import asyncio
from miniros import AsyncROSClient


class MyROSClient(AsyncROSClient):
    ...


async def main():
    client = MyROSClient()
    await asyncio.gather(
        client.run(),
        
        # waits for mainloop to start and then 
        # subscribes to MyROSClient handlers
        client.wait(),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

2. If you want to run some code paralelly (e.g. send anon data to topic):
```python
import asyncio
from miniros import AsyncROSClient


class MyROSClient(AsyncROSClient):
    ...


async def main():
    client = MyROSClient()

    async def run():
        await client.wait()

        ... # your code

    await asyncio.gather(
        client.run(),
        run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### topic
Creates new topic and returns AsyncTopic interface
- field: str - field name
- datatype: Datatype - type of data (subclass of miniros.datatypes.Datatype). 
Only your-client-side (use miniros.decorators.parsedata(Datatype) on other client)

Must be awaited

### anon
Sends anon message to specified client on specified field
- node: str - node name
- field: str - field name
- data: bytearray - encoded data to send

Must be awaited