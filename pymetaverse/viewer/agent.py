import asyncio
import struct

from ..eventtarget import EventTarget
from .simulator import Simulator
from . import messages

import logging
logger = logging.getLogger(__name__)

sHandle = struct.Struct("<II")
sIP = struct.Struct("<BBBB")

class Agent(EventTarget):
    def __init__(self):
        super().__init__()
        self.agentId = None
        self.sessionId = None
        self.secureSessionId = None
        self.circuitCode = None
        self.simulator = None
        self.simulators = []
        self.messageTemplate = messages.getDefaultTemplate()
    
    async def addSimulator(self, handle, host, circuit, caps = None, parent = False):
        logger.debug(f"Connecting to {host} with circuit {circuit}")
        sim = Simulator(self)
        await sim.connect(host, circuit)
        self.simulators.append(sim)
        
        if caps:
            await sim.fetchCapabilities(caps)
        
        if parent:
            self.simulator = sim
        
        sim.on("message", self.handleMessage)
        sim.on("event", self.handleEvent)
        return sim
    
    def send(self, msg, reliable):
        if self.simulator:
            self.simulator.send(msg, reliable)
    
    async def handleMessage(self, sim, msg):
        if msg.name == "DisableSimulator":
            sim.close()
            if sim == self.simulator:
                self.simulator = None
            
            if sim in self.simulators:
                self.simulators.remove(sim)
        
        elif msg.name == "LogoutReply" or msg.name == "KickUser":
            for simulator in self.simulators:
                simulator.close()
                self.simulators.remove(simulator)
            self.simulator = None
            await self.fire("logout")
        
        await self.fire("message", sim, msg)
    
    async def handleEvent(self, sim, name, body):
        if name == "EnableSimulator":
            simulatorInfo = body["SimulatorInfo"][0]
            handle = struct.unpack("<II", simulatorInfo["Handle"])
            host = "{}.{}.{}.{}".format(*sIP.unpack(simulatorInfo["IP"]))
            await self.addSimulator(
                handle,
                (host, simulatorInfo["Port"]),
                self.circuitCode
            )
        
        elif name == "TeleportFinish":
            info = body["Info"][0]
            handle = struct.unpack("<II", info["RegionHandle"])
            host = "{}.{}.{}.{}".format(*sIP.unpack(info["SimIP"]))
            await self.addSimulator(
                handle,
                (host, info["SimPort"]),
                self.circuitCode,
                info["SeedCapability"],
                True
            )
            msg = self.messageTemplate.getMessage("CompleteAgentMovement")
            msg.AgentData.AgentID = self.agentId
            msg.AgentData.SessionID = self.sessionId
            msg.AgentData.CircuitCode = self.circuitCode
            self.send(msg, True)
        
        elif name == "CrossedRegion":
            CrossedRegion = body["CrossedRegion"][0]
            handle = struct.unpack("<II", CrossedRegion["RegionData"][0]["RegionHandle"])
            host = "{}.{}.{}.{}".format(*sIP.unpack(CrossedRegion["RegionData"][0]["SimIP"]))
            await self.addSimulator(
                handle,
                (host, CrossedRegion["RegionData"][0]["SimPort"]),
                self.circuitCode,
                CrossedRegion["RegionData"][0]["SeedCapability"],
                True
            )
            msg = self.messageTemplate.getMessage("CompleteAgentMovement")
            msg.AgentData.AgentID = self.agentId
            msg.AgentData.SessionID = self.sessionId
            msg.AgentData.CircuitCode = self.circuitCode
            self.send(msg, True)
        
        elif name == "EstablishAgentCommunication":
            host = body["sim-ip-and-port"].split(":", 1)
            host = (host[0], int(host[1]))

            for simulator in self.simulators:
                if simulator.host == host:
                    await simulator.fetchCapabilities(body["seed-capability"])
                    break
            
            else:
                logger.warning(f"Received EstablishAgentCommunication for unknown host {host}")
        
        await self.fire("event", sim, name, body)
    
    async def login(self, login):
        if login["login"] == False:
            raise ValueError("Invalid login handle")
        
        self.agentId = login["agent_id"]
        self.sessionId = login["session_id"]
        self.secureSessionId = login["secure_session_id"]
        self.circuitCode = login["circuit_code"]
        
        await self.addSimulator(
            (login["region_x"], login["region_y"]),
            (login["sim_ip"], login["sim_port"]),
            self.circuitCode,
            login["seed_capability"],
            True
        )
        
        msg = self.messageTemplate.getMessage("CompleteAgentMovement")
        msg.AgentData.AgentID = self.agentId
        msg.AgentData.SessionID = self.sessionId
        msg.AgentData.CircuitCode = self.circuitCode
        self.send(msg, True)
    
    def logout(self):
        msg = self.messageTemplate.getMessage("LogoutRequest")
        msg.AgentData.AgentID = self.agentId
        msg.AgentData.SessionID = self.sessionId
        self.send(msg, True)
    
    async def run(self):
        while True:
            try:
                if not self.simulator:
                    break

                await asyncio.sleep(0.1)
            
            except asyncio.exceptions.CancelledError:
                # Attempt to gracefully logout
                self.logout()
        