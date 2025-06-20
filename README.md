[![License](https://img.shields.io/pypi/l/pymetaverse.svg)](https://pypi.python.org/pypi/pymetaverse/)
[![PyPI version shields.io](https://img.shields.io/pypi/v/pymetaverse.svg)](https://pypi.python.org/pypi/pymetaverse/)

# PyMetaverse
A library for connecting to Second Life, OpenSimulator, or other compatible grids.

# Simple bot example
```py
import asyncio
import datetime
from pymetaverse import login
from pymetaverse.bot import SimpleBot
from pymetaverse.const import *

bot = SimpleBot()

@bot.on("message", name="ChatFromSimulator")
def ChatFromSimulator(simulator, message):
    # Ignore start / stop
    if message.ChatData.ChatType in (4, 5):
        return
    
    sender = message.ChatData.FromName.rstrip(b"\0").decode()
    text = message.ChatData.Message.rstrip(b"\0").decode()
    
    if text == "logout":
        bot.say(0, "Ok!")
        bot.logout()
        
    print("[{}] {}: {}".format(
        datetime.datetime.now().strftime("%Y-%M-%d %H:%m:%S"),
        sender,
        text
    ))

async def main():
    await bot.login(("Example", "Resident"), "password")
    await bot.run()

# Run everything
asyncio.run(main())
```

# Similar Projects
* Second Life Viewer (C++) - https://github.com/secondlife/viewer
* LibreMetaverse (C#) - https://github.com/cinderblocks/libremetaverse
* Node Metaverse (NodeJS) - https://github.com/CasperTech/node-metaverse