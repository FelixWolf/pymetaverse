import asyncio
import struct
import math
import random
from .eventtarget import EventTarget
from . import login
from . import viewer as Viewer
from .const import *

class SimpleBot(EventTarget):
    def __init__(self):
        super().__init__()
        self.agent = Viewer.Agent()
        self.agent.on("message", self.handleMessage)
    
    async def handleSystemMessages(self, simulator, message):
        # We only really care about the parent simulator here
        if simulator == self.simulator:
            pass
        
        if message.name == "RegionHandshake":
            # Send some stuff to make the simulator happy about our presence
            msg = self.messageTemplate.getMessage("AgentThrottle")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.AgentData.CircuitCode = self.agent.circuitCode
            msg.Throttle.GenCounter = 0
            msg.Throttle.Throttles = struct.pack("<7f",
                #http://wiki.secondlife.com/wiki/AgentThrottle
                150000,  #Resend
                170000,  #Land
                34000,   #Wind
                34000,   #Cloud
                446000,  #Task
                446000,  #Texture
                220000   #Asset
            )
            self.send(msg)
            
            msg = self.messageTemplate.getMessage("AgentFOV")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.AgentData.CircuitCode = self.agent.circuitCode
            msg.FOVBlock.GenCounter = 0
            msg.FOVBlock.VerticalAngle = 6.233185307179586
            self.send(msg)
            
            msg = self.messageTemplate.getMessage("AgentHeightWidth")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.AgentData.CircuitCode = self.agent.circuitCode
            msg.HeightWidthBlock.GenCounter = 0
            msg.HeightWidthBlock.Height = 0xffff
            msg.HeightWidthBlock.Width = 0xffff
            self.send(msg)
            
    
    @property
    def simulator(self):
        return self.agent.simulator
    
    @property
    def messageTemplate(self):
        return self.agent.messageTemplate
    
    async def handleMessage(self, simulator, message):
        self.agentUpdate()
        await self.handleSystemMessages(simulator, message)
        await self.fire("message", simulator, message, name=message.name)
    
    def send(self, message, reliable = False):
        self.agent.send(message, reliable)
    
    
    async def login(self, username, password):
        loginHandle = await login.Login(username, password, isBot = True)
        if loginHandle["login"] == False:
            raise ValueError("Incorrect username or password")
        
        await self.agent.login(loginHandle)
    
    async def run(self):
        await self.agent.run()
    
    def logout(self):
        self.agent.logout()
    
    def say(self, channel, message, ctype = CHAT_TYPE_NORMAL):
        if channel >= 0:
            msg = self.messageTemplate.getMessage("ChatFromViewer")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.ChatData.Message = message.encode() + b"\0"
            msg.ChatData.Type = ctype
            msg.ChatData.Channel = channel
            self.send(msg)
        
        else:
            # Because ChatFromViewer.Message.Channel is a signed int, we have
            # to use dialogs here
            msg = self.messageTemplate.getMessage("ScriptDialogReply")
            msg.AgentData.AgentID = self.agent.agentId
            msg.AgentData.SessionID = self.agent.sessionId
            msg.Data.ObjectID = self.agent.agentId
            msg.Data.ChatChannel = channel
            msg.Data.ButtonIndex = 0
            msg.Data.ButtonLabel = message.encode() + b"\0"
            self.send(msg)
            
    
    def agentUpdate(self, controls = 0, forward = 0, state = 0, flags = 0):
        angle_rad = math.radians(forward)
        half_angle = angle_rad / 2

        sin_half = math.sin(half_angle)
        cos_half = math.cos(half_angle)
        
        msg = self.messageTemplate.getMessage("AgentUpdate")
        msg.AgentData.AgentID = self.agent.agentId
        msg.AgentData.SessionID = self.agent.sessionId
        msg.AgentData.BodyRotation = (0.0, 0.0, sin_half, cos_half)
        msg.AgentData.HeadRotation = (0.0, 0.0, sin_half, cos_half)
        msg.AgentData.State = state
        msg.AgentData.CameraCenter = (0, 0, 0)
        msg.AgentData.CameraAtAxis = (0, 0.999999, 0)
        msg.AgentData.CameraLeftAxis = (0.999999, 0, 0)
        msg.AgentData.CameraUpAxis = (0, 0, 0.999999)
        msg.AgentData.Far = math.inf
        msg.AgentData.ControlFlags = controls
        msg.AgentData.Flags = flags
        self.send(msg)