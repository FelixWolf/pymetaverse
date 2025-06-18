from .circuit import Circuit
from . import messages
from .. import httpclient
from .. import llsd
from ..eventtarget import EventTarget

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
        self.caps = {}
        self.messageTemplate = messages.getDefaultTemplate()
    
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
    
    def handleSystemMessages(self, msg):
        if msg.name == "PacketAck":
            acks = []
            for ack in msg.Packets:
                acks.append(ack.ID)
                
            self.circuit.acknowledge(acks)
        
        elif msg.name == "StartPingCheck":
            msg = self.messageTemplate.getMessage("CompletePingCheck")
            msg.PingID.PingID = msg.PingID.PingID
            self.send(msg)
        
        elif msg.name == "RegionHandshake":
            self.name = msg.RegionInfo.SimName.rstrip(b"\0").decode()
            self.owner = msg.RegionInfo.SimOwner
            self.id = msg.RegionInfo2.RegionID
            msg = self.messageTemplate.getMessage("RegionHandshakeReply")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.RegionInfo.Flags = 2
            self.send(msg, True)
    
    def handleMessage(self, addr, body):
        # Reject unknown hosts as a security precaution
        if addr != self.host:
            return
        
        msg = self.messageTemplate.loadMessage(body)
        self.handleSystemMessages(msg)
        self.fire("message", self, msg)
    
    async def fetchCapabilities(self, seed):
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__} \"{self.name}\" ({self.host[0]}:{self.host[1]})>"
    