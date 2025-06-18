from .circuit import Circuit
from . import messages
from . import httpclient
from . import llsd
from .eventtarget import EventTarget

class Simulator(EventTarget):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.host = None
        self.circuit = None
        self.region = None
        self.caps = {}
        self.messageTemplate = messages.getDefaultTemplate()
    
    async def connect(self, host, circuitCode):
        self.host = host
        self.circuit = await Circuit.create(host)
        self.circuit.on("message", self.handleMessage)
        msg = self.messageTemplate.getMessage("UseCircuitCode")
        msg.CircuitCode.Code = circuitCode
        msg.CircuitCode.SessionID = self.agent.sessionId
        msg.CircuitCode.ID = self.agent.agentId
        self.circuit.send(msg, True)
    
    def send(self, msg, reliable = False):
        self.circuit.send(msg, reliable)
    
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
            msg = self.messageTemplate.getMessage("RegionHandshakeReply")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.RegionInfo.Flags = 2
            self.send(msg, True)
    
    def handleMessage(self, addr, body):
        # Reject unknown hosts as a security precaution
        if addr != self.host:
            print("REJECT")
            return
        
        msg = self.messageTemplate.loadMessage(body)
        self.handleSystemMessages(msg)
        self.fire("message", msg)
    
    async def fetchCapabilities(self, seed):
        pass
    