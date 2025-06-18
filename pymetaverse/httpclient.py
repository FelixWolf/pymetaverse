import aiohttp

class HttpResponse:
    def __init__(self, handle):
        self._handle = handle
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._handle.close()
    
    @property
    def status(self):
        return self._handle.status
    
    @property
    def headers(self):
        return self._handle.headers
    
    async def read(self):
        return await self._handle.read()

class HttpClient:
    def __init__(self):
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._session.close()

    async def get(self, url, **kwargs):
        response = await self._session.get(url, **kwargs)
        return HttpResponse(response)

    async def post(self, url, **kwargs):
        response = await self._session.post(url, **kwargs)
        return HttpResponse(response)

    async def put(self, url, **kwargs):
        response = await self._session.put(url, **kwargs)
        return HttpResponse(response)

    async def delete(self, url, **kwargs):
        response = await self._session.delete(url, **kwargs)
        return HttpResponse(response)

    async def head(self, url, **kwargs):
        response = await self._session.head(url, **kwargs)
        return HttpResponse(response)

    async def options(self, url, **kwargs):
        response = await self._session.options(url, **kwargs)
        return HttpResponse(response)

    async def patch(self, url, **kwargs):
        response = await self._session.patch(url, **kwargs)
        return HttpResponse(response)