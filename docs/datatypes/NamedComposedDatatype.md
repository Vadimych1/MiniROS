# NamedComposedDatatype
Pure-Python analog of Protobuf

## Usage example
Using NamedComposedDatatype is quite simple:
```python
from miniros import *

# UInt, Movement, Vector and Dict are built-in MiniROS datatypes
# See how to create your own datatype at `docs/Datatype.md`
RobotComposedDT = NamedComposedDatatype({
    "id": UInt,
    "pose": Movement,
    "score_vector": Vector,
    "meta": Dict
})

myData = RobotComposedDT(
    id = 11,
    pose = Movement(
        Vector(1, 2, 3),
        Vector(4, 5, 6),
    )
    score_vector = Vector(10, 0, 0),
    meta = {"name": "my_best_robot", "workspace": "vbot"}
)

print(myData.id) # 11

myData.meta = {"name": "new_robot"}
print(myData.meta) # {"name": "new_robot"}

myData.some_undefined_var = 0 # AttributeError
print(myData.some_undefined_var) # AttributeError
```

**Note:** you can create a new instance of your composed datatype with no arguments. It will have no values and you wont be able to encode it until you set all attributes that were specified on datatype creation

After NamedComposedDatatype creation you can use it as a plain MiniROS datatype. This example uses datatype from previous code snippet

Receiver node:
```python
from miniros import AsyncROSClient, aparsedata
import asyncio

class MyClient(AsyncROSClient):
    def __init__(self, ip="localhost", port="3000"):
        super().__init__("receiver", ip, port)

    @aparsedata(RobotComposedDT)
    def on_sender_newdata(self, data):
        print(f"Got new message:", data)

if __name__ == "__main__":
    client = MyClient()
    asyncio.run(client.run())
```

Sender node:
```python
from miniros import AsyncROSClient
import asyncio

async def main():
    client = AsyncROSClient(name="sender")

    async def run():
        await client.wait()

        newdata_topic = await client.topic("newdata", RobotComposedDT)

        while True:
            await asyncio.sleep(1)
            await newdata_topic.post(
                RobotComposedDT(
                    id = 11,
                    pose = Movement(
                        Vector(1, 2, 3),
                        Vector(4, 5, 6),
                    )
                    score_vector = Vector(10, 0, 0),
                    meta = {"name": "my_best_robot", "workspace": "vbot"}
                )
            )

    await asyncio.gather(
        run(),
        client.run()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

