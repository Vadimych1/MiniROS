from asyncio import Queue, QueueEmpty

class LatestQueue:
    def __init__(self) -> None:
        self.queue = Queue(1)
        
    async def put(self, item):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            
            except QueueEmpty:
                break
        
        await self.queue.put(item)
        
    async def get(self):
        return await self.queue.get()