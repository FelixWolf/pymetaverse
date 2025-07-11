from .. import httpclient
from .. import llsd

class CapabilityRegistry:
    def __init__(self):
        self.capabilities = {}
    
    def register(self, name):
        def _(func):
            self.capabilities[name] = func
            return func
        return _
    
    def __contains__(self, what):
        return what in self.capabilities
    
    def get(self, name, url):
        try:
            return self.capabilities[name](url)
        except KeyError:
            raise ValueError("No such capability {}".format(name))

Capabilities = CapabilityRegistry()

class BaseCapability:
    def __init__(self, url):
        self.url = url

# Please keep these in alphabetical order! :)

@Capabilities.register("EventQueueGet")
class EventQueueGet(BaseCapability):
    async def poll(self, ack, done = False):
        async with httpclient.HttpClient() as session:
            async with await session.post(self.url,
                data = llsd.llsdEncode({
                    "ack": ack,
                    "done": done
                }),
                headers = {
                    "Content-Type": "application/llsd+xml"
                },
                timeout = 60 # Timeouts on the server are 30, twice that is more than enough
            ) as response:
                if response.status == 404:
                    return None, []
                
                elif response.status == 200:
                    data = await response.read()
                    result = llsd.llsdDecode(data, format="xml")
                    return result["id"], result["events"]
                
                else:
                    return ack, []

@Capabilities.register("Seed")
class Seed(BaseCapability):
    async def getCapabilities(self, caps):
        async with httpclient.HttpClient() as session:
            async with await session.post(self.url,
                data = llsd.llsdEncode(list(caps.capabilities.keys())),
                headers = {
                    "Content-Type": "application/llsd+xml"
                }
            ) as response:
                capList = llsd.llsdDecode(await response.read(), format="xml")
                result = {}
                for name, url in capList.items():
                    if name in caps:
                        result[name] = caps.get(name, url)
                
                return result
