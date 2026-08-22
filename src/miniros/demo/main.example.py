from miniros import AsyncROSClient, datatypes, aparsedata
import asyncio, sys


# this is basic setup for your MiniROS client class.
# always override client's name when calling super().__init__()
class SenderClient(AsyncROSClient):
    def __init__(self, ip="localhost", port=3000, _parse_handlers=True):
        super().__init__("sender", ip, port, _parse_handlers)


class ReceiverClient(AsyncROSClient):
    def __init__(self, ip="localhost", port=3000, _parse_handlers=True):
        super().__init__("receiver", ip, port, _parse_handlers)

    # MiniROS uses class functions to handle data
    # naming is important: if you will name your
    # function wrong, it will not receive any data
    # - for topics: on_<node>_<topic>(self, data)
    # - for anon messages: on_<anon_path>(self, data, sender)
    # do not use any other underscores, things may break
    #
    # `aparsedata` is an asynchronous decorator for data
    # handlers. it automatically converts `bytes` into
    # readable datatype, like `str`, `int` or `numpy.ndarray`
    # see more about datatypes at `MiniROS/docs/datatypes`
    #
    # this is a topic data handler
    @aparsedata(datatypes.String)
    async def on_sender_data(self, data: str):
        print(f"[topic] got data: {data}")

    # and this is an anon data handler
    @aparsedata(datatypes.Int)
    async def on_counter(self, data: int, node: str):
        print(f"[anon] got data from node {node}: {data}")
        
        # termination signal
        if data == -1:
            # graceful backend shutdown
            await self.stop()


# MiniROS uses asyncio API for fast and reliable data transferring
# never run code that could block event loop in the same thread
# as the MiniROS
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
                # send anon message. auto encoding is not implemented
                # now, so you may need to encode manually
                #
                # set force_to_tcp=True if you are getting exceptions or
                # encountering high data loss
                await client.anon("receiver", "counter", datatypes.Int.encode(i))
            
            # add delay
            await asyncio.sleep(0.5)
        
        # send termination signal to the receiver
        await client.anon("receiver", "counter", datatypes.Int.encode(-1))
        
        # graceful backend shutdown
        await client.stop()

    # this call makes asyncio run your code
    # and MiniROS backend simultaneously
    await asyncio.gather(client.run(), run())


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
