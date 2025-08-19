#!/usr/bin/env python3
import sys
import hashlib
import uuid #For Mac addresses
import socket #For Host ID
from . import httpclient
from . import llsd

import logging
logger = logging.getLogger(__name__)

def getMacAddress():
    mac = uuid.getnode()
    return ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))

def getPlatform():
    if sys.platform == "linux" or sys.platform == "linux2":
       return "Lnx"

    elif sys.platform == "darwin":
        return "Mac"

    elif sys.platform == "win32":
        return "Win"
    
    return "Unk"

#Convenience name
OPTIONS_NONE = []

#Enough to get us most capability out of the grid without restrictions
OPTIONS_MINIMAL = [
    "adult_compliant",
]

#Normal stuff
OPTIONS_MOST = [
    "inventory-root",
    
    "inventory-lib-root",
    "inventory-lib-owner",

    "display_names",
    "adult_compliant",

    "advanced-mode",
    
    "max_groups",
    "max-agent-groups",
    "map-server-url",
    "login-flags",
]

#This may take longer to log in
OPTIONS_FULL = [
    "inventory-root",
    "inventory-skeleton",
    "inventory-meat",
    "inventory-skel-targets",
    
    "inventory-lib-root",
    "inventory-lib-owner",
    "inventory-skel-lib",
    "inventory-meat-lib",

    "wearables",
    "attachments",

    "initial-outfit",
    "gestures",
    "display_names",
    "event_categories",
    "event_notifications",
    "classified_categories",
    "adult_compliant", 
    "buddy-list",
    "newuser-config",
    "ui-config",

    "landmarks",

    "advanced-mode",
    
    "max_groups",
    "max-agent-groups",
    "map-server-url",
    "voice-config",
    "tutorial_setting",
    "login-flags",
    "global-textures",
    #"god-connect", #lol no
]

async def Login(username, password,
          start = "last",
          options = None,
          grid = "https://login.agni.lindenlab.com/cgi-bin/login.cgi",
          isBot = True,
          token = ""
    ):
    
    # Try our hardest to parse whatever we've been previded
    if type(username) == str:
        if "." in username:
            username = username.split(".", 1)
        elif " " in username:
            username = username.split(" ", 1)
        
    if len(username) == 1:
        username = (username[0], "resident")
    
    elif len(username) != 2:
        raise ValueError("Username must be a tuple of firstname and optionally last name")
    
    #WARNING:
    # Falsifying this is a violation of the Terms of Service
    mac = getMacAddress()
    
    platform = getPlatform()
    
    #WARNING:
    # Deviating from this format MAY be a violation of the Terms of Service
    id0 = hashlib.md5("{}:{}:{}".format(
            platform,
            mac,
            sys.version
        ).encode("latin")
    ).hexdigest()
    
    if options == None:
        options = OPTIONS_MOST
    
    # Hash the password if it isn't hashed
    if not password.startswith("$1$"):
        password = "$1$" + hashlib.md5(password.encode("latin")).hexdigest()

    requestBody = llsd.llsdEncode({
        #Credentials
        "first": username[0],
        "last": username[1],
        "passwd": password,
        #"web_login_key": "",
        
        #OS information
        "platform": platform,
        "platform_version": sys.version,
        
        #Viewer information
        "channel": "pymetaverse",
        "version": "Testing", #TODO: Change this to metaverse.__VERSION__
        #"major": 0,
        #"minor": 0,
        #"patch": 0,
        #"build": 0,
        #"viewer_digest": "",
        
        #Machine information
        "host_id": socket.gethostname(),
        "mac": mac, #WARNING: Falsifying this is a violation of the Terms of Service
        "id0": id0, #WARNING: Falsifying this is a violation of the Terms of Service
        
        #Ignore messages for now
        "skipoptional": True,
        "agree_to_tos": True,
        "read_critical": True,
        
        #Viewer options
        "extended_errors": True,
        "options": options,
        "agent_flags": 2 if isBot else 0, #Bitmask, we are a bot, so set bit 2 to true,
        "start": start,
        #"functions": "", #No idea what this does
        
        #Login error tracking
        "last_exec_event": 0,
        #"last_exec_froze": False,
        #"last_exec_duration": 0,
        
        #For proxied connections apparently:
        #"service_proxy_ip": "",
        
        "token": token,
        "mfa_hash": ""
    })
    
    async with httpclient.HttpClient() as session:
        async with await session.post(grid, data = requestBody, headers = {
            "Content-Type": "application/llsd+xml"
        }) as response:
            resp = await response.read()
            # Log the pre-parsed result, just in case the server returns something funky
            logger.debug(f"Received login reply: {resp}")
            return llsd.llsdDecode(resp, format="xml")
        