import asyncio
from ..eventtarget import EventTarget

class EventQueue(EventTarget):
    def __init__(self, simulator):
        super().__init__()
        self.simulator = simulator
        self.sequence = 0
        self.task = None
    
    async def handleEvent(self, event):
        await self.fire("event", event["message"], event["body"])

    async def run(self):
        while True:
            if not "EventQueueGet" in self.simulator.capabilities:
                await asyncio.sleep(0.1)
            
            ack, events = await self.simulator.capabilities["EventQueueGet"].poll(self.sequence, False)
            if ack == None:
                return
            
            for event in events:
                await self.handleEvent(event)
            
            self.sequence = ack
    
    def start(self, loop = None):
        loop = loop or asyncio.get_running_loop()
        if self.task:
            self.task.cancel()
        self.task = loop.create_task(self.run())
        
    def close(self):
        if self.task:
            self.task.cancel()