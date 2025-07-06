import asyncio
import inspect

class EventTargetListener:
    def __init__(self, func, filters=None, once=False):
        self.func = func
        self.filters = filters or {}
        self.once = once

    def test(self, event_kwargs):
        return all(event_kwargs.get(k) == v for k, v in self.filters.items())

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def is_async(self):
        return inspect.iscoroutinefunction(self.func)


class EventTarget:
    def __init__(self):
        self._listeners = {}  # event -> list of EventTargetListener

    def on(self, event, func=None, once=False, **filters):
        if event not in self._listeners:
            self._listeners[event] = []

        def decorator(f):
            listener = EventTargetListener(f, filters, once)
            self._listeners[event].append(listener)
            return f

        return decorator(func) if func else decorator

    def once(self, event, func=None, **filters):
        return self.on(event, func=func, once=True, **filters)

    def off(self, event, func):
        if event in self._listeners:
            self._listeners[event] = [
                listener for listener in self._listeners[event]
                if listener.func != func
            ]

    async def fire(self, event, *args, **kwargs):
        listeners = self._listeners.get(event, [])
        to_remove = []

        for listener in list(listeners):  # shallow copy to allow mutation
            if listener.test(kwargs):
                if listener.is_async():
                    await listener(*args)
                else:
                    listener(*args)
                if listener.once:
                    to_remove.append(listener)

        for listener in to_remove:
            self._listeners[event].remove(listener)

    def fireSync(self, event, *args, **kwargs):
        listeners = self._listeners.get(event, [])
        to_remove = []

        for listener in list(listeners):
            if listener.test(kwargs):
                listener(*args)
                if listener.once:
                    to_remove.append(listener)

        for listener in to_remove:
            self._listeners[event].remove(listener)

    async def waitFor(self, event, timeout=None, **filters):
        future = asyncio.get_event_loop().create_future()

        def handler(*args):
            if not future.done():
                self.off(event, handler)  # Ensure the listener is removed
                future.set_result(args)

        self.on(event, handler, once=True, **filters)

        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self.off(event, handler)
            raise TimeoutError(f"Timeout while waiting for event '{event}'")
