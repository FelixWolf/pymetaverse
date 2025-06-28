import logging

logging.basicConfig(
    level=logging.INFO,  # Or INFO, WARNING, etc.
    format="%(asctime)s [%(levelname)s] %(message)s"
)

import asyncio
import json
import time
import datetime
import traceback
import uuid
import re
import importlib
from aiohttp import web
from pymetaverse import login
from pymetaverse.bot import SimpleBot
from pymetaverse.viewer import messages
from pymetaverse.const import *

def loadDictIntoMessage(msg, data):
    for name, block in data.items():
        if type(data[name]) == list:
            for i, varblock in enumerate(data[name]):
                for key, value in data[name][i].items():
                    if type(value) == dict:
                        if value["type"] == "bytestring":
                            value = value["data"].encode() + b"\0"
                        elif value["type"] == "bytes":
                            value = bytes(value["data"])
                    msg.blocks[name][i].values[key] = value
            msg.blocks[name].count = len(data[name])
        
        elif type(data[name]) == dict:
            for key, value in data[name].items():
                if type(value) == dict:
                    if value["type"] == "bytestring":
                        value = value["data"].encode() + b"\0"
                    elif value["type"] == "bytes":
                        value = bytes(value["data"])
                msg.blocks[name].values[key] = value

class BotInstance:
    def __init__(self, username, password, features = None):
        self.username = username
        self.password = password
        self.features = features or []
        self.routes = []
        self.bot = None
    
    def route(self, pattern):
        def decorator(func):
            regex = re.compile(f"^{pattern}$")
            self.routes.append((regex, func))
            return func
        return decorator

    async def handle_request(self, request, path):
        for regex, handler in self.routes:
            match = regex.match(path)
            if match:
                return await handler(request, **match.groupdict())
        logging.warning("[{}] No handler for path: {}".format(
            ".".join(self.bot.agent.username),
            path
        ))
        return web.Response(status=404, text="No handler for path")
    
    async def run(self):
        while True:
            try:
                bot = SimpleBot()
                self.bot = bot
                self.routes = []
                for feature in self.features:
                    feature(self, bot)
                await bot.login(self.username, self.password)
                logging.info("[{}] Logged in.".format(
                    ".".join(bot.agent.username)
                ))
                await bot.run()
                logging.info("[{}] Logged out.".format(
                    ".".join(bot.agent.username)
                ))
                self.bot = None
            except asyncio.exceptions.CancelledError as e:
                break

def load_callable(path: str):
    """Loads a function or object from a string like 'package.module:func'."""
    if ':' not in path:
        raise ValueError(f"Invalid path '{path}', expected format 'module.submodule:function'")
    
    module_path, func_name = path.split(':', 1)
    module = importlib.import_module(module_path)
    
    try:
        return getattr(module, func_name)
    except AttributeError:
        raise ImportError(f"Function '{func_name}' not found in module '{module_path}'")

async def main():
    with open("bots.json", "r") as f:
        bots = json.load(f)

    instances = []
    for bot in bots:
        if bot.get("disabled", False) == True:
            continue

        functions = []
        for function_path in bot.get("functions", []):
            functions.append(load_callable(function_path))
        instance = BotInstance(bot["username"], bot["password"], functions)
        instances.append(instance)

    async def handle_bot_request(request):
        uuid_str = request.match_info['uuid']
        path = request.match_info.get('path', "")
        
        bot = None
        try:
            bot_uuid = str(uuid.UUID(uuid_str))
            for instance in instances:
                try:
                    if instance.bot.agent.agentId == uuid_str:
                        bot = instance
                        break
                except Exception as e:
                    raise e
        
        except ValueError:
            for instance in instances:
                try:
                    if ".".join(instance.bot.agent.username).lower() == uuid_str.lower():
                        bot = instance
                        break
                except Exception as e:
                    raise e

        if bot:
            return await bot.handle_request(request, path)
        
        logging.warning("[WEB] No bot found: {}".format(
            uuid_str
        ))
        return web.Response(status=404, text="Bot not found")

    async def handle_bot_index(request):
        response = {}
        for instance in instances:
            response[instance.bot.agent.agentId] = {
                "username": list(instance.bot.agent.username) if instance.bot.agent.username != (None, None) else []
            }
            
        return web.Response(status=200, text=json.dumps(response))
    
    async def run_web_server():
        app = web.Application()
        app.router.add_get('/bot/{uuid}/{path:.*}', handle_bot_request)
        app.router.add_get('/bot/{uuid}', handle_bot_request)
        app.router.add_get('/bot', handle_bot_index)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 26875)
        await site.start()
    
    # Launch both the web server and bots
    await asyncio.gather(
        run_web_server(),
        *[instance.run() for instance in instances]
    )

# Run everything
asyncio.run(main())
