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

import logging
logger = logging.getLogger(__name__)

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
        self.eventQueue.on("Event", self.handleEvent)
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
        self.circuit.on("Message", self.handleMessage)
        
        msg = self.messageTemplate.getMessage("UseCircuitCode")
        msg.CircuitCode.Code = circuitCode
        msg.CircuitCode.SessionID = self.agent.sessionId
        msg.CircuitCode.ID = self.agent.agentId
        self.send(msg, True)
    
    async def handleSystemMessages(self, msg):
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
            logger.debug(f"Received handshake for {self}")
            
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
        
        self.lastMessage = time.time()
        msg = self.messageTemplate.loadMessage(body)
        await self.handleSystemMessages(msg)
        
        # Don't break the whole script!
        try:
            await self.fire("Message", self, msg, name=msg.name)
        except Exception as e:
            traceback.print_exc()
    
    async def handleEvent(self, name, body):
        try:
            await self.fire("Event", self, name, body)
        except Exception as e:
            traceback.print_exc()

    async def fetchCapabilities(self, url = None):
        if "Seed" not in Capabilities:
            return
        
        seed = Capabilities.get("Seed", url)
        self.capabilities = await seed.getCapabilities(Capabilities)
        self.eventQueue.start()

    async def sendAcks(self):
        if len(self.circuit.acks) == 0:
            return False
        
        msg = self.messageTemplate.getMessage("PacketAck")
        for i in range(255):
            if len(self.circuit.acks) > 0:
                msg.Packets[i].ID = self.circuit.acks.pop(0)
            else:
                break
        
        self.send(msg)
        return len(self.circuit.acks) > 0
        

    async def ping(self, timeout = 5.0, forceUsePingCheck = False):
        # If we already have a message within the timeout range,
        # just use that instead. Unless specified otherwise.
        if not forceUsePingCheck and self.lastMessage + timeout > time.time():
            return True
        
        logger.debug(f"Starting ping check for {self}")

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        currentPing = self.pingSequence
        self.pingSequence = (currentPing + 1) & 0xFF

        # If it exists at this point, it's probably not ever going to
        # come in
        if currentPing in self.pendingPings:
            old_future = self.pendingPings[currentPing]
            if not old_future.done():
                old_future.set_result(False)
            del self.pendingPings[currentPing]
        
        msg = self.messageTemplate.getMessage("StartPingCheck")
        msg.PingID.PingID = currentPing

        self.pendingPings[msg.PingID.PingID] = future

        self.send(msg)

        try:
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            if msg.PingID.PingID in self.pendingPings:
                del self.pendingPings[msg.PingID.PingID]
            return False
        
        return True

    def close(self):
        self.eventQueue.close()
        self.circuit.close()

    def __repr__(self):
        return f"<{self.__class__.__name__} \"{self.name}\" ({self.host[0]}:{self.host[1]})>"
    