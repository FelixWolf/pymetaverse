import asyncio
import struct
import math
import random
import datetime
import uuid
from .eventtarget import EventTarget
from . import login
from . import viewer as Viewer
from .const import *

import logging
logger = logging.getLogger(__name__)

class SimpleBot(EventTarget):
    def __init__(self):
        super().__init__()
        self.agent = Viewer.Agent()
        self.agent.on("Message", self.handleMessage)
        self.agent.on("Event", self.handleEvent)
        self.lastAgentUpdate = None
    
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

            self.agentUpdate()
            self.updateAnimations({
                ANIM_AGENT_DO_NOT_DISTURB: False,
                ANIM_AGENT_LAND: False,
                ANIM_AGENT_STAND: True,
                ANIM_AGENT_STAND_1: False,
                ANIM_AGENT_STAND_2: False,
                ANIM_AGENT_STAND_3: False,
                ANIM_AGENT_STAND_4: False
            })

        elif message.name == "ImprovedInstantMessage":
            await self.fire("InstantMessage",
                message.MessageBlock.ID,
                message.AgentData.AgentID,
                message.MessageBlock.FromAgentName.decode(),
                message.MessageBlock.Message.decode(),
                message.MessageBlock.Offline == 1,
                message.MessageBlock.BinaryBucket,
                message.MessageBlock.Dialog,
                datetime.datetime.fromtimestamp(message.MessageBlock.Timestamp)
            )

    async def handleSystemEvent(self, sim, name, body):
        if name == "ChatterBoxInvitation":
            if "instantmessage" in body:
                im = body["instantmessage"]["message_params"]
                await sim.capabilities["ChatSessionRequest"].acceptInvitation(im["id"])
                await self.fire("InstantMessage",
                    im["id"],
                    im["from_id"],
                    im["from_name"],
                    im["message"],
                    im["offline"] == 1,
                    im["data"]["binary_bucket"],
                    IM_SESSION_INVITE,
                    datetime.datetime.fromtimestamp(im["timestamp"])
                )
            
    @property
    def simulator(self):
        return self.agent.simulator
    
    @property
    def messageTemplate(self):
        return self.agent.messageTemplate
    
    async def handleEvent(self, sim, name, body):
        await self.handleSystemEvent(sim, name, body)
        await self.fire("Event", sim, name, body, name=name)

    async def handleMessage(self, simulator, message):
        await self.handleSystemMessages(simulator, message)
        await self.fire("Message", simulator, message, name=message.name)
    
    def send(self, message, reliable = False):
        self.agent.send(message, reliable)
    
    async def login(self, *args, **kwargs):
        loginHandle = await login.Login(*args, **kwargs, isBot = True)
        if loginHandle["login"] == "false":
            logger.critical("Login failure: {}".format(loginHandle["message"]))
            raise ValueError("Incorrect username or password")
        
        logger.info("Login success: {}".format(loginHandle["message"]))
        
        await self.agent.login(loginHandle)
    
    async def run(self):
        bot_tasks = asyncio.create_task(self._bot_tasks())
        
        try:
            await self.agent.run()
        finally:
            bot_tasks.cancel()
            try:
                await bot_tasks
            except asyncio.CancelledError:
                pass

    async def _bot_tasks(self):
        while True:
            await asyncio.sleep(1)
            if self.lastAgentUpdate:
                self.send(self.lastAgentUpdate)
    
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
    
    def sendIM(self, sessionId, destination, message = None,
                dialog = IM_NOTHING_SPECIAL, binaryBucket = None):
        msg = self.messageTemplate.getMessage("ImprovedInstantMessage")
        msg.AgentData.AgentID = self.agent.agentId
        msg.AgentData.SessionID = self.agent.sessionId
        msg.MessageBlock.ToAgentID = destination
        msg.MessageBlock.Offline = IM_ONLINE
        msg.MessageBlock.Dialog = dialog
        msg.MessageBlock.ID = sessionId
        msg.MessageBlock.FromAgentName = "{} {}".format(*self.agent.username).encode() + b"\0"
        msg.MessageBlock.Message = (message or "").encode() + b"\0"
        msg.MessageBlock.BinaryBucket = binaryBucket or b""
        self.send(msg)

    def updateAnimations(self, animations, eventList = None):
        msg = self.messageTemplate.getMessage("AgentAnimation")
        msg.AgentData.AgentID = self.agent.agentId
        msg.AgentData.SessionID = self.agent.sessionId
        for i, (animation, state) in enumerate(animations.items()):
            if type(animation) != uuid.UUID:
                animation = uuid.UUID(animation)
            
            msg.AnimationList[i].AnimID = animation
            msg.AnimationList[i].StartAnim = state
        
        if eventList == None:
            eventList = [b""]
        
        for i, v in enumerate(eventList):
            msg.PhysicalAvatarEventList[i].TypeData = v
        
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
        self.lastAgentUpdate = msg