# superserver
Superserver is MiniROS technology that allows you to connect robot to a higher-level server with built-in tools
To enable superserver you need to:
1. Create an `json` config file, e.g. `superserver.config.json`. It's format specified below:
```json
{
    "ip": "global-server-ip",
    "port": 3000,
    "robot_name": "your-robot-name",
    "on_robot": [
        {
            "from_node": "supermain",
            "from_field": "task",
            
            "to_node": "robotmain",
            "to_field": "task"
        }
    ],
    "on_server": [
        {
            "from_node": "robotmain",
            "from_field": "map",

            "to_node": "supermain",
            "to_field": "map"
        }
    ]
}
```

2. Create handlers on both server and robot. To send data through superserver, you need to create a topic and post data to it. For receiving, create an anon handler with required name
```python
import asyncio

class RobotMainClient(AsyncROSClient):
    def __init__(self, ip="localhost", port=3000):
        super("robotmain", ip, port)

    async def on_task(self, data: bytes, node: str): # handler for {from_node: slam, from_field: main}
        "Handle data"

async def main():
    client = RobotMainClient()

    async def run():
        await client.wait()

        map_topic = client.topic("map") # create a topic to send data through superserver

        "Handle sending"

    await asyncio.gather(
        run(),
        client.run(),
    )

asyncio.run(main())
```

3. All done! Now just run `miniros server --superserver path/to/superserver.config.json` on robot and start plain server on the global computer

*Note: in some cases there are bug with MiniROS:*