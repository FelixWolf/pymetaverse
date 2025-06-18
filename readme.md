# Second Life viewer in python
```py
import asyncio
import json
from pymetaverse import login
from pymetaverse.agent import Agent

async def main():
    # Set argument isBot = False if human
    loginHandle = await login.Login(username=("firstname", "lastname"), password="A secret to everyone")
    
    agent = await Agent.fromLogin(loginHandle)
    @agent.on("message")
    def handleMessage(simulator, message):
        print(simulator, message)
    
    await agent.run()

asyncio.run(main())
```