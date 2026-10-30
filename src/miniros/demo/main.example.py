from miniros import AsyncROSClient, datatypes, aparsedata
import asyncio, sys


# this is basic setup for your MiniROS client class.
# always override client's name when calling super().__init__()
#
# MiniROS has naming module (from miniros import naming), which
# provides some descriptive names of Nodes and Topics you should use
class SenderClient(AsyncROSClient):
    def __init__(self, ip="localhost", port=3000):
        super().__init__("sender", ip, port)

class ReceiverClient(AsyncROSClient):
    def __init__(self, ip="localhost", port=3000):
        super().__init__("receiver", ip, port)
        
        # subscribe to topics
        # always do this in initializer or before calling client.wait(),
        # otherwise MiniROS wont process these handlers
        self.add_topic_handler(self.on_sender_data, "sender", "data")
        self.add_anon_handler(self.counter_handler, "counter")

    # you can enable automatic topic and anon handler parsing using:
    #
    # ```
    # import miniros.util.options as opts
    # opts.enable_on_handlers()
    # ```
    #
    # then your topic and anon handler names SHOULD look like this:
    # `async def on_{node}_{topic}(self, data)` - for topics
    # `async def on_{anon_field}` - for anon handlers
    # 
    # note that this does not disable `add_topic_handler` and `add_anon_handler`
    # adding handlers with them will work as well

    # because we are adding handlers manually
    # they can be named as we want
    #
    # recommended descriptive name guideline is
    # `type-of-data_handler`, for example:
    # - `odometry_handler`
    # - `slam_pose_handler`
    # - `rtc_change_handler`
    
    # this can used with `enable_on_handlers`
    @aparsedata(datatypes.String)
    async def on_sender_data(self, data: str):
        print(f"[topic] got data: {data}")

    # this will work too, but handler should be added manually
    @aparsedata(datatypes.Int)
    async def counter_handler(self, data: int, node: str):
        print(f"[anon] got data from node {node}: {data}")
        
        # termination signal
        if data == -1:
            # graceful backend shutdown
            await self.stop()


# MiniROS uses asyncio API for fast and reliable data transferring
# never run code that could block event loop in the same thread
# as the MiniROS (use asyncio.to_thread or loop.run_in_executor for heavy work)
async def run_sender():
    client = SenderClient()

    async def run():
        # this line does two things:
        # 1. waits for `client` to connect
        # 2. subscribes to topics that were specified
        # at class creation
        await client.wait()

        # topic creation. you need to specify topic
        # name and it's datatype for auto encoding
        data_topic = await client.topic("data", datatypes.String)

        for i in range(20):
            # post data to topic
            await data_topic.post(f"{i}. Hello, world!")

            if i % 3 == 0:
                # send anon message; encode it manually
                await client.anon("receiver", "counter", datatypes.Int.encode(i))
            
            # add delay
            await asyncio.sleep(0.5)
        
        # send termination signal to the receiver
        await client.anon("receiver", "counter", datatypes.Int.encode(-1))
        
        # graceful backend shutdown
        await client.stop()
    
    # always ensure that you are running background tasks using asyncio.create_task
    # otherwise MiniROS receiver loop could be blocked
    run_task = asyncio.create_task(run())

    # run code and MiniROS backend simultaneously
    await asyncio.gather(client.run(), run_task)


async def run_receiver():
    client = ReceiverClient()

    # even if you do not run any code you should call
    # client.wait() to ensure topic subscription
    await asyncio.gather(client.wait(), client.run())

# code below is demo-only. in production you
# should write something like this:
# if __name__ == "__main__":
#     asyncio.run(run_sender())
#
# before running your package, start server with
# `miniros server`
#
# start receiver first, otherwise some packets may be lost
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: main.py [sender, receiver]")

    elif sys.argv[1] == "sender":
        asyncio.run(run_sender())

    elif sys.argv[1] == "receiver":
        asyncio.run(run_receiver())

    else:
        print(f"usage: main.py [sender, receiver]")
