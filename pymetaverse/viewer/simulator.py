import asyncio
from .circuit import Circuit
from . import messages
from .capability import Capabilities
from . import region
from .. import httpclient
from .. import llsd
from . import eventqueue
from ..eventtarget import EventTarget
import time
import traceback

class Simulator(EventTarget):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.host = None
        self.name = "Unknown Region"
        self.owner = None
        self.id = None
        self.circuit = None
        self.region = None
        self.lastMessage = time.time()
        self.capabilities = {}
        self.pingSequence = 0
        self.pendingPings = {}
        self.eventQueue = eventqueue.EventQueue(self)
        self.eventQueue.on("event", self.handleEvent)
        self.messageTemplate = messages.getDefaultTemplate()
    
    def __del__(self):
        try:
            self.close()
        except RuntimeError:
            pass
    
    def send(self, msg, reliable = False):
        self.circuit.send(msg, reliable)
    
    async def connect(self, host, circuitCode):
        self.host = host
        self.circuit = await Circuit.create(host)
        self.circuit.on("message", self.handleMessage)
        
        msg = self.messageTemplate.getMessage("UseCircuitCode")
        msg.CircuitCode.Code = circuitCode
        msg.CircuitCode.SessionID = self.agent.sessionId
        msg.CircuitCode.ID = self.agent.agentId
        self.send(msg, True)
    
    async def handleSystemMessages(self, msg):
        self.lastMessage = time.time()
        if msg.name == "PacketAck":
            acks = []
            for ack in msg.Packets:
                acks.append(ack.ID)
                
            self.circuit.acknowledge(acks)
        
        elif msg.name == "StartPingCheck":
            msg = self.messageTemplate.getMessage("CompletePingCheck")
            msg.PingID.PingID = msg.PingID.PingID
            self.send(msg)
        
        elif msg.name == "CompletePingCheck":
            if msg.PingID.PingID in self.pendingPings:
                future = self.pendingPings[msg.PingID.PingID]
                if not future.done():
                    future.set_result(False)
                del self.pendingPings[msg.PingID.PingID]
        
        elif msg.name == "RegionHandshake":
            self.name = msg.RegionInfo.SimName.rstrip(b"\0").decode()
            self.owner = msg.RegionInfo.SimOwner
            self.id = msg.RegionInfo2.RegionID
            
            msg = self.messageTemplate.getMessage("RegionHandshakeReply")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.RegionInfo.Flags = 1
            self.send(msg, True)
        
        elif msg.name == "DisableSimulator":
            self.close()
    
    async def handleMessage(self, addr, body):
        # Reject unknown hosts as a security precaution
        if addr != self.host:
            return
        
        msg = self.messageTemplate.loadMessage(body)
        await self.handleSystemMessages(msg)
        
        # Don't break the whole script!
        try:
            await self.fire("message", self, msg, name=msg.name)
        except Exception as e:
            traceback.print_exc()
    
    async def handleEvent(self, name, body):
        try:
            await self.fire("event", self, name, body)
        except Exception as e:
            traceback.print_exc()

    async def fetchCapabilities(self, url = None):
        if "Seed" not in Capabilities:
            return
        
        seed = Capabilities.get("Seed", url)
        self.capabilities = await seed.getCapabilities(Capabilities)
        self.eventQueue.start()

    async def ping(self, timeout = 5.0, forceUsePingCheck = False):
        # If we already have a message within the timeout range,
        # just use that instead. Unless specified otherwise.
        if not forceUsePingCheck and self.lastMessage + timeout > time.time():
            return True
        
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        # If it exists at this point, it's probably not ever going to
        # come in
        if self.pingSequence in self.pendingPings:
            old_future = self.pendingPings[self.pingSequence]
            if not old_future.done():
                old_future.set_result(False)
            del self.pendingPings[self.pingSequence]
        
        msg = self.messageTemplate.getMessage("StartPingCheck")
        msg.PingID.PingID = self.pingSequence

        self.pendingPings[msg.PingID.PingID] = future
        self.pingSequence = (self.pingSequence + 1) & 0xFF

        self.send(msg)

        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            del self.pendingPings[msg.PingID.PingID]
            return False
        
        return True

    def close(self):
        self.eventQueue.close()
        self.circuit.close()

    def __repr__(self):
        return f"<{self.__class__.__name__} \"{self.name}\" ({self.host[0]}:{self.host[1]})>"
    