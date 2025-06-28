import datetime
import uuid
from aiohttp import web

def logChat(instance, bot):
    @bot.on("message", name="ChatFromSimulator")
    def ChatFromSimulator(simulator, message):
        # Ignore start / stop
        if message.ChatData.Audible == 0 or message.ChatData.ChatType in (4, 5):
            return
            
        text = message.ChatData.Message.rstrip(b"\0").decode()
        print("[{}] [{}] {}: {}".format(
            datetime.datetime.now().strftime("%Y-%M-%d %H:%m:%S"),
            ".".join(bot.agent.username),
            message.ChatData.FromName.rstrip(b"\0").decode(),
            text
        ))

def testRoute(instance, bot):
    @instance.route("test")
    async def testRoute(request):
        return web.Response(text=f"Got request")
