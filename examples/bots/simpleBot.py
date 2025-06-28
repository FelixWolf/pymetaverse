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