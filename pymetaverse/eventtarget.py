import asyncio
import inspect

class EventTarget:
    def __init__(self):
        self._listeners = {}  # event -> list of (func, filters)

    def on(self, event, func=None, **filters):
        if event not in self._listeners:
            self._listeners[event] = []

        def decorator(f):
            self._listeners[event].append((f, filters))
            return f

        return decorator(func) if func else decorator

    def off(self, event, func):
        if event in self._listeners:
            self._listeners[event] = [
                (f, filt) for (f, filt) in self._listeners[event] if f != func
            ]

    async def fire(self, event, *args, **kwargs):
        listeners = self._listeners.get(event, [])
        for func, filters in listeners:
            if all(kwargs.get(k) == v for k, v in filters.items()):
                if inspect.iscoroutinefunction(func):
                    await func(*args)
                else:
                    func(*args)
    
    def fireSync(self, event, *args, **kwargs):
        listeners = self._listeners.get(event, [])
        for func, filters in listeners:
            if all(kwargs.get(k) == v for k, v in filters.items()):
                func(*args)
