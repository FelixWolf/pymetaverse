from ..eventtarget import EventTarget
from .simulator import Simulator
from . import messages
import asyncio

class Agent(EventTarget):
    def __init__(self):
        super().__init__()
        self.simulator = None
        self.simulators = []
        self.messageTemplate = messages.getDefaultTemplate()
        self.circuitCode = None
    
    async def addSimulator(self, host, circuit, caps = None, parent = False):
        sim = Simulator(self)
        await sim.connect(host, circuit)
        self.simulators.append(sim)
        
        if caps:
            await sim.fetchCapabilities(caps)
        
        if parent:
            self.simulator = sim
        
        sim.on("message", self.handleMessage)
        
        return sim
    
    def send(self, msg, reliable):
        if self.simulator:
            self.simulator.send(msg, reliable)
    
    def handleMessage(self, sim, msg):
        self.fire("message", sim, msg)
    
    @classmethod
    async def fromLogin(cls, login):
        self = cls()
        
        if login["login"] == False:
            raise ValueError("Invalid login handle")
        
        self.agentId = login["agent_id"]
        self.sessionId = login["session_id"]
        self.secureSessionId = login["secure_session_id"]
        self.circuitCode = login["circuit_code"]
        
        await self.addSimulator((login["sim_ip"], login["sim_port"]), self.circuitCode, login["seed_capability"], True)
        
        msg = self.messageTemplate.getMessage("CompleteAgentMovement")
        msg.AgentData.AgentID = self.agentId
        msg.AgentData.SessionID = self.sessionId
        msg.AgentData.CircuitCode = self.circuitCode
        self.send(msg, True)
        
        return self
    
    async def run(self):
        while True:
            await asyncio.sleep(5)
            if self.simulator == None:
                break
        